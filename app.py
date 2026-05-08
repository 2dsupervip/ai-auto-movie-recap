import streamlit as st
import os
from moviepy import VideoFileClip, AudioFileClip
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

# --- Session State ---
if 'credits' not in st.session_state:
    st.session_state.credits = 231 

# --- UI Header ---
st.markdown('<div class="main-title">🗝️ Golden Key Recap Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Final Level: Auto-Sync Video & Audio Integration</div>', unsafe_allow_html=True)

col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
with col_c2:
    st.markdown(f'<div class="credit-box">💳 Available Credits: {st.session_state.credits}</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

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
    except: pass

    # --- Media Upload ---
    st.markdown("### 🎬 Media Upload")
    uploaded_file = st.file_uploader("Upload Video", type=["mp4", "mov"], label_visibility="collapsed")

    if uploaded_file:
        with open("temp_video.mp4", "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.video("temp_video.mp4")

        # --- Studio Settings ---
        st.markdown("### 🎛️ Studio Settings")
        col1, col2 = st.columns(2)
        with col1:
            project_name = st.text_input("Project Name", value="Recap_Project")
            voice_gender = st.selectbox("Voice Identity", ["Female (Nilar)", "Male (Thiha)"])
        with col2:
            model_choice = st.selectbox("AI Model", available_models if available_models else ["gemini-1.5-flash-latest"])

        if st.button("🚀 Process & Merge Video"):
            if st.session_state.credits > 0:
                # 1. Extract Audio
                with st.spinner(">> အဆင့် (၁): အသံခွဲထုတ်နေသည်..."):
                    video_clip = VideoFileClip("temp_video.mp4")
                    video_clip.audio.write_audiofile("temp_audio.mp3", logger=None)
                
                # 2. AI Script
                with st.spinner(">> အဆင့် (၂): AI Script ရေးသားနေသည်..."):
                    audio_file = genai.upload_file(path="temp_audio.mp3")
                    model = genai.GenerativeModel(model_choice)
                    prompt = "Write a very concise Burmese movie recap script for this audio. It must be exactly short enough to fit the video length."
                    response = model.generate_content([prompt, audio_file])
                    burmese_script = response.text
                
                # 3. Generate Burmese Voice
                with st.spinner(">> အဆင့် (၃): Premium Voice-over ဖန်တီးနေသည်..."):
                    clean_script = burmese_script.replace("*", "").replace("#", "").replace("_", "")
                    clean_script = clean_script.replace("အသံ:", "").replace("Voiceover:", "").replace("Narrator:", "")
                    voice_id = "my-MM-NilarNeural" if voice_gender == "Female (Nilar)" else "my-MM-ThihaNeural"
                    asyncio.run(generate_voice(clean_script, voice_id, "recap_audio.mp3"))
                
                # 4. Merge Video and Audio (Auto-Sync Video Speed)
                with st.spinner(">> အဆင့် (၄): ဗီဒီယိုနှင့် မြန်မာအသံကို အလိုအလျောက် အချိန်ညှိနေသည်... (ခဏစောင့်ပါ)"):
                    try:
                        new_audio = AudioFileClip("recap_audio.mp3")
                        audio_duration = new_audio.duration
                        video_duration = video_clip.duration
                        
                        # (၁) Speed Factor တွက်ချက်ခြင်း
                        speed_factor = video_duration / audio_duration
                        
                        # (၂) MoviePy Version အလိုက် အနှေး/အမြန် ညှိခြင်း (fl_time Error ကို အပြီးတိုင် ဖြေရှင်းထားသည်)
                        if hasattr(video_clip, 'with_effects'):
                            # MoviePy Version 2.0+ (Version အသစ်များအတွက်)
                            import moviepy.video.fx as vfx
                            synced_video = video_clip.with_effects([vfx.MultiplySpeed(speed_factor)])
                            final_video = synced_video.with_duration(audio_duration).with_audio(new_audio)
                        else:
                            # MoviePy Version 1.x (Version အဟောင်းများအတွက်)
                            synced_video = video_clip.speedx(factor=speed_factor)
                            final_video = synced_video.set_duration(audio_duration).set_audio(new_audio)
                        
                        final_video.write_videofile("final_recap_video.mp4", codec="libx264", audio_codec="aac", logger=None)
                        
                        st.session_state.credits -= 1
                        st.success("🎉 အောင်မြင်စွာ အချိန်ကိုက် ပေါင်းစပ်ပြီးပါပြီ! (Auto-Synced)")
                        
                        # ရလဒ်ပြသခြင်း
                        st.video("final_recap_video.mp4")
                        
                        # ဒေါင်းလုဒ်ခလုတ်
                        with open("final_recap_video.mp4", "rb") as file:
                            st.download_button(
                                label="📥 Download Auto-Synced Recap Video",
                                data=file,
                                file_name=f"GoldenKey_{project_name}_Synced.mp4",
                                mime="video/mp4"
                            )
                    except Exception as e:
                        st.error(f"ပေါင်းစပ်ရာတွင် အမှားအယွင်းရှိပါသည်: {e}")

                        # ရလဒ်ပြသခြင်း
                        st.video("final_recap_video.mp4")
                        
                        # ဒေါင်းလုဒ်ခလုတ်
                        with open("final_recap_video.mp4", "rb") as file:
                            st.download_button(
                                label="📥 Download Auto-Synced Recap Video",
                                data=file,
                                file_name=f"GoldenKey_{project_name}_Synced.mp4",
                                mime="video/mp4"
                            )
                    except Exception as e:
                        st.error(f"ပေါင်းစပ်ရာတွင် အမှားအယွင်းရှိပါသည်: {e}")
                        
                        # ရလဒ်ပြသခြင်း
                        st.video("final_recap_video.mp4")
                        
                        # ဒေါင်းလုဒ်ခလုတ်
                        with open("final_recap_video.mp4", "rb") as file:
                            st.download_button(
                                label="📥 Download Final Recap Video",
                                data=file,
                                file_name=f"GoldenKey_{project_name}.mp4",
                                mime="video/mp4"
                            )
                    except Exception as e:
                        st.error(f"ပေါင်းစပ်ရာတွင် အမှားအယွင်းရှိပါသည်: {e}")
            else:
                st.error("Credits မလုံလောက်ပါ။")
else:
    st.info("👈 Please enter API Key in Configuration.")
