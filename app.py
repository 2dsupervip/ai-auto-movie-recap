import streamlit as st
import os
from moviepy.editor import VideoFileClip
import openai

st.set_page_config(page_title="AI Movie Recap Tool", layout="centered")
st.title("🎥 AI One-Click Movie Recap Tool")

# Sidebar for API Key
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Enter OpenAI API Key", type="password")
    if api_key:
        openai.api_key = api_key

# Function: Video မှ Audio ထုတ်ယူခြင်း
def extract_audio(video_path, audio_path):
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path)
    return audio_path

# အဓိက UI
uploaded_file = st.file_uploader("Video ဖိုင် တင်လိုက်ပါ (English Recap)", type=["mp4", "mov"])

if uploaded_file is not None:
    # ယာယီသိမ်းမည့်နေရာ
    with open("temp_video.mp4", "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.video("temp_video.mp4")

    if st.button("Start Processing"):
        if not api_key:
            st.warning("OpenAI API Key ထည့်ပေးပါဦး Bro!")
        else:
            with st.spinner("အဆင့် (၁): အသံခွဲထုတ်နေသည်..."):
                extract_audio("temp_video.mp4", "temp_audio.mp3")
                st.success("Audio Extract လုပ်ပြီးပါပြီ။")
            
            with st.spinner("အဆင့် (၂): အင်္ဂလိပ်စကားပြောကို စာသားပြောင်းနေသည်..."):
                # Whisper AI ကိုသုံးပြီး Transcription လုပ်ခြင်း
                audio_file = open("temp_audio.mp3", "rb")
                transcript = openai.Audio.transcribe("whisper-1", audio_file)
                st.text_area("English Transcript", transcript['text'], height=150)
            
            with st.spinner("အဆင့် (၃): မြန်မာလို ဘာသာပြန်နေသည်..."):
                # GPT-4o သုံးပြီး မြန်မာ Recap ပုံစံ ဘာသာပြန်ခြင်း
                response = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a professional Burmese movie recap script writer."},
                        {"role": "user", "content": f"Translate this movie recap to engaging Burmese: {transcript['text']}"}
                    ]
                )
                burmese_script = response.choices[0].message.content
                st.text_area("Burmese Recap Script", burmese_script, height=200)
                st.success("ဘာသာပြန်ခြင်း ပြီးစီးပါပြီ။")
