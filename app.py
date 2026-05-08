import streamlit as st
import os
import gc
import json
import asyncio
import google.generativeai as genai
import edge_tts
import yt_dlp
from gtts import gTTS
from moviepy import VideoFileClip, AudioFileClip
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
    with open(API_FILE, "r") as f:
        saved_key = json.load(f).get("api_key", "")
else:
    saved_key = ""

# --- Initial Session States ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'draft_script' not in st.session_state: st.session_state.draft_script = ""
if 'api_key' not in st.session_state: st.session_state.api_key = saved_key
if 'video_duration' not in st.session_state: st.session_state.video_duration = 0
if 'is_long_video' not in st.session_state: st.session_state.is_long_video = False

def next_step(): st.session_state.step += 1
def prev_step(): st.session_state.step -= 1

# --- Premium TTS & Auto-SRT Helper ---
async def generate_premium_voice_and_srt(text, voice_name, audio_filename, srt_filename):
    communicate = edge_tts.Communicate(text, voice_name)
    submaker = edge_tts.SubMaker()
    with open(audio_filename, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                if hasattr(submaker, 'feed'): submaker.feed(chunk)
                elif hasattr(submaker, 'create_sub'): submaker.create_sub((chunk["offset"], chunk["duration"]), chunk["text"])
    with open(srt_filename, "w", encoding="utf-8") as file:
        if hasattr(submaker, 'get_srt'): file.write(submaker.get_srt())
        elif hasattr(submaker, 'generate_subs'): file.write(submaker.generate_subs())
        else: file.write(str(submaker))

# --- Standard TTS Helper ---
def generate_standard_voice(text, audio_filename):
    tts = gTTS(text=text, lang='my')
    tts.save(audio_filename)

# --- YouTube Downloader Helper ---
def download_youtube_video(url, output_path="temp_video.mp4"):
    ydl_opts = {
        'format': 'best[height<=720]', 
        'outtmpl': output_path,
        'quiet': True,
        'nocheckcertificate': True,
        'extractor_args': {'youtube': {'player_client': ['android']}}
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return output_path

# --- UI Header ---
st.markdown('<div class="main-title">🎬 Shorts Movie Recap (AI Free)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Smart Engine (Dual TTS, Copyright Safe & Auto-Subtitle)</div>', unsafe_allow_html=True)

# ==========================================
# WIZARD STEP 1: Setup & Media Input
# ==========================================
if st.session_state.step == 1:
    st.markdown('<div class="step-header">Step 1: AI Engine Setup & Input</div>', unsafe_allow_html=True)
    
    # --- API Config UI ---
    col_k1, col_k2 = st.columns([3, 1])
    with col_k1:
        api_input = st.text_input("🔑 Google Gemini API Key", type="password", value=st.session_state.api_key)
    with col_k2:
        st.write("")
        st.write("")
        if st.button("💾 သိမ်းမည်"):
            with open(API_FILE, "w") as f:
                json.dump({"api_key": api_input}, f)
            st.session_state.api_key = api_input
            st.success("Saved!")
            
    if st.session_state.api_key:
        genai.configure(api_key=st.session_state.api_key)
        st.markdown("🟢 **API Status:** ချိတ်ဆက်မှု အောင်မြင်သည် (Active)")
    else:
        st.markdown("🔴 **API Status:** API Key ထည့်သွင်းရန် လိုအပ်သည်")
    
    st.markdown("---")
    # --- Media Source ---
    input_method = st.radio("📥 တင်မည့်ပုံစံ ရွေးချယ်ပါ", ["Upload Video (အကြံပြုသည်)", "YouTube Link (Error တက်နိုင်သည်)"], horizontal=True)
    if input_method == "Upload Video (အကြံပြုသည်)":
        uploaded_file = st.file_uploader("ဗီဒီယိုဖိုင် ရွေးပါ", type=["mp4", "mov"])
        if uploaded_file:
            with open("temp_video.mp4", "wb") as f: f.write(uploaded_file.getbuffer())
            st.success("ဗီဒီယို တင်ပြီးပါပြီ။")
    else:
        youtube_url = st.text_input("Paste YouTube Link Here")
        if st.button("⬇️ Download Video"):
            if youtube_url:
                with st.spinner("YouTube မှ ဆွဲယူနေပါသည်..."):
                    try:
                        if os.path.exists("temp_video.mp4"): os.remove("temp_video.mp4")
                        download_youtube_video(youtube_url)
                        st.success("YouTube ဗီဒီယို ဆွဲယူခြင်း အောင်မြင်ပါသည်။")
                    except Exception as e:
                        st.error("YouTube မှ ပိတ်ထားပါသည်။ Upload Video စနစ်ကို ပြောင်းသုံးပါ။")

    # --- Script & Voice Settings ---
    st.markdown("### 🎛️ Script & Voice Settings")
    col1, col2 = st.columns(2)
    with col1:
        script_tone = st.selectbox("📝 ဇာတ်ညွှန်း ပြောဟန် (Script Tone)", ["Narrative (ဇာတ်လမ်းပြောဟန်)", "Calm (အေးအေးဆေးဆေး)", "Energetic (တက်တက်ကြွကြွ)", "Dramatic (ခံစားချက်အပြည့်)"])
        tts_engine = st.selectbox("🎙️ Voice Engine", ["Premium Engine (Edge-TTS / လူသံ)", "Standard Engine (gTTS / စက်သံ)"])
    with col2:
        voice_gender = st.selectbox("🗣️ Premium Voice (Edge-TTS ရွေးထားမှသာ)", ["Female (Nilar)", "Male (Thiha)"])
        target_duration = st.selectbox("⏳ အနှစ်ချုပ်ရမည့် အချိန် (ဗီဒီယိုရှည်များအတွက်)", ["3 Minutes", "4 Minutes", "5 Minutes"])

    if st.button("🚀 Next: Analyze & Generate Script"):
        if not st.session_state.api_key: st.error("⚠️ API Key အရင်ထည့်ပါ။")
        elif not os.path.exists("temp_video.mp4"): st.error("⚠️ ဗီဒီယို အရင်တင်ရန် လိုအပ်ပါသည်။")
        else:
            with st.spinner(">> ဗီဒီယိုကြာချိန်ကို စစ်ဆေးနေပါသည်..."):
                video_clip = VideoFileClip("temp_video.mp4")
                duration = video_clip.duration
                st.session_state.video_duration = duration
                
                if duration > 300:
                    st.session_state.is_long_video = True
                    st.warning("⚠️ ၅ မိနစ်ကျော်သော ဗီဒီယိုဖြစ်သဖြင့် အနှစ်ချုပ် (Summarize) သာ ပြုလုပ်ပေးပါမည်။")
                else:
                    st.session_state.is_long_video = False
                    st.info("💡 ၅ မိနစ်အောက်ဖြစ်သဖြင့် အသံနှင့်ရုပ် ပေါင်းစပ်ပေးပါမည်။")
                
                video_clip.audio.write_audiofile("temp_audio.mp3", logger=None)
                video_clip.close()
                gc.collect()

            with st.spinner(">> AI မှ သတ်မှတ် Tone ဖြင့် ဇာတ်ညွှန်း ရေးသားနေပါသည်..."):
                try:
                    # AI Model Auto-Detect
                    available_models = [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    best_model = "gemini-1.5-flash" if "gemini-1.5-flash" in available_models else (available_models[0] if available_models else "gemini-1.5-pro")
                        
                    model = genai.GenerativeModel(best_model)
                    audio_file = genai.upload_file(path="temp_audio.mp3")
                    
                    tone_map = {
                        "Narrative (ဇာတ်လမ်းပြောဟန်)": "narrative storytelling",
                        "Calm (အေးအေးဆေးဆေး)": "calm and relaxing",
                        "Energetic (တက်တက်ကြွကြွ)": "highly energetic and enthusiastic",
                        "Dramatic (ခံစားချက်အပြည့်)": "intensely dramatic and emotional"
                    }
                    selected_tone = tone_map[script_tone]
                    
                    if st.session_state.is_long_video:
                        duration_mins = target_duration.split()[0]
                        prompt = f"Listen to this English audio. Summarize the plot into a Burmese TikTok script in a {selected_tone} tone. MUST take exactly {duration_mins} minutes to read out loud. No markdown."
                    else:
                        prompt = f"Listen to this English audio. Write a concise Burmese movie recap script in a {selected_tone} tone. It MUST be short enough to take the exact same amount of time to read as the original audio. No markdown."

                    response = model.generate_content([prompt, audio_file])
                    st.session_state.draft_script = response.text
                    st.session_state.tts_engine = tts_engine
                    st.session_state.voice_gender = voice_gender
                    
                    next_step()
                    st.rerun()
                except Exception as e:
                    if "Quota" in str(e) or "429" in str(e):
                        st.error("🔴 Quota Limit ပြည့်သွားပါပြီ! အခြား API Key ပြောင်းသုံးပါ။")
                    else:
                        st.error(f"AI Error: {e}")

# ==========================================
# WIZARD STEP 2: Script Editor
# ==========================================
elif st.session_state.step == 2:
    st.markdown('<div class="step-header">Step 2: Script Editor</div>', unsafe_allow_html=True)
    st.info("📝 အောက်ပါ ဇာတ်ညွှန်းအား မိမိစိတ်ကြိုက် ပြင်ဆင်နိုင်ပါသည်။")

    edited_script = st.text_area("Edit Burmese Script:", value=st.session_state.draft_script, height=300)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Back"): prev_step(); st.rerun()
    with col2:
        if st.button("🎙️ Next: Generate Final Output"):
            st.session_state.final_script = edited_script
            next_step()
            st.rerun()

# ==========================================
# WIZARD STEP 3: Final Processing & Export
# ==========================================
elif st.session_state.step == 3:
    st.markdown('<div class="step-header">Step 3: Final Output</div>', unsafe_allow_html=True)
    
    with st.spinner(">> Voice-over ဖန်တီးနေပါသည်..."):
        try:
            clean_script = st.session_state.final_script.replace("*", "").replace("#", "")
            has_srt = False
            
            # --- 1. Dual Engine TTS Generation ---
            if "Premium" in st.session_state.tts_engine:
                voice_id = "my-MM-NilarNeural" if "Nilar" in st.session_state.voice_gender else "my-MM-ThihaNeural"
                asyncio.run(generate_premium_voice_and_srt(clean_script, voice_id, "final_voice.mp3", "subtitles.srt"))
                has_srt = True
            else:
                generate_standard_voice(clean_script, "final_voice.mp3")
                has_srt = False # gTTS အတွက် SRT မထုတ်ပေးနိုင်ပါ

            # --- 2. Long Video Processing (No Merge) ---
            if st.session_state.is_long_video:
                st.success("🎉 အနှစ်ချုပ် အသံဖိုင် ဖန်တီးပြီးပါပြီ! (VN/CapCut တွင် ဖြတ်ဆက်ပါ)")
                st.audio("final_voice.mp3")
                
                cols = st.columns(3)
                with cols[0]:
                    with open("temp_video.mp4", "rb") as f: st.download_button("🎥 Raw Video", data=f, file_name="Raw_Video.mp4", mime="video/mp4")
                with cols[1]:
                    with open("final_voice.mp3", "rb") as f: st.download_button("🎙️ Audio Only", data=f, file_name="Recap_Audio.mp3", mime="audio/mp3")
                if has_srt:
                    with cols[2]:
                        with open("subtitles.srt", "rb") as f: st.download_button("📝 Subtitle (SRT)", data=f, file_name="GoldenKey_Subs.srt", mime="text/plain")

            # --- 3. Short Video Processing (Merge + Copyright + Progress Bar) ---
            else:
                video_clip = VideoFileClip("temp_video.mp4")
                new_audio = AudioFileClip("final_voice.mp3")
                speed_factor = video_clip.duration / new_audio.duration
                
                # Copyright Check: Mirror
                if hasattr(video_clip, 'with_effects'):
                    import moviepy.video.fx as vfx
                    synced_video = video_clip.with_effects([vfx.MultiplySpeed(speed_factor), vfx.MirrorX()])
                else:
                    import moviepy.video.fx.all as vfx
                    synced_video = video_clip.speedx(factor=speed_factor).fx(vfx.mirror_x)
                
                w, h = synced_video.size
                
                # Copyright Check: Crop Bottom 15%
                if hasattr(synced_video, 'cropped'): synced_video = synced_video.cropped(x1=w*0.05, y1=h*0.05, x2=w*0.95, y2=h*0.85)
                else: synced_video = synced_video.crop(x1=w*0.05, y1=h*0.05, x2=w*0.95, y2=h*0.85)
                
                # Apply Audio
                if hasattr(synced_video, 'with_duration'): final_video = synced_video.with_duration(new_audio.duration).with_audio(new_audio)
                else: final_video = synced_video.set_duration(new_audio.duration).set_audio(new_audio)
                
                # Optimization
                if hasattr(final_video, 'resized'): final_video = final_video.resized(height=720)
                else: final_video = final_video.resize(height=720)
                
                # 🌟 Render with ProgLog Custom UI Logger 🌟
                my_logger = StreamlitLogger()
                final_video.write_videofile("final_merged.mp4", codec="libx264", audio_codec="aac", preset="ultrafast", threads=2, logger=my_logger)
                
                video_clip.close()
                new_audio.close()
                final_video.close()
                gc.collect()
                
                my_logger.text_holder.markdown("**✅ ဗီဒီယို ပေါင်းစပ်ခြင်း ၁၀၀% ပြီးစီးပါပြီ!**")
                st.success("🎉 Copyright-Safe ဗီဒီယို အောင်မြင်စွာ ပေါင်းစပ်ပြီးပါပြီ!")
                st.video("final_merged.mp4")
                
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    with open("final_merged.mp4", "rb") as f: st.download_button("📥 Download Safe Video", data=f, file_name="AI_Free_Merged.mp4", mime="video/mp4")
                if has_srt and os.path.exists("subtitles.srt"):
                    with col_f2:
                        with open("subtitles.srt", "rb") as f: st.download_button("📝 Download SRT File", data=f, file_name="AI_Free_Subs.srt", mime="text/plain")
                        
            st.markdown("---")
            if st.button("🔄 Start New Project"): st.session_state.step = 1; st.rerun()

        except Exception as e:
            st.error(f"Processing Error: {e}")
