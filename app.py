import streamlit as st
import os
from moviepy import VideoFileClip
import google.generativeai as genai
from gtts import gTTS

st.set_page_config(page_title="Free AI Movie Recap Tool", layout="centered")
st.title("🎥 AI Free Movie Recap Tool (Gemini)")

# Sidebar for API Key
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Enter Google Gemini API Key", type="password")
    st.markdown("[Get Free Key Here](https://aistudio.google.com/app/apikey)")

# Function: Video မှ Audio ထုတ်ယူခြင်း
def extract_audio(video_path, audio_path):
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path)
    return audio_path

# API Key ထည့်ထားမှ အောက်က အဆင့်တွေကို ပြပါမယ်
if api_key:
    genai.configure(api_key=api_key)
    
    # 🌟 လက်ရှိသုံးလို့ရတဲ့ AI Model များကို ဆွဲထုတ်ခြင်း 🌟
    available_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
    except Exception as e:
        st.error(f"API Error: {e}")

    if available_models:
        # Dropdown ဖြင့် Model ရွေးချယ်ခိုင်းခြင်း
        st.success("API Key ချိတ်ဆက်မှု အောင်မြင်ပါသည်။")
        selected_model = st.selectbox("🤖 အသုံးပြုမည့် AI Model ကို ရွေးချယ်ပါ (flash သို့မဟုတ် pro ပါသည်ကို ရွေးပါ)", available_models)
        
        uploaded_file = st.file_uploader("Video ဖိုင် တင်လိုက်ပါ (English Recap)", type=["mp4", "mov"])

        if uploaded_file is not None:
            # ယာယီသိမ်းမည့်နေရာ
            with open("temp_video.mp4", "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.video("temp_video.mp4")

            if st.button("Start Free Processing"):
                with st.spinner("အဆင့် (၁): အသံခွဲထုတ်နေသည်..."):
                    extract_audio("temp_video.mp4", "temp_audio.mp3")
                
                with st.spinner(f"အဆင့် (၂): {selected_model} ဖြင့် နားထောင်ပြီး ဘာသာပြန်နေသည်..."):
                    # အသံဖိုင်ကို Gemini ဆီသို့ တိုက်ရိုက်ပို့ခြင်း
                    audio_file = genai.upload_file(path="temp_audio.mp3")
                    
                    # 🌟 User ရွေးချယ်ထားသော Model ကို အသုံးပြုခြင်း 🌟
                    model = genai.GenerativeModel(selected_model)
                    
                    # Prompt ပေးခြင်း
                    prompt = "You are a professional Burmese movie recap script writer. Listen to this English audio and write an engaging Burmese movie recap script based on it."
                    response = model.generate_content([prompt, audio_file])
                    burmese_script = response.text
                    
                    st.text_area("Burmese Recap Script", burmese_script, height=200)
                
                with st.spinner("အဆင့် (၃): မြန်မာအသံ (Voice-over) ဖန်တီးနေသည်..."):
                    # မြန်မာစာကို အသံပြောင်းခြင်း
                    tts = gTTS(text=burmese_script, lang='my')
                    tts.save("burmese_voice.mp3")
                    
                    st.audio("burmese_voice.mp3")
                    st.success("အားလုံး အောင်မြင်စွာ ပြီးစီးပါပြီ! အပေါ်က မြန်မာ Voice-over ကို Play နှိပ်ပြီး နားထောင်ကြည့်ပါ။")
else:
    st.info("👈 စတင်ရန် ဘယ်ဘက်ဘေးရှိ 'Enter Google Gemini API Key' နေရာတွင် သင်၏ API Key ကို အရင်ထည့်ပါ။")
