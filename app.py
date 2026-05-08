import streamlit as st
import os
import gc
import asyncio
import google.generativeai as genai
import edge_tts
import yt_dlp
from moviepy import VideoFileClip

# --- Page Configuration ---
st.set_page_config(page_title="Golden Key Recap Studio", page_icon="🗝️", layout="centered")

# --- Custom CSS ---
st.markdown("""
    <style>
    .main-title { font-size: 38px; font-weight: 800; color: #D4AF37; text-align: center; margin-bottom: 5px; }
    .sub-title { text-align: center; color: #A0A0A0; font-size: 14px; margin-bottom: 30px; font-family: monospace;}
    .step-header { color: #D4AF37; font-weight: bold; font-size: 20px; border-bottom: 1px solid #D4AF37; padding-bottom: 10px; margin-bottom: 20px; }
    .stButton>button { background-color: #D4AF37; color: #111111; font-weight: bold; border-radius: 8px; width: 100%; transition: 0.3s; }
    .stButton>button:hover { background-color: #FFDF00; color: #000000; }
    </style>
""", unsafe_allow_html=True)

# --- Initial Session States for Wizard UI ---
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'draft_script' not in st.session_state:
    st.session_state.draft_script = ""
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""

def next_step():
    st.session_state.step += 1

def prev_step():
    st.session_state.step -= 1

# --- Helper Functions ---
async def generate_voice(text, voice_name, output_filename):
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(output_filename)

def download_youtube_video(url, output_path="downloaded_video.mp4"):
    ydl_opts = {
        'format': 'best[height<=720]', # 720p အများဆုံးဆွဲမည် (Memory သက်သာစေရန်)
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return output_path

# --- UI Header ---
st.markdown('<div class="main-title">🗝️ Golden Key Recap Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">YouTube to TikTok AI Generator</div>', unsafe_allow_html=True)

# ==========================================
# WIZARD STEP 1: Setup & Download
# ==========================================
if st.session_state.step == 1:
    st.markdown('<div class="step-header">Step 1: Configuration & Media Setup</div>', unsafe_allow_html=True)
    
    # API Key Input (Saves in session)
    api_key_input = st.text_input("Google Gemini API Key", type="password", value=st.session_state.api_key)
    if api_key_input:
        st.session_state.api_key = api_key_input
        genai.configure(api_key=st.session_state.api_key)
    
    st.markdown("### 📥 Input Source")
    youtube_url = st.text_input("Paste YouTube Recap Link Here", placeholder="https://www.youtube.com/watch?v=...")
    
    st.markdown("### 🎛️ Generation Settings")
    col1, col2 = st.columns(2)
    with col1:
        voice_gender = st.selectbox("Premium Voice", ["Female (Nilar)", "Male (Thiha)"])
    with col2:
        target_duration = st.selectbox("Target Output Duration", ["3 Minutes", "4 Minutes", "5 Minutes"])
        
    if st.button("🚀 Next: Analyze & Generate Script"):
        if not st.session_state.api_key:
            st.error("⚠️ ကျေးဇူးပြု၍ API Key အရင်ထည့်ပါ။")
        elif not youtube_url:
            st.error("⚠️ YouTube Link ထည့်ရန် လိုအပ်ပါသည်။")
        else:
            with st.spinner(">> ဗီဒီယိုကို YouTube မှ ဒေါင်းလုဒ်ဆွဲနေပါသည်... (ခဏစောင့်ပါ)"):
                try:
                    if os.path.exists("downloaded_video.mp4"):
                        os.remove("downloaded_video.mp4")
                    download_youtube_video(youtube_url)
                    
                    with st.spinner(">> အသံဖိုင်ခွဲထုတ်နေပါသည်..."):
                        video_clip = VideoFileClip("downloaded_video.mp4")
                        video_clip.audio.write_audiofile("temp_audio.mp3", logger=None)
                        video_clip.close()
                        gc.collect() # Free up RAM
                    
                    with st.spinner(">> AI မှ သတ်မှတ်ချိန်အတိုင်း အနှစ်ချုပ်ဇာတ်ညွှန်း ရေးသားနေပါသည်..."):
                        audio_file = genai.upload_file(path="temp_audio.mp3")
                        model = genai.GenerativeModel("gemini-1.5-flash-latest")
                        
                        # မိနစ်အလိုက် Prompt ကို ချိန်ညှိခြင်း
                        duration_mins = target_duration.split()[0]
                        prompt = f"Listen to this English movie recap audio. Summarize the entire plot into an engaging, fast-paced Burmese script designed for a TikTok video. CRITICAL: The script MUST take exactly {duration_mins} minutes to read out loud. Focus only on the main storyline and exciting moments. Do not use asterisks or markdown formatting."
                        
                        response = model.generate_content([prompt, audio_file])
                        st.session_state.draft_script = response.text
                        st.session_state.voice_gender = voice_gender
                        
                        next_step()
                        st.rerun()
                except Exception as e:
                    st.error(f"Error အမှားအယွင်းဖြစ်နေပါသည်: {e}")

# ==========================================
# WIZARD STEP 2: Human-in-the-Loop Editor
# ==========================================
elif st.session_state.step == 2:
    st.markdown('<div class="step-header">Step 2: Script Editor (Human-in-the-Loop)</div>', unsafe_allow_html=True)
    st.info("💡 အောက်ပါ ဇာတ်ညွှန်းသည် AI မှ ရေးသားထားခြင်းဖြစ်သည်။ မိမိစိတ်ကြိုက် အသုံးအနှုန်းများ ဝင်ရောက်ပြင်ဆင်နိုင်ပါသည်။")
    
    edited_script = st.text_area("📝 Edit Burmese Script Here:", value=st.session_state.draft_script, height=300)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Back"):
            prev_step()
            st.rerun()
    with col2:
        if st.button("🎙️ Next: Generate Final Voice"):
            st.session_state.final_script = edited_script
            next_step()
            st.rerun()

# ==========================================
# WIZARD STEP 3: Final Export
# ==========================================
elif st.session_state.step == 3:
    st.markdown('<div class="step-header">Step 3: Final Assets Export</div>', unsafe_allow_html=True)
    
    with st.spinner(">> Premium Voice-over အသံဖိုင် ဖန်တီးနေပါသည်..."):
        try:
            clean_script = st.session_state.final_script.replace("*", "").replace("#", "")
            voice_id = "my-MM-NilarNeural" if "Nilar" in st.session_state.voice_gender else "my-MM-ThihaNeural"
            
            asyncio.run(generate_voice(clean_script, voice_id, "final_voice.mp3"))
            st.success("🎉 အားလုံးလုပ်ဆောင်ပြီးစီးပါပြီ! အောက်တွင် ဒေါင်းလုဒ်ရယူပါ။")
            
            st.audio("final_voice.mp3")
            
            st.markdown("### 📥 Download Your Assets (CapCut ထဲသို့ ထည့်ရန်)")
            
            # Download Original Raw Video
            if os.path.exists("downloaded_video.mp4"):
                with open("downloaded_video.mp4", "rb") as file:
                    st.download_button(
                        label="🎥 1. Download Raw Video (ကုန်ကြမ်း ဗီဒီယို)",
                        data=file,
                        file_name="GoldenKey_Raw_Video.mp4",
                        mime="video/mp4"
                    )
            
            # Download Final Pro Audio
            if os.path.exists("final_voice.mp3"):
                with open("final_voice.mp3", "rb") as file:
                    st.download_button(
                        label="🎙️ 2. Download Pro Voice-over (မြန်မာအသံဖိုင်)",
                        data=file,
                        file_name="GoldenKey_Pro_Audio.mp3",
                        mime="audio/mp3"
                    )
            
            st.info("📌 အထက်ပါ ဖိုင် (၂) ခုကို ဒေါင်းလုဒ်ဆွဲပြီး CapCut အတွင်း ထည့်သွင်းကာ စိတ်ကြိုက် ဖြတ်ဆက်ပြုလုပ်နိုင်ပါပြီ။")
            
            if st.button("🔄 Start New Project"):
                st.session_state.step = 1
                st.rerun()
                
        except Exception as e:
            st.error(f"အသံဖန်တီးရာတွင် အမှားအယွင်းဖြစ်နေပါသည်: {e}")
