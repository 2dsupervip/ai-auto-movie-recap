import streamlit as st
import os
import gc
import asyncio
import google.generativeai as genai
import edge_tts
import yt_dlp
from moviepy import VideoFileClip, AudioFileClip

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

# --- Initial Session States ---
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'draft_script' not in st.session_state:
    st.session_state.draft_script = ""
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'video_duration' not in st.session_state:
    st.session_state.video_duration = 0
if 'is_long_video' not in st.session_state:
    st.session_state.is_long_video = False

def next_step(): st.session_state.step += 1
def prev_step(): st.session_state.step -= 1

# --- Helper Functions ---
async def generate_voice(text, voice_name, output_filename):
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(output_filename)

def download_youtube_video(url, output_path="temp_video.mp4"):
    ydl_opts = {
        'format': 'best[height<=720]', 
        'outtmpl': output_path,
        'quiet': True,
        'nocheckcertificate': True,
        # 403 Error ရှောင်ရန် Android Client အဖြစ် ဟန်ဆောင်ခြင်း
        'extractor_args': {'youtube': {'player_client': ['android']}}
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return output_path

# --- UI Header ---
st.markdown('<div class="main-title">🗝️ Golden Key Recap Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Smart Video Processing Engine</div>', unsafe_allow_html=True)

# ==========================================
# WIZARD STEP 1: Setup & Media Input
# ==========================================
if st.session_state.step == 1:
    st.markdown('<div class="step-header">Step 1: Configuration & Input</div>', unsafe_allow_html=True)
    
    api_key_input = st.text_input("Google Gemini API Key", type="password", value=st.session_state.api_key)
    if api_key_input:
        st.session_state.api_key = api_key_input
        genai.configure(api_key=st.session_state.api_key)
    
    st.markdown("### 📥 Choose Media Source")
    input_method = st.radio("တင်မည့်ပုံစံ ရွေးချယ်ပါ", ["Upload Video (အကြံပြုသည်)", "YouTube Link (Error တက်နိုင်သည်)"], horizontal=True)
    
    video_ready = False
    
    if input_method == "Upload Video (အကြံပြုသည်)":
        uploaded_file = st.file_uploader("ဗီဒီယိုဖိုင် ရွေးပါ", type=["mp4", "mov"])
        if uploaded_file:
            with open("temp_video.mp4", "wb") as f:
                f.write(uploaded_file.getbuffer())
            video_ready = True
            st.success("ဗီဒီယို အောင်မြင်စွာ တင်ပြီးပါပြီ။")
            
    else:
        youtube_url = st.text_input("Paste YouTube Link Here")
        if st.button("⬇️ Download YouTube Video"):
            if youtube_url:
                with st.spinner("YouTube မှ ဆွဲယူနေပါသည်..."):
                    try:
                        if os.path.exists("temp_video.mp4"): os.remove("temp_video.mp4")
                        download_youtube_video(youtube_url)
                        video_ready = True
                        st.success("YouTube ဗီဒီယို ဆွဲယူခြင်း အောင်မြင်ပါသည်။")
                    except Exception as e:
                        st.error("YouTube မှ တိုက်ရိုက်ဆွဲယူခွင့် ပိတ်ထားပါသည်။ အထက်ပါ 'Upload Video' စနစ်ကို ပြောင်းလဲအသုံးပြုပါ။")

    st.markdown("### 🎛️ Voice Settings")
    voice_gender = st.selectbox("Premium Voice", ["Female (Nilar)", "Male (Thiha)"])
    target_duration = st.selectbox("အနှစ်ချုပ်ရမည့် အချိန် (ဗီဒီယိုအရှည်ကြီးများအတွက်သာ)", ["3 Minutes", "4 Minutes", "5 Minutes"])

    if st.button("🚀 Next: Analyze & Generate Script"):
        if not st.session_state.api_key:
            st.error("⚠️ API Key အရင်ထည့်ပါ။")
        elif not os.path.exists("temp_video.mp4"):
            st.error("⚠️ ဗီဒီယို အရင်တင်ရန် သို့မဟုတ် ဒေါင်းလုဒ်ဆွဲရန် လိုအပ်ပါသည်။")
        else:
            with st.spinner(">> ဗီဒီယိုကြာချိန်ကို စစ်ဆေးနေပါသည်..."):
                video_clip = VideoFileClip("temp_video.mp4")
                duration = video_clip.duration
                st.session_state.video_duration = duration
                
                # ၅ မိနစ် (စက္ကန့် ၃၀၀) ကျော်မကျော် စစ်ဆေးခြင်း
                if duration > 300:
                    st.session_state.is_long_video = True
                    st.warning("⚠️ ၅ မိနစ်ကျော်သော ဗီဒီယိုဖြစ်သဖြင့် Auto-Merge မလုပ်ဘဲ အနှစ်ချုပ် (Summarize) သာ ပြုလုပ်ပေးပါမည်။")
                else:
                    st.session_state.is_long_video = False
                    st.info("💡 ၅ မိနစ်အောက် ဗီဒီယိုဖြစ်သဖြင့် အသံနှင့် ရုပ်ကို အလိုအလျောက် ပေါင်းစပ်ပေးပါမည်။")
                
                video_clip.audio.write_audiofile("temp_audio.mp3", logger=None)
                video_clip.close()
                gc.collect()

            with st.spinner(">> AI မှ ဇာတ်ညွှန်း ရေးသားနေပါသည်..."):
                try:
                    audio_file = genai.upload_file(path="temp_audio.mp3")
                    model = genai.GenerativeModel("gemini-1.5-flash-latest")
                    
                    if st.session_state.is_long_video:
                        duration_mins = target_duration.split()[0]
                        prompt = f"Listen to this English movie recap audio. Summarize the entire plot into an engaging, fast-paced Burmese script designed for a TikTok video. CRITICAL: The script MUST take exactly {duration_mins} minutes to read out loud. Focus only on the main storyline. No markdown."
                    else:
                        prompt = "Listen to this English audio. Write a concise Burmese movie recap script. It MUST be exactly short enough to take the exact same amount of time to read as the original audio. No markdown."

                    response = model.generate_content([prompt, audio_file])
                    st.session_state.draft_script = response.text
                    st.session_state.voice_gender = voice_gender
                    
                    next_step()
                    st.rerun()
                except Exception as e:
                    st.error(f"AI Error: {e}")

# ==========================================
# WIZARD STEP 2: Script Editor
# ==========================================
elif st.session_state.step == 2:
    st.markdown('<div class="step-header">Step 2: Script Editor</div>', unsafe_allow_html=True)
    
    if st.session_state.is_long_video:
        st.info("📝 ဤသည်မှာ ၁၅ မိနစ်စာ ဗီဒီယိုမှ ၃-၅ မိနစ်စာ အနှစ်ချုပ်ထားသော ဇာတ်ညွှန်းဖြစ်သည်။")
    else:
        st.info("📝 ဤသည်မှာ မူရင်းဗီဒီယိုအရှည်အတိုင်း အချိန်ကိုက် ဘာသာပြန်ထားသော ဇာတ်ညွှန်းဖြစ်သည်။")

    edited_script = st.text_area("Edit Burmese Script:", value=st.session_state.draft_script, height=300)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Back"):
            prev_step()
            st.rerun()
    with col2:
        if st.button("🎙️ Next: Generate Final Output"):
            st.session_state.final_script = edited_script
            next_step()
            st.rerun()

# ==========================================
# WIZARD STEP 3: Final Processing & Export
# ==========================================
elif st.session_state.step == 3:
    st.markdown('<div class="step-header">Step 3: Final Output</div>', unsafe_allow_html=True)
    
    with st.spinner(">> Premium Voice-over ဖန်တီးနေပါသည်..."):
        try:
            clean_script = st.session_state.final_script.replace("*", "").replace("#", "")
            voice_id = "my-MM-NilarNeural" if "Nilar" in st.session_state.voice_gender else "my-MM-ThihaNeural"
            asyncio.run(generate_voice(clean_script, voice_id, "final_voice.mp3"))
            
            # -----------------------------------------------------
            # LOGIC 1: ဗီဒီယို ၅ မိနစ်ကျော်လျှင် (Audio/Video သီးသန့်ပြမည်)
            # -----------------------------------------------------
            if st.session_state.is_long_video:
                st.success("🎉 အနှစ်ချုပ် အသံဖိုင် ဖန်တီးပြီးပါပြီ! (VN/CapCut တွင် သွားရောက် ဖြတ်ဆက်ပါ)")
                st.audio("final_voice.mp3")
                
                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    with open("temp_video.mp4", "rb") as file:
                        st.download_button("🎥 Download Raw Video", data=file, file_name="Raw_Video.mp4", mime="video/mp4")
                with col_dl2:
                    with open("final_voice.mp3", "rb") as file:
                        st.download_button("🎙️ Download Audio Only", data=file, file_name="Recap_Audio.mp3", mime="audio/mp3")

            # -----------------------------------------------------
            # LOGIC 2: ဗီဒီယို ၅ မိနစ်အောက်လျှင် (Auto-Merge လုပ်ပေးမည်)
            # -----------------------------------------------------
            else:
                with st.spinner(">> ဗီဒီယိုနှင့် အသံကို အလိုအလျောက် ပေါင်းစပ်နေပါသည် (Auto-Merge)..."):
                    video_clip = VideoFileClip("temp_video.mp4")
                    new_audio = AudioFileClip("final_voice.mp3")
                    
                    speed_factor = video_clip.duration / new_audio.duration
                    
                    if hasattr(video_clip, 'with_effects'):
                        import moviepy.video.fx as vfx
                        synced_video = video_clip.with_effects([vfx.MultiplySpeed(speed_factor)])
                        final_video = synced_video.with_duration(new_audio.duration).with_audio(new_audio)
                    else:
                        synced_video = video_clip.speedx(factor=speed_factor)
                        final_video = synced_video.set_duration(new_audio.duration).set_audio(new_audio)
                    
                    if final_video.h > 720:
                        if hasattr(final_video, 'resized'): final_video = final_video.resized(height=720)
                        else: final_video = final_video.resize(height=720)
                    
                    final_video.write_videofile("final_merged.mp4", codec="libx264", audio_codec="aac", preset="ultrafast", threads=2, logger=None)
                    
                    video_clip.close()
                    new_audio.close()
                    final_video.close()
                    gc.collect()
                    
                    st.success("🎉 အောင်မြင်စွာ ပေါင်းစပ်ပြီးပါပြီ!")
                    st.video("final_merged.mp4")
                    
                    with open("final_merged.mp4", "rb") as file:
                        st.download_button("📥 Download Final Video", data=file, file_name="GoldenKey_Merged.mp4", mime="video/mp4")
            
            st.markdown("---")
            if st.button("🔄 Start New Project"):
                st.session_state.step = 1
                st.rerun()

        except Exception as e:
            st.error(f"Processing Error: {e}")
