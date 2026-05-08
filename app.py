import streamlit as st
import os
from moviepy import VideoFileClip
import google.generativeai as genai
from gtts import gTTS

# Page Configuration
st.set_page_config(page_title="Golden Key Recap Studio", page_icon="🗝️", layout="centered")

# --- Custom CSS လှလှလေး ထည့်ခြင်း (Minimalist & Professional Vibe) ---
st.markdown("""
    <style>
    /* ခေါင်းစဉ် ဒီဇိုင်း */
    .main-title {
        font-size: 40px;
        font-weight: 800;
        color: #D4AF37;
        text-align: center;
        margin-bottom: 5px;
        letter-spacing: 1.5px;
    }
    /* Subtitle ဒီဇိုင်း */
    .sub-title {
        text-align: center;
        color: #A0A0A0;
        font-size: 16px;
        margin-bottom: 35px;
        font-family: 'Courier New', Courier, monospace;
    }
    /* ခလုတ် ဒီဇိုင်း (ရွှေရောင်) */
    .stButton>button {
        background-color: #D4AF37;
        color: #111111;
        font-weight: 900;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #FFDF00;
        color: #000000;
        transform: scale(1.02);
    }
    /* Expander ဒီဇိုင်း */
    .streamlit-expanderHeader {
        font-weight: bold;
        color: #D4AF37;
    }
    </style>
""", unsafe_allow_html=True)

# --- UI Header ---
st.markdown('<div class="main-title">🗝️ Golden Key Recap Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Data-Driven AI Video Translation & Dubbing</div>', unsafe_allow_html=True)

# --- API Settings (Expander နဲ့ သပ်သပ်ရပ်ရပ် ဖျောက်ထားမည်) ---
with st.expander("⚙️ API Configuration (စတင်ရန် နှိပ်ပါ)", expanded=True):
    api_key = st.text_input("Google Gemini API Key", type="password", help="သင်၏ အခမဲ့ Gemini Key ကို ဤနေရာတွင် ထည့်ပါ။")

# API Key ထည့်ပြီးမှ အောက်ပိုင်းကို ဆက်လုပ်ပါမည်
if api_key:
    genai.configure(api_key=api_key)
    
    # 🌟 လက်ရှိသုံးလို့ရတဲ့ AI Model များကို အလိုအလျောက် ဆွဲထုတ်ခြင်း (Error ကင်းစင်စေရန်) 🌟
    available_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # နာမည်ထဲက 'models/' ဆိုတာကို ဖြုတ်ပြီး အလွယ်တကူရွေးနိုင်အောင် လုပ်ပေးခြင်း
                model_name = m.name.replace("models/", "")
                available_models.append(model_name)
    except Exception as e:
        st.error(f"API Error: {e}")

    if available_models:
        # --- Main Video Upload Section ---
        st.markdown("### 🎬 Media Upload")
        uploaded_file = st.file_uploader("Drop your English Recap Video here (MP4/MOV)", type=["mp4", "mov"], label_visibility="collapsed")

        if uploaded_file is not None:
            # ယာယီသိမ်းမည့်နေရာ
            with open("temp_video.mp4", "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.video("temp_video.mp4")
            
            # --- Studio Settings ---
            st.markdown("### 🎛️ Studio Settings")
            
            col1, col2 = st.columns(2)
            with col1:
                project_name = st.text_input("Project Name", value="Recap_Project_01")
                voice_gender = st.selectbox("Voice Identity", ["Female (Nilar)", "Male (Thiha)"])
            with col2:
                # 🌟 ရရှိနိုင်သော Model များကိုသာ Dropdown တွင် ပြပေးမည် 🌟
                model_choice = st.selectbox("AI Model", available_models)
                emotion = st.selectbox("Emotion", ["Narrative", "Calm", "Energetic", "Dramatic"])
            
            st.markdown("<br>", unsafe_allow_html=True) # Space လေးခြားရန်
            
            # --- Processing Action ---
            if st.button("🚀 Generate Golden Recap", use_container_width=True):
                with st.spinner(">> အဆင့် (၁): အသံဒေတာ ခွဲထုတ်နေသည်..."):
                    video = VideoFileClip("temp_video.mp4")
                    video.audio.write_audiofile("temp_audio.mp3")
                    
                with st.spinner(f">> အဆင့် (၂): {model_choice} ဖြင့် Script ရေးသားနေသည်..."):
                    audio_file = genai.upload_file(path="temp_audio.mp3")
                    model = genai.GenerativeModel(model_choice)
                    
                    prompt = "You are a professional Burmese movie recap script writer. Listen to this English audio and write an engaging Burmese movie recap script based on it. CRITICAL RULE: The Burmese script MUST be very concise and short. Make sure it takes the exact same amount of time to read as the original English audio."
                    response = model.generate_content([prompt, audio_file])
                    burmese_script = response.text
                    
                    # Text area တွင် ရလဒ်ပြခြင်း
                    st.text_area("📝 Master Script Generated:", burmese_script, height=200)
                    
                with st.spinner(">> အဆင့် (၃): မြန်မာ Voice-over ဖန်တီးနေသည်..."):
                    clean_script = burmese_script.replace("*", "").replace("#", "").replace("_", "")
                    clean_script = clean_script.replace("အသံ:", "").replace("Voiceover:", "").replace("Narrator:", "")
                    
                    tts = gTTS(text=clean_script, lang='my')
                    tts.save("burmese_voice.mp3")
                    
                    st.success("🎉 အားလုံးအောင်မြင်စွာ ပြီးစီးပါပြီ!")
                    st.audio("burmese_voice.mp3")
