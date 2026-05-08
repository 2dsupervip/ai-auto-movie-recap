import streamlit as st
import os
from moviepy import VideoFileClip
import google.generativeai as genai
import edge_tts
import asyncio

# --- Page Configuration ---
st.set_page_config(page_title="Golden Key Recap Studio", page_icon="🗝️", layout="centered")

# --- Custom CSS (Golden Key Theme) ---
st.markdown("""
    <style>
    .main-title { font-size: 38px; font-weight: 800; color: #D4AF37; text-align: center; margin-bottom: 5px; }
    .sub-title { text-align: center; color: #A0A0A0; font-size: 14px; margin-bottom: 30px; font-family: monospace;}
    .stButton>button { background-color: #D4AF37; color: #111111; font-weight: 900; border-radius: 8px; width: 100%; transition: 0.3s; }
    .stButton>button:hover { background-color: #FFDF00; color: #000000; transform: scale(1.02); }
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

# --- Async Function for Edge TTS ---
async def generate_voice(text, voice_name, output_filename):
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(output_filename)

# --- API Settings ---
with st.expander("⚙️ API Configuration (Click to Open)", expanded=False):
    api_key = st.text_input("Google Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    available_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name.replace("models/", ""))
    except Exception as e:
        st.error("API ချိတ်ဆက်မှု အဆင်မပြေပါ။ Key မှန်ကန်မှုရှိမရှိ စစ်ဆေးပါ။")

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
            voice_gender = st.selectbox("Voice Identity (Premium Neural)", ["Female (Nilar)", "Male (Thiha)"])
            
        with col2:
            model_choice = st.selectbox("AI Model", available_models if available_models else ["gemini-1.5-flash-latest"])

        st.info("💡 Emotion အစား ပုဒ်ဖြတ်ပုဒ်ရပ် (!, ?, .) များပေါ်မူတည်၍ အသံအတက်အကျ အလိုအလျောက် ပြောင်းလဲပေးမည်ဖြစ်သည်။")

        # --- Test Audio Button ---
        if st.button("🔈 Test Premium Audio (အစမ်းနားထောင်ရန်)"):
            test_text = "မင်္ဂလာပါ၊ Golden Key Studio ကနေ ကြိုဆိုပါတယ်။ ကျွန်မကတော့ နီလာပါ။ ကျွန်တော်ကတော့ သီဟပါ။"
            voice_id = "my-MM-NilarNeural" if voice_gender == "Female (Nilar)" else "my-MM-ThihaNeural"
            
            with st.spinner("အသံဖန်တီးနေသည်..."):
                asyncio.run(generate_voice(test_text, voice_id, "test_voice.mp3"))
                st.audio("test_voice.mp3")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Main Processing ---
        if st.button("🚀 Generate Golden Recap"):
            if st.session_state.credits > 0:
                with st.spinner(">> အဆင့် (၁): ဗီဒီယိုမှ အသံဒေတာ ခွဲထုတ်နေသည်..."):
                    try:
                        video = VideoFileClip("temp_video.mp4")
                        video.audio.write_audiofile("temp_audio.mp3", logger=None)
                    except Exception as e:
                        st.error(f"အသံခွဲထုတ်ရာတွင် အမှားအယွင်းဖြစ်နေပါသည်: {e}")
                    
                with st.spinner(">> အဆင့် (၂): AI မှ Recap ဇာတ်ညွှန်း ရေးသားနေသည်..."):
                    try:
                        audio_file = genai.upload_file(path="temp_audio.mp3")
                        model = genai.GenerativeModel(model_choice)
                        # တိုတိုတုတ်တုတ်ဖြစ်စေရန် တိကျသော Prompt
                        prompt = "You are a professional Burmese movie recap script writer. Listen to this English audio and write an engaging Burmese movie recap script based on it. CRITICAL RULE: The Burmese script MUST be very concise and short. Make sure it takes the exact same amount of time to read as the original English audio. Focus on the main action."
                        response = model.generate_content([prompt, audio_file])
                        burmese_script = response.text
                    except Exception as e:
                        st.error(f"AI Script ရေးသားရာတွင် အမှားအယွင်းဖြစ်နေပါသည်: {e}")
                        burmese_script = ""
                    
                if burmese_script:
                    with st.spinner(">> အဆင့် (၃): Premium Voice-over ဖန်တီးနေသည်..."):
                        # အသံမထွက်ခင် သင်္ကေတများ ရှင်းလင်းခြင်း
                        clean_script = burmese_script.replace("*", "").replace("#", "").replace("_", "")
                        clean_script = clean_script.replace("အသံ:", "").replace("Voiceover:", "").replace("Narrator:", "")
                        
                        # Nilar သို့မဟုတ် Thiha အသံ ရွေးချယ်ခြင်း
                        voice_id = "my-MM-NilarNeural" if voice_gender == "Female (Nilar)" else "my-MM-ThihaNeural"
                        
                        try:
                            asyncio.run(generate_voice(clean_script, voice_id, "burmese_voice.mp3"))
                            
                            st.session_state.credits -= 1
                            
                            st.success(f"🎉 အောင်မြင်ပါပြီ! Remaining Credits: {st.session_state.credits}")
                            st.text_area("📝 Master Script Generated:", burmese_script, height=200)
                            st.audio("burmese_voice.mp3")
                            
                            # ဖိုင်ဒေါင်းလုဒ်လုပ်ရန် ခလုတ်ထည့်ပေးခြင်း
                            with open("burmese_voice.mp3", "rb") as file:
                                st.download_button(
                                    label="💾 Download Voice-over (MP3)",
                                    data=file,
                                    file_name="Golden_Key_Recap_Audio.mp3",
                                    mime="audio/mp3"
                                )
                        except Exception as e:
                            st.error(f"အသံဖန်တီးရာတွင် အမှားအယွင်းဖြစ်နေပါသည်: {e}")
            else:
                st.error("⚠️ Credits မလုံလောက်တော့ပါ။")

else:
    st.info("👈 စတင်ရန် 'API Configuration' တွင် သင်၏ API Key ကို အရင်ထည့်ပါ။")
