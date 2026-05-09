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
    .main-title { font-size: 36px; font-weight: 800; color: #00E676; text-align: center; margin-bottom: 5px; }
    .sub-title { text-align: center; color: #A0A0A0; font-size: 14px; margin-bottom: 30px; font-family: monospace;}
    .step-header { color: #00E676; font-weight: bold; font-size: 20px; border-bottom: 1px solid #00E676; padding-bottom: 10px; margin-bottom: 20px; }
    .stButton>button { background-color: #00E676; color: #111111; font-weight: bold; border-radius: 8px; width: 100%; transition: 0.3s; }
    .stButton>button:hover { background-color: #B2FF59; color: #000000; }
    </style>
""", unsafe_allow_html=True)

# --- Init Persistent API Storage ---
API_FILE = "api_config.json"
saved_gemini = ""
saved_groq = ""
if os.path.exists(API_FILE):
    with open(API_FILE, "r") as f: 
        data = json.load(f)
        saved_gemini = data.get("gemini_key", "")
        saved_groq = data.get("groq_key", "")

# --- Initial Session States ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'draft_script' not in st.session_state: st.session_state.draft_script = ""
if 'gemini_key' not in st.session_state: st.session_state.gemini_key = saved_gemini
if 'groq_key' not in st.session_state: st.session_state.groq_key = saved_groq

def next_step(): st.session_state.step += 1
def prev_step(): st.session_state.step -= 1

def reset_project():
    for f in ["temp_video.mp4", "temp_audio.mp3", "final_voice.mp3", "final_merged.mp4", "subtitles.srt", "custom_bgm.mp3"]:
        if os.path.exists(f): os.remove(f)
    st.session_state.clear()
    st.session_state.gemini_key = saved_gemini 
    st.session_state.groq_key = saved_groq
    st.session_state.step = 1
    st.rerun()

# --- AI Model Auto-Detector ---
def get_best_gemini_model():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in models:
            if "1.5-flash" in m: return m
        for m in models:
            if "1.5-pro" in m: return m
        return models[0] if models else "models/gemini-1.5-flash"
    except:
        return "models/gemini-1.5-flash"

# --- 🌟 SMART HYBRID AI ENGINE 🌟 ---
def generate_script_hybrid(audio_path, prompt_tone, target_duration, is_long):
    prompt_instruction = f"Summarize this movie plot into an engaging Burmese script for TikTok in a {prompt_tone} tone. {'Target exactly ' + target_duration.split()[0] + ' minutes to read.' if is_long else 'Match original video length.'} Focus only on the main storyline. No markdown."
    
    # 1. Try Gemini First (Primary Engine)
    try:
        st.write(">> 🟢 Gemini AI ဖြင့် ဇာတ်ညွှန်း ရေးသားနေပါသည်...")
        genai.configure(api_key=st.session_state.gemini_key)
        best_model_name = get_best_gemini_model()
        model = genai.GenerativeModel(best_model_name)
        audio_file = genai.upload_file(path=audio_path)
        response = model.generate_content([prompt_instruction, audio_file])
        return response.text
        
    except Exception as gemini_err:
        err_msg = str(gemini_err)
        # Check if it's a Limit Error
        if "429" in err_msg or "Quota" in err_msg or "ResourceExhausted" in err_msg:
            if not st.session_state.groq_key:
                raise Exception("Gemini Limit ပြည့်သွားပါသည်။ Groq API Key ထည့်ထားခြင်း မရှိသဖြင့် အလုပ်ရပ်နားလိုက်ပါသည်။")
            
            # 2. Fallback to Groq (Secondary Engine)
            st.warning("⚠️ Gemini Limit ပြည့်သွားသဖြင့် Groq AI သို့ အလိုအလျောက် ကူးပြောင်းနေပါသည်...")
            client = Groq(api_key=st.session_state.groq_key)
            
            # Step 2a: Whisper to Text
            st.write(">> 🟠 Groq AI (Whisper) ဖြင့် အသံအား စာသားပြောင်းနေပါသည်...")
            with open(audio_path, "rb") as file:
                transcription = client.audio.transcriptions.create(
                  file=(audio_path, file.read()),
                  model="whisper-large-v3",
                  response_format="text"
                )
            eng_text = transcription
            
            # Step 2b: Llama3 to Burmese Script
            st.write(">> 🟠 Groq AI (Llama 3) ဖြင့် မြန်မာဇာတ်ညွှန်း ရေးသားနေပါသည်...")
            llama_prompt = f"Translate and summarize the following English text into an engaging Burmese script for TikTok in a {prompt_tone} tone. Return ONLY the Burmese script. No markdown formatting. \n\nEnglish Text: {eng_text}"
            
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": llama_prompt}],
                model="llama3-8b-8192",
            )
            return chat_completion.choices[0].message.content
        else:
            raise Exception(f"Gemini Error: {gemini_err}")

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
st.markdown('<div class="sub-title">Smart Hybrid AI Engine (Gemini + Groq Fallback)</div>', unsafe_allow_html=True)

# ==========================================
# WIZARD STEP 1: Setup & Media Input
# ==========================================
if st.session_state.step == 1:
    st.markdown('<div class="step-header">Step 1: Setup & Configuration</div>', unsafe_allow_html=True)
    
    col_k1, col_k2, col_k3 = st.columns([2, 2, 1])
    with col_k1:
        gemini_input = st.text_input("🔑 Google Gemini API Key", type="password", value=st.session_state.gemini_key)
    with col_k2:
        groq_input = st.text_input("🔑 Groq API Key (Fallback)", type="password", value=st.session_state.groq_key)
    with col_k3:
        st.write(""); st.write("")
        if st.button("💾 သိမ်းမည်"):
            with open(API_FILE, "w") as f: 
                json.dump({"gemini_key": gemini_input, "groq_key": groq_input}, f)
            st.session_state.gemini_key = gemini_input
            st.session_state.groq_key = groq_input
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
        script_tone = st.selectbox("📝 ဇာတ်ညွှန်း ပြောဟန် (Script Tone)", ["Narrative (ဇာတ်လမ်းပြောဟန်)", "Calm (အေးအေးဆေးဆေး)", "Energetic (တက်တက်ကြွကြွ)", "Dramatic (ခံစားချက်အပြည့်)"])
        use_bgm = st.checkbox("🎶 နောက်ခံတီးလုံး (BGM) ထည့်မည်", value=True)
    with col2:
        tts_engine = st.selectbox("🎙️ Voice Engine", ["Premium (Nilar/Thiha)", "Standard (gTTS)"])
        target_duration = st.selectbox("⏳ အနှစ်ချုပ်မည့်အချိန် (Long Video များအတွက်)", ["3 Minutes", "4 Minutes", "5 Minutes"])
        if "Premium" in tts_engine:
            voice_gender = st.selectbox("🗣️ Premium Voice အသံ", ["Female (Nilar)", "Male (Thiha)"])
        else:
            voice_gender = "None"

    custom_bgm_file = st.file_uploader("📂 ကိုယ်ပိုင်တီးလုံးတင်ရန် (မဖြစ်မနေမဟုတ်ပါ)", type=["mp3"])
    if custom_bgm_file:
        with open("custom_bgm.mp3", "wb") as f: f.write(custom_bgm_file.getbuffer())

    if st.button("🚀 Next: Generate Script"):
        if not st.session_state.gemini_key: st.error("⚠️ Gemini API Key အနည်းဆုံး လိုအပ်ပါသည်။")
        elif not os.path.exists("temp_video.mp4"): st.error("⚠️ ဗီဒီယို အရင်တင်ပါ။")
        else:
            with st.spinner("Analyzing Audio & Generating Script..."):
                video_clip = VideoFileClip("temp_video.mp4")
                video_clip.audio.write_audiofile("temp_audio.mp3", logger=None)
                is_long = video_clip.duration > 300
                video_clip.close()
                gc.collect()
                
                tone_map = {
                    "Narrative (ဇာတ်လမ်းပြောဟန်)": "narrative storytelling",
                    "Calm (အေးအေးဆေးဆေး)": "calm and relaxing",
                    "Energetic (တက်တက်ကြွကြွ)": "highly energetic and enthusiastic",
                    "Dramatic (ခံစားချက်အပြည့်)": "intensely dramatic and emotional"
                }
                selected_tone = tone_map[script_tone]
                
                try:
                    # Execute Hybrid Logic
                    final_draft = generate_script_hybrid("temp_audio.mp3", selected_tone, target_duration, is_long)
                    
                    st.session_state.draft_script = final_draft
                    st.session_state.is_long_video = is_long
                    st.session_state.use_bgm = use_bgm
                    st.session_state.script_tone = script_tone
                    st.session_state.tts_engine = tts_engine
                    st.session_state.voice_gender = voice_gender
                    next_step()
                    st.rerun()
                except Exception as e:
                    st.error(f"Processing Error: {e}")

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
            clean_script = st.session_state.final_script.replace("*", "")
            has_srt = False
            
            if "Premium" in st.session_state.tts_engine:
                voice_id = "my-MM-NilarNeural" if "Nilar" in st.session_state.voice_gender else "my-MM-ThihaNeural"
                asyncio.run(generate_premium_voice_and_srt(clean_script, voice_id, "final_voice.mp3", "subtitles.srt"))
                has_srt = True
            else:
                gTTS(text=clean_script, lang='my').save("final_voice.mp3")
            
            if st.session_state.is_long_video:
                st.success("Long Video အား အနှစ်ချုပ် အသံဖိုင် ထုတ်ပေးပြီးပါပြီ!")
                st.audio("final_voice.mp3")
                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    with open("final_voice.mp3", "rb") as f: st.download_button("🎙️ Download Audio Only", data=f, file_name="Recap_Audio.mp3", mime="audio/mp3")
                if has_srt:
                    with col_dl2:
                        if os.path.exists("subtitles.srt"):
                            with open("subtitles.srt", "rb") as f: st.download_button("📝 Download SRT File", data=f, file_name="Subs.srt", mime="text/plain")
            else:
                import moviepy.video.fx.all as vfx
                import moviepy.audio.fx.all as afx
                
                video_clip = VideoFileClip("temp_video.mp4")
                voice_audio = AudioFileClip("final_voice.mp3")
                
                speed_factor = video_clip.duration / voice_audio.duration
                processed_video = video_clip.speedx(factor=speed_factor).fx(vfx.mirror_x)
                w, h = processed_video.size
                
                processed_video = processed_video.crop(x1=w*0.03, y1=h*0.03, x2=w*0.97, y2=h*0.97)
                processed_video = processed_video.resize(height=720).fx(vfx.colorx, 1.05).fx(vfx.speedx, 1.01)
                
                final_audio = voice_audio
                if st.session_state.use_bgm:
                    bgm_name = st.session_state.script_tone.split(" ")[0].lower()
                    bgm_path = "custom_bgm.mp3" if os.path.exists("custom_bgm.mp3") else f"bgm/{bgm_name}.mp3"
                    
                    if os.path.exists(bgm_path):
                        bgm = AudioFileClip(bgm_path).fx(afx.volumex, 0.12).set_duration(voice_audio.duration)
                        final_audio = CompositeAudioClip([voice_audio.set_start(0), bgm.set_start(0)])

                final_video = processed_video.set_audio(final_audio)
                
                my_logger = StreamlitLogger()
                final_video.write_videofile("final_merged.mp4", codec="libx264", audio_codec="aac", threads=2, logger=my_logger)
                
                video_clip.close()
                voice_audio.close()
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
            if st.button("🔄 New Project (Reset)"): reset_project()
            
        except Exception as e:
            st.error(f"Processing Error: {e}")
