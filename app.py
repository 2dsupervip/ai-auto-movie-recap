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
st.set_page_config(page_title="AI Free Recap Studio Pro", page_icon="🎬", layout="centered")

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
for k, v in saved_keys.items():
    if k not in st.session_state: st.session_state[k] = v

def reset_project():
    gc.collect()
    for f in ["temp_video.mp4", "temp_audio.mp3", "final_voice.mp3", "final_merged.mp4", "subtitles.srt", "custom_bgm.mp3"]:
        try:
            if os.path.exists(f): os.remove(f)
        except: pass
    st.session_state.step = 1
    st.rerun()

# --- 🌟 SMART DURATION SCRIPT LOGIC 🌟 ---
def get_prompt_with_limit(duration_seconds, tone):
    # မြန်မာစကားပြောနှုန်း တစ်မိနစ် ၁၄၀ လုံး အကြမ်းဖျဉ်းတွက်ချက်ခြင်း
    duration_minutes = duration_seconds / 60
    word_limit = int(duration_minutes * 140)
    
    return f"""
    Act as a professional Burmese movie recapper. 
    Summarize this video/audio into a natural Burmese storytelling script.
    TONE: {tone}
    TARGET LENGTH: Exactly around {word_limit} Burmese words (to fit {duration_minutes:.1f} minutes of speaking time).
    CRITICAL: Do NOT exceed {word_limit + 20} words. Keep it concise and engaging.
    Return ONLY the Burmese script.
    """

# --- AI Executors ---
def execute_gemini_smart(audio_path, tone, duration):
    active_keys = [st.session_state[k] for k in ["gemini_1", "gemini_2", "gemini_3"] if st.session_state[k].strip()]
    if not active_keys: raise Exception("API Key လိုအပ်ပါသည်။")
    
    prompt = get_prompt_with_limit(duration, tone)
    
    for idx, key in enumerate(active_keys):
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            audio_file = genai.upload_file(path=audio_path)
            response = model.generate_content([prompt, audio_file])
            return response.text
        except Exception as e:
            if "429" in str(e) and idx < len(active_keys) - 1: continue
            else: raise e

# --- UI ---
st.markdown('<h1 style="color:#00E676;text-align:center;">🎬 AI Recap Studio Pro</h1>', unsafe_allow_html=True)

if st.session_state.step == 1:
    with st.expander("⚙️ API Key Settings"):
        st.session_state.gemini_1 = st.text_input("Gemini Key 1", type="password", value=st.session_state.gemini_1)
        st.session_state.groq_1 = st.text_input("Groq Key", type="password", value=st.session_state.groq_1)
        if st.button("💾 Save Keys"): save_keys({k: st.session_state[k] for k in saved_keys}); st.success("Saved!")

    uploaded_file = st.file_uploader("ဗီဒီယိုတင်ပါ", type=["mp4", "mov"])
    
    col1, col2 = st.columns(2)
    tone = col1.selectbox("ပြောဟန် ရွေးပါ", ["Narrative (ဇာတ်လမ်းပြောဟန်)", "Dramatic (ခံစားချက်အပြည့်)", "Energetic (တက်တက်ကြွကြွ)"])
    workflow = col2.radio("လုပ်ငန်းစဉ်", ["Auto (Gemini)", "Manual (Groq)"])

    if st.button("🚀 Next: Generate Script") and uploaded_file:
        with open("temp_video.mp4", "wb") as f: f.write(uploaded_file.getbuffer())
        with st.spinner("Analyzing Video..."):
            clip = VideoFileClip("temp_video.mp4")
            st.session_state.video_duration = clip.duration
            clip.audio.write_audiofile("temp_audio.mp3", logger=None)
            clip.close()
            
            try:
                if "Auto" in workflow:
                    st.session_state.draft_script = execute_gemini_smart("temp_audio.mp3", tone, st.session_state.video_duration)
                    st.session_state.workflow_mode = "Auto"
                else:
                    client = Groq(api_key=st.session_state.groq_1)
                    with open("temp_audio.mp3", "rb") as f:
                        transcription = client.audio.transcriptions.create(file=("temp_audio.mp3", f.read()), model="whisper-large-v3", response_format="text")
                    # Manual Prompt with Word Limit
                    limit = int((st.session_state.video_duration/60)*140)
                    st.session_state.ready_made_prompt = f"Summarize this into Burmese ({tone}) around {limit} words:\n\n{transcription}"
                    st.session_state.workflow_mode = "Manual"
                
                st.session_state.step = 2
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

elif st.session_state.step == 2:
    st.markdown("### Step 2: Script Editor")
    if st.session_state.workflow_mode == "Auto":
        # 🌟 Copy Box (Code Block) စနစ်ဖြင့် ပြသခြင်း 🌟
        st.info("အောက်က Box ထဲမှာ ကလစ်နှိပ်ပြီး ဇာတ်ညွှန်းကို Copy ကူးနိုင်ပါတယ်။")
        st.code(st.session_state.draft_script, language="markdown")
        edited_script = st.text_area("✍️ လိုအပ်တာ ပြင်ဆင်ပါ -", value=st.session_state.draft_script, height=300)
    else:
        st.code(st.session_state.ready_made_prompt, language="text")
        edited_script = st.text_area("✍️ ဘာသာပြန်ထားတာ ထည့်ပါ -", height=300)

    col1, col2 = st.columns(2)
    if col1.button("⬅️ Back"): st.session_state.step = 1; st.rerun()
    if col2.button("🎙️ Next: Render Video"):
        st.session_state.final_script = edited_script
        st.session_state.step = 3
        st.rerun()

elif st.session_state.step == 3:
    with st.spinner("Rendering Final Video..."):
        try:
            asyncio.run(edge_tts.Communicate(st.session_state.final_script, "my-MM-NilarNeural").save("final_voice.mp3"))
            
            video = VideoFileClip("temp_video.mp4")
            audio = AudioFileClip("final_voice.mp3")
            
            # 🌟 Sync Logic: ဗီဒီယိုကို အသံနဲ့အညီ အမြန်နှုန်းချိန်ညှိခြင်း 🌟
            final_video = video.speedx(factor=video.duration/audio.duration).set_audio(audio)
            
            # Copyright FX
            import moviepy.video.fx.all as vfx
            w, h = final_video.size
            final_video = final_video.fx(vfx.mirror_x).crop(x1=w*0.03, y1=h*0.03, x2=w*0.97, y2=h*0.97)
            
            my_logger = StreamlitLogger()
            final_video.write_videofile("final_merged.mp4", codec="libx264", audio_codec="aac", threads=2, logger=my_logger)
            
            st.success("ပြီးပါပြီ!")
            st.video("final_merged.mp4")
            st.download_button("📥 Download", data=open("final_merged.mp4", "rb"), file_name="Final_Recap.mp4")
            if st.button("🔄 New Project"): reset_project()
        except Exception as e: st.error(f"Render Error: {e}")
