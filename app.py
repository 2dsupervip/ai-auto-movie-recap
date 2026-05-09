# 🌟 PIL Error Auto-Fix 🌟
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

import streamlit as st
import os
import gc
import json
import asyncio
import google.generativeai as genai
from groq import Groq
import edge_tts
import yt_dlp
from gtts import gTTS
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
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
    .main-title { font-size: 32px; font-weight: 800; color: #00E676; text-align: center; margin-bottom: 5px; }
    .sub-title { text-align: center; color: #A0A0A0; font-size: 14px; margin-bottom: 30px; font-family: monospace;}
    .step-header { color: #00E676; font-weight: bold; font-size: 20px; border-bottom: 1px solid #00E676; padding-bottom: 10px; margin-bottom: 20px; }
    .stButton>button { background-color: #00E676; color: #111111; font-weight: bold; border-radius: 8px; width: 100%; transition: 0.3s; }
    .stButton>button:hover { background-color: #B2FF59; color: #000000; }
    </style>
""", unsafe_allow_html=True)

# --- Persistent API Storage ---
API_FILE = "api_config.json"
def load_keys():
    if os.path.exists(API_FILE):
        with open(API_FILE, "r") as f: return json.load(f)
    return {"gemini_1": "", "gemini_2": "", "gemini_3": "", "groq_1": ""}

def save_keys(keys_dict):
    with open(API_FILE, "w") as f: json.dump(keys_dict, f)

# --- Session States ---
saved_keys = load_keys()
if 'step' not in st.session_state: st.session_state.step = 1
if 'draft_script' not in st.session_state: st.session_state.draft_script = ""
if 'ready_made_prompt' not in st.session_state: st.session_state.ready_made_prompt = ""
if 'video_duration' not in st.session_state: st.session_state.video_duration = 0
if 'is_rendered' not in st.session_state: st.session_state.is_rendered = False
for k, v in saved_keys.items():
    if k not in st.session_state: st.session_state[k] = v

def next_step(): st.session_state.step += 1
def prev_step(): st.session_state.step -= 1

def reset_project():
    gc.collect()
    for f in ["temp_video.mp4", "temp_audio.mp3", "final_voice.mp3", "final_merged.mp4", "subtitles.srt", "custom_bgm.mp3"]:
        try:
            if os.path.exists(f): os.remove(f)
        except: pass
    keys_to_keep = {k: st.session_state[k] for k in saved_keys}
    st.session_state.clear()
    for k, v in keys_to_keep.items(): st.session_state[k] = v
    st.session_state.step = 1
    st.session_state.is_rendered = False
    st.rerun()

# --- 🌟 SRT AND PREMIUM VOICE HELPER 🌟 ---
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

# --- SMART PROMPT LOGIC (ADDED NO-BRACKET NAME RULE) ---
def get_prompt_with_limit(duration_seconds, tone):
    word_limit = int((duration_seconds / 60) * 140)
    bt = "`" * 3
    return f"""
    Act as a professional Burmese movie recapper. 
    Summarize this plot into a natural, engaging Burmese script.
    TONE: {tone}
    LENGTH: ~{word_limit} Burmese words.
    CRITICAL INSTRUCTIONS:
    1. Return the final Burmese script ONLY inside a markdown code block ({bt}). No other text.
    2. Do NOT include English names in parentheses. Write names naturally in Burmese only (e.g., write "ဂျက်", NOT "ဂျက် (Jack)").
    """

# --- AI Executors ---
def execute_gemini_smart(audio_path, tone, duration):
    active_keys = [st.session_state[k] for k in ["gemini_1", "gemini_2", "gemini_3"] if st.session_state[k].strip()]
    if not active_keys: raise Exception("Gemini API Key လိုအပ်ပါသည်။")
    prompt = get_prompt_with_limit(duration, tone)
    for idx, key in enumerate(active_keys):
        try:
            st.write(f">> 🟢 Gemini Key {idx+1} ဖြင့် ချိတ်ဆက်နေပါသည်...")
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            audio_file = genai.upload_file(path=audio_path)
            return model.generate_content([prompt, audio_file]).text
        except Exception as e:
            if "429" in str(e) and idx < len(active_keys) - 1: continue
            else: raise e

# --- UI Header ---
st.markdown('<div class="main-title">🎬 Shorts Movie Recap (AI Free)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Smart Duration | Voice & SRT Sync | Full Automation</div>', unsafe_allow_html=True)

# ==========================================
# WIZARD STEP 1: Settings & Media
# ==========================================
if st.session_state.step == 1:
    st.markdown('<div class="step-header">Step 1: Setup & Media</div>', unsafe_allow_html=True)
    
    with st.expander("⚙️ API Key Settings", expanded=False):
        col_g1, col_g2, col_g3 = st.columns(3)
        st.session_state.gemini_1 = col_g1.text_input("Gemini 1", type="password", value=st.session_state.gemini_1)
        st.session_state.gemini_2 = col_g2.text_input("Gemini 2", type="password", value=st.session_state.gemini_2)
        st.session_state.gemini_3 = col_g3.text_input("Gemini 3", type="password", value=st.session_state.gemini_3)
        st.session_state.groq_1 = st.text_input("Groq Key", type="password", value=st.session_state.groq_1)
        if st.button("💾 API Keys သိမ်းမည်"): save_keys({k: st.session_state[k] for k in saved_keys}); st.success("Saved!")

    input_method = st.radio("Media Source:", ["Upload Video", "YouTube Link"], horizontal=True)
    if input_method == "Upload Video":
        uploaded_file = st.file_uploader("ဗီဒီယိုဖိုင် ရွေးပါ", type=["mp4", "mov"])
        if uploaded_file:
            with open("temp_video.mp4", "wb") as f: f.write(uploaded_file.getbuffer())
            st.success("Video Ready!")
    else:
        youtube_url = st.text_input("YouTube Link")
        if st.button("⬇️ Download"):
            with st.spinner("Downloading..."):
                try:
                    with yt_dlp.YoutubeDL({'format': 'best[height<=720]', 'outtmpl': 'temp_video.mp4', 'quiet': True}) as ydl: ydl.download([youtube_url])
                    st.success("Download Complete!")
                except Exception as e: st.error(f"Error: {e}")

    st.markdown("### 🎛️ Preferences")
    col_w, col_t = st.columns(2)
    with col_w:
        workflow = st.radio("🔄 လုပ်ငန်းစဉ်", ["Auto (Gemini)", "Manual (Groq)"])
        script_tone = st.selectbox("📝 Tone", ["Narrative", "Calm", "Energetic", "Dramatic"])
    with col_t:
        engine_col, gender_col = st.columns(2)
        tts_engine = engine_col.selectbox("🎙️ Voice Engine", ["Premium (TTS)", "Standard (gTTS)"])
        gender = gender_col.selectbox("👤 Gender", ["Male", "Female"])
        use_bgm = st.checkbox("🎶 Background Music", value=True)

    if st.button("🚀 Process Script"):
        if not os.path.exists("temp_video.mp4"): st.error("⚠️ ဗီဒီယို အရင်တင်ပါ။")
        else:
            with st.spinner("Analyzing..."):
                video_clip = VideoFileClip("temp_video.mp4")
                st.session_state.video_duration = video_clip.duration
                video_clip.audio.write_audiofile("temp_audio.mp3", logger=None)
                video_clip.close()
                
                tone_map = {"Narrative": "storytelling", "Calm": "calm", "Energetic": "energetic", "Dramatic": "dramatic"}
                try:
                    if "Auto" in workflow:
                        st.session_state.draft_script = execute_gemini_smart("temp_audio.mp3", tone_map[script_tone], st.session_state.video_duration)
                        st.session_state.workflow_mode = "Auto"
                    else:
                        client = Groq(api_key=st.session_state.groq_1)
                        with open("temp_audio.mp3", "rb") as f:
                            transcription = client.audio.transcriptions.create(file=("temp_audio.mp3", f.read()), model="whisper-large-v3", response_format="text")
                        limit = int((st.session_state.video_duration/60)*140)
                        bt = "`" * 3
                        
                        st.session_state.ready_made_prompt = f"""Act as a professional movie recapper. Summarize this English transcription into a natural Burmese storytelling script.
TONE: {tone_map[script_tone]}
LENGTH: ~{limit} Burmese words.
CRITICAL INSTRUCTIONS:
1. Return the final Burmese script ONLY inside a markdown code block ({bt}text ... {bt}) so I can copy it.
2. Do NOT include English names in parentheses. Write names naturally in Burmese only (e.g., write "ဂျက်", NOT "ဂျက် (Jack)").

Transcription:
{transcription}"""
                        st.session_state.workflow_mode = "Manual"
                    
                    st.session_state.tts_engine, st.session_state.gender, st.session_state.use_bgm = tts_engine, gender, use_bgm
                    st.session_state.step = 2
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

# ==========================================
# WIZARD STEP 2: Editor
# ==========================================
elif st.session_state.step == 2:
    st.markdown('<div class="step-header">Step 2: Script Editor</div>', unsafe_allow_html=True)
    bt = "`" * 3 
    
    if st.session_state.workflow_mode == "Auto":
        st.info("Copy ခလုတ်ကို နှိပ်၍ ဇာတ်ညွှန်းကို ကူးယူနိုင်ပါသည်။")
        display_text = st.session_state.draft_script.replace(f"{bt}text", "").replace(f"{bt}markdown", "").replace(bt, "").strip()
        st.code(display_text, language="markdown")
        edited_script = st.text_area("✍️ လိုအပ်ပါက ပြင်ဆင်ပါ:", value=display_text, height=300)
    else:
        st.info("💡 အောက်ပါစာသားကို Copy ယူပြီး Gemini တွင် ထည့်ပါ။ Gemini မှထွက်လာသော Code Block ကို Copy ပြန်ယူပြီး အောက်တွင် Paste လုပ်ပါ။")
        st.code(st.session_state.ready_made_prompt, language="text")
        edited_script = st.text_area("✍️ Paste translated script here:", value=st.session_state.draft_script, height=300)

    c1, c2 = st.columns(2)
    if c1.button("⬅️ Back"): st.session_state.step = 1; st.rerun()
    if c2.button("🎙️ Next: Render"):
        if not edited_script.strip(): st.error("စာသားထည့်ပါ")
        else: 
            clean_edited = edited_script.replace(f"{bt}text", "").replace(f"{bt}markdown", "").replace(bt, "").strip()
            st.session_state.draft_script = clean_edited 
            st.session_state.final_script = clean_edited
            st.session_state.is_rendered = False 
            next_step()
            st.rerun()

# ==========================================
# WIZARD STEP 3: Rendering
# ==========================================
elif st.session_state.step == 3:
    st.markdown('<div class="step-header">Step 3: Final Output</div>', unsafe_allow_html=True)
    
    if not st.session_state.is_rendered:
        with st.spinner("Rendering Video & Generating Subtitles..."):
            try:
                if "Premium" in st.session_state.tts_engine:
                    voice = "my-MM-ThihaNeural" if st.session_state.gender == "Male" else "my-MM-NilarNeural"
                    asyncio.run(generate_premium_voice_and_srt(st.session_state.final_script, voice, "final_voice.mp3", "subtitles.srt"))
                else: 
                    gTTS(text=st.session_state.final_script, lang='my').save("final_voice.mp3")
                
                video, audio = VideoFileClip("temp_video.mp4"), AudioFileClip("final_voice.mp3")
                import moviepy.video.fx.all as vfx
                import moviepy.audio.fx.all as afx
                
                final_v = video.speedx(factor=video.duration/audio.duration).fx(vfx.mirror_x).set_audio(audio)
                w, h = final_v.size
                final_v = final_v.crop(x1=w*0.03, y1=h*0.03, x2=w*0.97, y2=h*0.97).resize(height=720)
                
                if st.session_state.use_bgm:
                    bgm_path = "custom_bgm.mp3" if os.path.exists("custom_bgm.mp3") else f"bgm/narrative.mp3"
                    if os.path.exists(bgm_path):
                        bgm = AudioFileClip(bgm_path).fx(afx.volumex, 0.12).set_duration(audio.duration)
                        final_v = final_v.set_audio(CompositeAudioClip([audio, bgm]))

                final_v.write_videofile("final_merged.mp4", codec="libx264", audio_codec="aac", threads=2, logger=StreamlitLogger())
                
                st.session_state.is_rendered = True 
                st.rerun() 
            except Exception as e: 
                st.error(f"Error: {e}")

    if st.session_state.is_rendered:
        st.success("🎉 ပြီးပါပြီ! Video နှင့် SRT ဖိုင် အဆင်သင့်ဖြစ်ပါပြီ။")
        if os.path.exists("final_merged.mp4"): st.video("final_merged.mp4")
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            if os.path.exists("final_merged.mp4"):
                with open("final_merged.mp4", "rb") as f: st.download_button("📥 Download Video", data=f, file_name="Final_Recap.mp4")
        with col_d2:
            if os.path.exists("subtitles.srt") and "Premium" in st.session_state.tts_engine:
                with open("subtitles.srt", "rb") as f: srt_bytes = f.read()
                st.download_button("📝 Download SRT (Subtitles)", data=srt_bytes, file_name="Subtitles.srt", mime="text/plain")
                
        st.markdown("---")
        
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("⬅️ Back to Editor (စာသားပြန်ပြင်ရန်)"): 
                st.session_state.step = 2
                st.session_state.is_rendered = False
                st.rerun()
        with col_b2:
            if st.button("🔄 New Project (အသစ်ပြန်စရန်)"): reset_project()
