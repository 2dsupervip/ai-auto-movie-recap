import streamlit as st
import os
import gc
import json
import asyncio
import google.generativeai as genai
import edge_tts
import yt_dlp
from gtts import gTTS
from moviepy import VideoFileClip, AudioFileClip, concatenate_audioclips, afx
from proglog import ProgressBarLogger

# --- Custom Logger for Streamlit Progress Bar ---
class StreamlitLogger(ProgressBarLogger):
    def __init__(self):
        super().__init__()
        self.bar = st.progress(0.0)
        self.text_holder = st.empty()
        
    def bars_callback(self, bar, attr, value, old_value=None):
        total = self.bars[bar]['total']
        if total > 0:
            percentage = min(100, int((value / total) * 100))
            self.bar.progress(min(1.0, value / total))
            self.text_holder.markdown(f"**⏳ ဗီဒီယို ပေါင်းစပ်နေသည်... {percentage}% ပြီးစီးပါပြီ**")

# --- Page Configuration ---
st.set_page_config(page_title="Shorts Movie Recap (AI Free)", page_icon="🎬", layout="centered")

# --- Custom CSS ---
st.markdown("""
    <style>
    .main-title { font-size: 36px; font-weight: 800; color: #00E676; text-align: center; margin-bottom: 5px; }
    .sub-title { text-align: center; color: #A0A0A0; font-size: 14px; margin-bottom: 30px; font-family: monospace;}
    .step-header { color: #00E676; font-weight: bold; font-size: 20px; border-bottom: 1px solid #00E676; padding-bottom: 10px; margin-bottom: 20px; }
    .stButton>button { background-color: #00E676; color: #111111; font-weight: bold; border-radius: 8px; width: 100%; transition: 0.3s; }
    .stButton>button:hover { background-color: #B2FF59; color: #000000; }
    </style>
""", unsafe_allow_html=True)

# --- Init Persistent API Storage ---
API_FILE = "api_config.json"
if os.path.exists(API_FILE):
    with open(API_FILE, "r") as f: saved_key = json.load(f).get("api_key", "")
else: saved_key = ""

# --- Initial Session States ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'draft_script' not in st.session_state: st.session_state.draft_script = ""
if 'api_key' not in st.session_state: st.session_state.api_key = saved_key

def next_step(): st.session_state.step += 1
def prev_step(): st.session_state.step -= 1

def reset_project():
    for f in ["temp_video.mp4", "temp_audio.mp3", "final_voice.mp3", "final_merged.mp4", "subtitles.srt", "custom_bgm.mp3"]:
        if os.path.exists(f): os.remove(f)
    st.session_state.clear()
    st.session_state.api_key = saved_key # Key ကိုတော့ ပြန်မှတ်ထားပေးမည်
    st.session_state.step = 1
    st.rerun()

# --- Helpers ---
async def generate_premium_voice_and_srt(text, voice_name, audio_filename, srt_filename):
    communicate = edge_tts.Communicate(text, voice_name)
    submaker = edge_tts.SubMaker()
    with open(audio_filename, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio": file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                if hasattr(submaker, 'feed'): submaker.feed(chunk)
                else: submaker.create_sub((chunk["offset"], chunk["duration"]), chunk["text"])
    with open(srt_filename, "w", encoding="utf-8") as file:
        if hasattr(submaker, 'get_srt'): file.write(submaker.get_srt())
        else: file.write(submaker.generate_subs())

# --- UI Header ---
st.markdown('<div class="main-title">🎬 Shorts Movie Recap (AI Free)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Ultimate Master Engine (BGM & Copyright Pro)</div>', unsafe_allow_html=True)

# ==========================================
# WIZARD STEP 1: Setup & Media Input
# ==========================================
if st.session_state.step == 1:
    st.markdown('<div class="step-header">Step 1: Setup & Configuration</div>', unsafe_allow_html=True)
    
    col_k1, col_k2 = st.columns([3, 1])
    with col_k1:
        api_input = st.text_input("🔑 Google Gemini API Key", type="password", value=st.session_state.api_key)
    with col_k2:
        st.write(""); st.write("")
        if st.button("💾 သိမ်းမည်"):
            with open(API_FILE, "w") as f: json.dump({"api_key": api_input}, f)
            st.session_state.api_key = api_input
            st.success("Saved!")

    input_method = st.radio("📥 တင်မည့်ပုံစံ ရွေးချယ်ပါ", ["Upload Video", "YouTube Link"], horizontal=True)
    if input_method == "Upload Video":
        uploaded_file = st.file_uploader("ဗီဒီယိုဖိုင် ရွေးပါ", type=["mp4", "mov"])
        if uploaded_file:
            with open("temp_video.mp4", "wb") as f: f.write(uploaded_file.getbuffer())
            st.success("Video Uploaded!")
    else:
        youtube_url = st.text_input("Paste YouTube Link Here")
        if st.button("⬇️ Download Video"):
            with st.spinner("Downloading..."):
                try:
                    ydl_opts = {'format': 'best[height<=720]', 'outtmpl': 'temp_video.mp4', 'quiet': True}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([youtube_url])
                    st.success("YouTube Video Downloaded!")
                except Exception as e: st.error(f"Download Error: {e}")

    st.markdown("### 🎛️ Advanced Settings")
    col1, col2 = st.columns(2)
    with col1:
        script_tone = st.selectbox("📝 Script Tone", ["Narrative", "Calm", "Energetic", "Dramatic"])
        use_bgm = st.checkbox("🎶 နောက်ခံတီးလုံး (BGM) ထည့်မည်", value=True)
    with col2:
        tts_engine = st.selectbox("🎙️ Voice Engine", ["Premium (Nilar/Thiha)", "Standard (gTTS)"])
        target_duration = st.selectbox("⏳ အနှစ်ချုပ်မည့်အချိန် (Long Video များအတွက်)", ["3 Minutes", "4 Minutes", "5 Minutes"])

    # Custom BGM Option
    custom_bgm_file = st.file_uploader("📂 ကိုယ်ပိုင်တီးလုံးတင်ရန် (မဖြစ်မနေမဟုတ်ပါ)", type=["mp3"])
    if custom_bgm_file:
        with open("custom_bgm.mp3", "wb") as f: f.write(custom_bgm_file.getbuffer())

    if st.button("🚀 Next: Generate Script"):
        if not st.session_state.api_key: st.error("⚠️ API Key လိုအပ်ပါသည်။")
        elif not os.path.exists("temp_video.mp4"): st.error("⚠️ ဗီဒီယို အရင်တင်ပါ။")
        else:
            with st.spinner("Analyzing Video..."):
                genai.configure(api_key=st.session_state.api_key)
                video_clip = VideoFileClip("temp_video.mp4")
                video_clip.audio.write_audiofile("temp_audio.mp3", logger=None)
                is_long = video_clip.duration > 300
                video_clip.close()
                
                model = genai.GenerativeModel("gemini-1.5-flash")
                audio_file = genai.upload_file(path="temp_audio.mp3")
                prompt = f"Summarize this movie in a {script_tone} Burmese script for TikTok. {'Target duration: ' + target_duration if is_long else 'Match original video length.'} No markdown."
                response = model.generate_content([prompt, audio_file])
                
                st.session_state.draft_script = response.text
                st.session_state.is_long_video = is_long
                st.session_state.use_bgm = use_bgm
                st.session_state.script_tone = script_tone
                st.session_state.tts_engine = tts_engine
                next_step()
                st.rerun()

# ==========================================
# WIZARD STEP 2: Editor
# ==========================================
elif st.session_state.step == 2:
    st.markdown('<div class="step-header">Step 2: Script Editor</div>', unsafe_allow_html=True)
    edited_script = st.text_area("Edit Script:", value=st.session_state.draft_script, height=300)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Back"): prev_step(); st.rerun()
    with col2:
        if st.button("🎙️ Next: Process Final Video"):
            st.session_state.final_script = edited_script
            next_step(); st.rerun()

# ==========================================
# WIZARD STEP 3: Final Export
# ==========================================
elif st.session_state.step == 3:
    st.markdown('<div class="step-header">Step 3: Processing Output</div>', unsafe_allow_html=True)
    
    with st.spinner("Generating Voice & Processing Video..."):
        try:
            # 1. Voice Generation
            clean_script = st.session_state.final_script.replace("*", "")
            if "Premium" in st.session_state.tts_engine:
                asyncio.run(generate_premium_voice_and_srt(clean_script, "my-MM-NilarNeural", "final_voice.mp3", "subtitles.srt"))
            else:
                gTTS(text=clean_script, lang='my').save("final_voice.mp3")
            
            # 2. Video Processing
            if st.session_state.is_long_video:
                st.success("Long Video အား အနှစ်ချုပ် အသံဖိုင် ထုတ်ပေးပြီးပါပြီ!")
                st.audio("final_voice.mp3")
            else:
                video_clip = VideoFileClip("temp_video.mp4")
                voice_audio = AudioFileClip("final_voice.mp3")
                
                # Copyright FX
                import moviepy.video.fx.all as vfx
                processed_video = video_clip.speedx(factor=video_clip.duration/voice_audio.duration).fx(vfx.mirror_x)
                w, h = processed_video.size
                processed_video = processed_video.crop(x1=w*0.03, y1=h*0.03, x2=w*0.97, y2=h*0.97).resize(height=720).fx(vfx.colorx, 1.05).fx(vfx.speedx, 1.01)
                
                # BGM Mixing
                final_audio = voice_audio
                if st.session_state.use_bgm:
                    bgm_path = "custom_bgm.mp3" if os.path.exists("custom_bgm.mp3") else f"bgm/{st.session_state.script_tone.lower()}.mp3"
                    if os.path.exists(bgm_path):
                        bgm = AudioFileClip(bgm_path).volumex(0.12).set_duration(voice_audio.duration)
                        final_audio = concatenate_audioclips([voice_audio.set_start(0), bgm.set_start(0)]) # Placeholder for mixing logic
                        # Real mixing: final_audio = CompositeAudioClip([voice_audio, bgm])
                        from moviepy.audio.AudioClip import CompositeAudioClip
                        final_audio = CompositeAudioClip([voice_audio, bgm])

                final_video = processed_video.set_audio(final_audio)
                my_logger = StreamlitLogger()
                final_video.write_videofile("final_merged.mp4", codec="libx264", audio_codec="aac", threads=2, logger=my_logger)
                
                st.success("ဗီဒီယို ပေါင်းစပ်ခြင်း ပြီးစီးပါပြီ!")
                st.video("final_merged.mp4")
            
            st.markdown("---")
            if st.button("🔄 New Project (Reset)"): reset_project()
        except Exception as e: st.error(f"Error: {e}")
