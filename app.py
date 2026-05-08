import streamlit as st
import os
from moviepy import VideoFileClip
import google.generativeai as genai
from gtts import gTTS

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
    st.session_state.credits = 231 # အစမ်း Credit ပေးထားခြင်း

# --- UI Header ---
st.markdown('<div class="main-title">🗝️ Golden Key Recap Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Data-Driven AI Video Translation & Dubbing</div>', unsafe_allow_html=True)

# --- Credit Display ---
col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
with col_c2:
    st.markdown(f'<div class="credit-box">💳 Available Credits: {st.session_state.credits}</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

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
            voice_gender = st.selectbox("Voice Identity", ["Female (Nilar)", "Male (Thiha)"])
            # Speed Selection
            voice_speed = st.select_slider("Audio Speed", options=["Slow", "Normal"], value="Normal")
            
        with col2:
            model_choice = st.selectbox("AI Model", available_models if available_models else ["gemini-1.5-flash"])
            # Emotion with Burmese Translation
            emotion = st.selectbox("Select Emotion", [
                "Narrative (ပုံမှန်ပြောပြခြင်း)", 
                "Calm (အေးအေးဆေးဆေး)", 
                "Energetic (တက်ကြွသော)", 
                "Dramatic (စိတ်လှုပ်ရှားဖွယ်)"
            ])

        # --- Test Audio Button ---
        if st.button("🔈 Test Sample Audio (အစမ်းနားထောင်ရန်)"):
            test_text = "မင်္ဂလာပါ၊ Golden Key Studio ကနေ ကြိုဆိုပါတယ်။ အခုကတော့ အသံစမ်းသပ်မှု ဖြစ်ပါတယ်။"
            is_slow = True if voice_speed == "Slow" else False
            test_tts = gTTS(text=test_text, lang='my', slow=is_slow)
            test_tts.save("test_voice.mp3")
            st.audio("test_voice.mp3")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Main Processing ---
        if st.button("🚀 Generate Golden Recap"):
            if st.session_state.credits > 0:
                with st.spinner("Processing..."):
                    # 1. Extract Audio
                    video = VideoFileClip("temp_video.mp4")
                    video.audio.write_audiofile("temp_audio.mp3")
                    
                    # 2. AI Script Generation
                    audio_file = genai.upload_file(path="temp_audio.mp3")
                    model = genai.GenerativeModel(model_choice)
                    prompt = "Write a very concise Burmese movie recap for this audio."
                    response = model.generate_content([prompt, audio_file])
                    burmese_script = response.text
                    
                    # 3. Clean and TTS
                    clean_script = burmese_script.replace("*", "").replace("#", "").replace("_", "")
                    is_slow = True if voice_speed == "Slow" else False
                    tts = gTTS(text=clean_script, lang='my', slow=is_slow)
                    tts.save("burmese_voice.mp3")
                    
                    # Deduct Credit
                    st.session_state.credits -= 1
                    
                    st.success(f"🎉 Done! 1 Credit deducted. Remaining: {st.session_state.credits}")
                    st.text_area("Generated Script", burmese_script, height=150)
                    st.audio("burmese_voice.mp3")
            else:
                st.error("Insufficient credits! Please top up.")

else:
    st.info("👈 Please enter API Key in Configuration to start.")
