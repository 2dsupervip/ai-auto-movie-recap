import streamlit as st
import os
from moviepy import VideoFileClip
import google.generativeai as genai
import edge_tts
import asyncio

# Page Configuration
st.set_page_config(page_title="Golden Key Recap Studio", page_icon="🗝️", layout="centered")

# Custom CSS for Styling
st.markdown("""
    <style>
    .main-title { font-size: 38px; font-weight: 800; color: #D4AF37; text-align: center; }
    .sub-title { text-align: center; color: #A0A0A0; font-size: 14px; margin-bottom: 30px; }
    .stButton>button { background-color: #D4AF37; color: #111111; font-weight: 900; border-radius: 8px; width: 100%; }
    .credit-box { background-color: #262730; border: 1px solid #D4AF37; padding: 10px; border-radius: 10px; text-align: center; color: #D4AF37; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- Initial Session State for Credits ---
if 'credits' not in st.session_state:
    st.session_state.credits = 231 

# --- UI Header ---
st.markdown('<div class="main-title">🗝️ Golden Key Recap Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Data-Driven AI Video Translation & Dubbing</div>', unsafe_allow_html=True)

# --- Credit Display ---
col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
with col_c2:
    st.markdown(f'<div class="credit-box">💳 Available Credits: {st.session_state.credits}</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- Async Function for Edge TTS (Free Azure Voices) ---
async def generate_voice(text, voice_name, output_filename):
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(output_filename)

# --- API Settings ---
with st.expander("⚙️ API Configuration", expanded=False):
    api_key = st.text_input("Google Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    available_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name.replace("models/", ""))
    except: pass

    # --- Media Upload ---
    st.markdown("### 🎬 Media Upload")
    uploaded_file = st.file_uploader("Upload English Video", type=["mp4", "mov"], label_visibility="collapsed")

    if uploaded_file:
        with open("temp_video.mp4", "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.video("temp_video.mp4")

        # --- Studio Settings ---
        st.markdown("### 🎛️ Studio Settings")
        col1, col2 = st.columns(2)
        
        with col1:
            voice_gender = st.selectbox("Voice Identity (Premium)", ["Female (Nilar)", "Male (Thiha)"])
            
        with col2:
            model_choice = st.selectbox("AI Model", available_models if available_models else ["gemini-1.5-flash"])

        st.info("💡 ဤ App သည် ကတ်မလိုသော Free Edge-TTS (Azure Neural) ကို အသုံးပြုထားသဖြင့် Nilar/Thiha အသံများ သဘာဝကျကျ ထွက်ပေါ်မည်ဖြစ်ပါသည်။")

        # --- Test Audio Button ---
        if st.button("🔈 Test Premium Audio (အစမ်းနားထောင်ရန်)"):
            test_text = "မင်္ဂလာပါ၊ Golden Key Studio ကနေ ကြိုဆိုပါတယ်။ ကျွန်မကတော့ နီလာပါ။ ကျွန်တော်ကတော့ သီဟပါ။"
            voice_id = "my-MM-NilarNeural" if voice_gender == "Female (Nilar)" else "my-MM-ThihaNeural"
            
            asyncio.run(generate_voice(test_text, voice_id, "test_voice.mp3"))
            st.audio("test_voice.mp3")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Main Processing ---
        if st.button("🚀 Generate Golden Recap"):
            if st.session_state.credits > 0:
                with st.spinner(">> အဆင့် (၁): အသံခွဲထုတ်နေသည်..."):
                    video = VideoFileClip("temp_video.mp4")
                    video.audio.write_audiofile("temp_audio.mp3")
                    
                with st.spinner(">> အဆင့် (၂): AI Script ရေးသားနေသည်..."):
                    audio_file = genai.upload_file(path="temp_audio.mp3")
                    model = genai.GenerativeModel(model_choice)
                    prompt = "Write a very concise Burmese movie recap for this audio. Make sure it takes the exact same amount of time to read as the original English audio."
                    response = model.generate_content([prompt, audio_file])
                    burmese_script = response.text
                    
                with st.spinner(">> အဆင့် (၃): Premium Voice-over ဖန်တီးနေသည်..."):
                    clean_script = burmese_script.replace("*", "").replace("#", "").replace("_", "")
                    clean_script = clean_script.replace("အသံ:", "").replace("Voiceover:", "").replace("Narrator:", "")
                    
                    # Nilar သို့မဟုတ် Thiha အသံ ရွေးချယ်ခြင်း
                    voice_id = "my-MM-NilarNeural" if voice_gender == "Female (Nilar)" else "my-MM-ThihaNeural"
                    
                    # Edge TTS ဖြင့် အသံဖန်တီးခြင်း
                    asyncio.run(generate_voice(clean_script, voice_id, "burmese_voice.mp3"))
                    
                    st.session_state.credits -= 1
                    
                    st.success(f"🎉 အောင်မြင်ပါပြီ! Remaining Credits: {st.session_state.credits}")
                    st.text_area("Generated Script", burmese_script, height=150)
                    st.audio("burmese_voice.mp3")
            else:
                st.error("Insufficient credits!")

else:
    st.info("👈 Please enter API Key in Configuration to start.")
