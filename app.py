# 🌟 PIL Error Auto-Fix (Must be at the very top) 🌟
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
st.set_page_config(page_title="Shorts Movie Recap Studio", page_icon="🎬", layout="centered")

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

# --- 🌟 API Key Persistence Logic (config.json) 🌟 ---
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
if 'workflow_mode' not in st.session_state: st.session_state.workflow_mode = "Auto"
for k, v in saved_keys.items():
    if k not in st.session_state: st.session_state[k] = v

def next_step(): st.session_state.step += 1
def prev_step(): st.session_state.step -= 1

# --- Force Reset Fix ---
def reset_project():
    gc.collect()
    for f in ["temp_video.mp4", "temp_audio.mp3", "final_voice.mp3", "final_merged.mp4", "subtitles.srt", "custom_bgm.mp3"]:
        try:
            if os.path.exists(f): os.remove(f)
        except: pass
    
    # Preserve Keys, Reset Workflow
    keys_to_keep = {k: st.session_state[k] for k in saved_keys}
    st.session_state.clear()
    for k, v in keys_to_keep.items(): st.session_state[k] = v
    st.session_state.step = 1
    st.rerun()

# --- AI Model Scanners ---
def get_best_gemini_model():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in models:
            if "1.5-flash" in m: return m
        return models[0] if models else "models/gemini-1.5-flash"
    except: return "models/gemini-1.5-flash"

def get_best_groq_chat_model(client):
    try:
        model_ids = [m.id for m in client.models.list().data]
        for preferred in ["llama-3.1-8b-instant", "llama3-8b-8192", "llama-3.1-70b-versatile"]:
            if preferred in model_ids: return preferred
        return model_ids[0]
    except: return "llama-3.1-8b-instant"

# --- AI Executors ---
def execute_gemini_rotation(audio_path, prompt_tone, target_duration, is_long):
    active_keys = [st.session_state[k] for k in ["gemini_1", "gemini_2", "gemini_3"] if st.session_state[k].strip()]
    if not active_keys: raise Exception("Gemini API Key အနည်းဆုံး တစ်ခု လိုအပ်ပါသည်။")
    
    prompt = f"Listen to this audio (auto-detect language) and summarize it into a natural Burmese movie recap script for TikTok in a {prompt_tone} tone. {'Target exactly ' + target_duration.split()[0] + ' minutes.' if is_long else 'Match video length.'} Return ONLY the Burmese text."
    
    for idx, key in enumerate(active_keys):
        try:
            st.write(f">> 🟢 Gemini Key {idx+1} ဖြင့် ကြိုးစားနေပါသည်...")
            genai.configure(api_key=key)
            model = genai.GenerativeModel(get_best_gemini_model())
            audio_file = genai.upload_file(path=audio_path)
            return model.generate_content([prompt, audio_file]).text
        except Exception as e:
            if "429" in str(e) or "Quota" in str(e):
                if idx < len(active_keys) - 1: continue
                else: raise Exception("Gemini Keys အားလုံး Limit ပြည့်သွားပါပြီ။")
            else: raise e

def execute_groq_storytelling(audio_path, prompt_tone):
    if not st.session_state.groq_1.strip(): raise Exception("Groq API Key လိုအပ်ပါသည်။")
    client = Groq(api_key=st.session_state.groq_1)
    
    # Whisper Transcription
    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(file=(audio_path, f.read()), model="whisper-large-v3", response_format="text")
    
    # Transform to Storytelling English for better translation
    st.write(">> 🟠 Groq AI ဖြင့် Storytelling English Script ဖန်တီးနေပါသည်...")
    prompt = f"Rewrite the following transcription into a first-person storytelling movie recap script in English. Use a {prompt_tone} tone. Focus on character feelings and plot twists. Avoid technical terms. \n\nTranscription: {transcription}"
    chat = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=get_best_groq_chat_model(client))
    return chat.choices[0].message.content

# --- TTS Helper ---
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
st.markdown('<div class="main-title">🎬 AI Free Recap Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Multi-Key Persist | Hybrid Workflow | Copyright Pro</div>', unsafe_allow_html=True)

# ==========================================
# WIZARD STEP 1: Settings & Media
# ==========================================
if st.session_state.step == 1:
    st.markdown('<div class="step-header">Step 1: AI Setup & Media Source</div>', unsafe_allow_html=True)
    
    with st.expander("⚙️ API Key Settings (Auto-Saved)", expanded=False):
        col_g1, col_g2, col_g3 = st.columns(3)
        st.session_state.gemini_1 = col_g1.text_input("Gemini Key 1", type="password", value=st.session_state.gemini_1)
        st.session_state.gemini_2 = col_g2.text_input("Gemini Key 2", type="password", value=st.session_state.gemini_2)
        st.session_state.gemini_3 = col_g3.text_input("Gemini Key 3", type="password", value=st.session_state.gemini_3)
        st.session_state.groq_1 = st.text_input("Groq Key (Manual Mode Only)", type="password", value=st.session_state.groq_1)
        if st.button("💾 API Keys သိမ်းမည်"):
            save_keys({k: st.session_state[k] for k in saved_keys})
            st.success("API Keys များအား config.json တွင် သိမ်းဆည်းပြီးပါပြီ!")

    st.markdown("### 📥 Media Source")
    input_method = st.radio("ရွေးချယ်ရန်:", ["Upload Video", "YouTube Link"], horizontal=True, label_visibility="collapsed")
    if input_method == "Upload Video":
        uploaded_file = st.file_uploader("ဗီဒီယိုဖိုင် ရွေးပါ", type=["mp4", "mov"])
        if uploaded_file:
            with open("temp_video.mp4", "wb") as f: f.write(uploaded_file.getbuffer())
            st.success("Video Ready!")
    else:
        youtube_url = st.text_input("Paste YouTube Link Here")
        if st.button("⬇️ Download Video"):
            with st.spinner("Downloading..."):
                try:
                    ydl_opts = {'format': 'best[height<=720]', 'outtmpl': 'temp_video.mp4', 'quiet': True}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([youtube_url])
                    st.success("Download Complete!")
                except Exception as e: st.error(f"Error: {e}")

    st.markdown("### 🎛️ Workflow & Tone")
    col1, col2 = st.columns(2)
    with col1:
        workflow = st.radio("🔄 လုပ်ငန်းစဉ် ရွေးချယ်ရန်", ["Auto Mode (Direct Gemini)", "Manual Mode (Groq Storytelling)"])
        script_tone = st.selectbox("📝 ဇာတ်ညွှန်း ပြောဟန် (Tone)", ["Narrative (ဇာတ်လမ်းပြောဟန်)", "Calm (အေးအေးဆေးဆေး)", "Energetic (တက်တက်ကြွကြွ)", "Dramatic (ခံစားချက်အပြည့်)"])
    with col2:
        tts_engine = st.selectbox("🎙️ Voice Engine", ["Premium (Nilar/Thiha)", "Standard (gTTS)"])
        target_duration = st.selectbox("⏳ အနှစ်ချုပ်မည့်အချိန်", ["3 Minutes", "4 Minutes", "5 Minutes"])
        use_bgm = st.checkbox("🎶 နောက်ခံတီးလုံး (BGM) ထည့်မည်", value=True)

    if st.button("🚀 Next: Generate Script"):
        if not os.path.exists("temp_video.mp4"): st.error("⚠️ ဗီဒီယို အရင်တင်ပါ။")
        else:
            with st.spinner("Processing AI Request..."):
                video_clip = VideoFileClip("temp_video.mp4")
                video_clip.audio.write_audiofile("temp_audio.mp3", logger=None)
                is_long = video_clip.duration > 300
                video_clip.close()
                
                tone_map = {"Narrative": "narrative storytelling", "Calm": "calm", "Energetic": "energetic", "Dramatic": "dramatic"}
                selected_tone = tone_map[script_tone.split(" ")[0]]
                
                try:
                    if "Auto" in workflow:
                        st.session_state.draft_script = execute_gemini_rotation("temp_audio.mp3", selected_tone, target_duration, is_long)
                        st.session_state.workflow_mode = "Auto"
                    else:
                        eng_script = execute_groq_storytelling("temp_audio.mp3", selected_tone)
                        st.session_state.ready_made_prompt = f"Act as a professional movie recapper. Translate this storytelling script into a natural, engaging Burmese script. Return ONLY Burmese text.\n\nEnglish Script:\n{eng_script}"
                        st.session_state.workflow_mode = "Manual"
                        st.session_state.draft_script = ""
                    
                    st.session_state.is_long_video = is_long
                    st.session_state.use_bgm = use_bgm
                    st.session_state.script_tone = script_tone
                    st.session_state.tts_engine = tts_engine
                    st.session_state.step = 2
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

# ==========================================
# WIZARD STEP 2: Editor
# ==========================================
elif st.session_state.step == 2:
    st.markdown('<div class="step-header">Step 2: Script Editor</div>', unsafe_allow_html=True)
    
    if st.session_state.workflow_mode == "Auto":
        st.info("💡 Gemini မှ အလိုအလျောက် ရေးသားထားသော မြန်မာဇာတ်ညွှန်း ဖြစ်ပါသည်။")
        edited_script = st.text_area("Edit Burmese Script:", value=st.session_state.draft_script, height=350)
    else:
        st.warning("💡 Manual Mode: အောက်ပါ Box ညာဘက်အပေါ်ရှိ Copy ကိုနှိပ်၍ Gemini တွင် ဘာသာပြန်ပါ။")
        st.code(st.session_state.ready_made_prompt, language="text")
        edited_script = st.text_area("✍️ Paste your translated Burmese Script here:", value=st.session_state.draft_script, height=250)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Back"): prev_step(); st.rerun()
    with col2:
        if st.button("🎙️ Next: Render Video"):
            if not edited_script.strip(): st.error("⚠️ မြန်မာ ဇာတ်ညွှန်း လိုအပ်ပါသည်။")
            else:
                st.session_state.final_script = edited_script
                next_step(); st.rerun()

# ==========================================
# WIZARD STEP 3: Render
# ==========================================
elif st.session_state.step == 3:
    st.markdown('<div class="step-header">Step 3: Final Rendering</div>', unsafe_allow_html=True)
    
    with st.spinner("Generating Final Output..."):
        try:
            clean_script = st.session_state.final_script.replace("*", "")
            has_srt = False
            
            # Voice Gen
            if "Premium" in st.session_state.tts_engine:
                asyncio.run(generate_premium_voice_and_srt(clean_script, "my-MM-NilarNeural", "final_voice.mp3", "subtitles.srt"))
                has_srt = True
            else:
                gTTS(text=clean_script, lang='my').save("final_voice.mp3")
            
            if st.session_state.is_long_video:
                st.success("Long Video Audio Ready!")
                st.audio("final_voice.mp3")
                if has_srt: st.download_button("📝 Download SRT", data=open("subtitles.srt", "rb"), file_name="Subs.srt")
            else:
                import moviepy.video.fx.all as vfx
                import moviepy.audio.fx.all as afx
                
                video_clip = VideoFileClip("temp_video.mp4")
                voice_audio = AudioFileClip("final_voice.mp3")
                
                # Copyright Safe FX
                processed_video = video_clip.speedx(factor=video_clip.duration/voice_audio.duration).fx(vfx.mirror_x)
                w, h = processed_video.size
                processed_video = processed_video.crop(x1=w*0.03, y1=h*0.03, x2=w*0.97, y2=h*0.97).resize(height=720).fx(vfx.colorx, 1.05).fx(vfx.speedx, 1.01)
                
                final_audio = voice_audio
                if st.session_state.use_bgm:
                    bgm_path = f"bgm/{st.session_state.script_tone.split(' ')[0].lower()}.mp3"
                    if os.path.exists("custom_bgm.mp3"): bgm_path = "custom_bgm.mp3"
                    if os.path.exists(bgm_path):
                        bgm = AudioFileClip(bgm_path).fx(afx.volumex, 0.12).set_duration(voice_audio.duration)
                        final_audio = CompositeAudioClip([voice_audio.set_start(0), bgm.set_start(0)])

                final_video = processed_video.set_audio(final_audio)
                my_logger = StreamlitLogger()
                final_video.write_videofile("final_merged.mp4", codec="libx264", audio_codec="aac", threads=2, logger=my_logger)
                
                video_clip.close(); voice_audio.close(); final_video.close(); gc.collect()
                st.success("🎉 Video Combined Successfully!")
                st.video("final_merged.mp4")
                st.download_button("📥 Download Video", data=open("final_merged.mp4", "rb"), file_name="Final_Recap.mp4")

            st.markdown("---")
            if st.button("🔄 New Project"): reset_project()
        except Exception as e: st.error(f"Error: {e}")
