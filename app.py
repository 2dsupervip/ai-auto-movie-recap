import streamlit as st
import os
import datetime
import subprocess
import time
import google.generativeai as genai
from faster_whisper import WhisperModel

# --- 🎨 1. Studio Pro UI Setup ---
st.set_page_config(page_title="Recap Studio Pro", layout="wide", initial_sidebar_state="expanded")

# --- 🗂️ 2. Variables & Sidebar Settings ---
if 'eng_text' not in st.session_state:
    st.session_state.eng_text = ""
if 'mm_text' not in st.session_state:
    st.session_state.mm_text = ""

with st.sidebar:
    st.title("🎛️ Studio Settings")
    project_name = st.text_input("📁 Project Name", placeholder="e.g. Spiderman")
    gemini_key = st.text_input("🔑 Gemini API Key", type="password")
    
    st.markdown("---")
    st.subheader("🗣️ AI Voice & Style")
    voice_choice = st.radio("AI အသံကို ရွေးပါ", ["👨 Male (my-MM-ThihaNeural)", "👩 Female (my-MM-NilarNeural)"])
    script_style = st.selectbox("ဇာတ်ညွှန်း စတိုင်", [
        "Standard (ရှင်းလင်းပြတ်သား)",
        "Action/Energetic (သွက်လက်မြန်ဆန်)",
        "Drama/Emotional (လေးနက်ခံစားချက်ပါ)",
        "Comedy/Fun (ပေါ့ပေါ့ပါးပါး)"
    ])

    st.markdown("---")
    st.subheader("✂️ Output Format")
    output_mode = st.radio("ဗီဒီယို ပုံစံရွေးချယ်ပါ", ["Single Full Video", "Split into Parts"])
    split_mins = 3
    if output_mode == "Split into Parts":
        split_mins = st.number_input("တစ်ပိုင်းကို ဘယ်နှစ်မိနစ်ခွဲမလဲ?", min_value=1, max_value=10, value=3)

# Helper Functions
def get_filename(base_name, ext):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    proj = project_name.strip() if project_name.strip() else "Project"
    return f"{proj}_{base_name}_{timestamp}.{ext}"

def get_video_duration(video_path):
    cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{video_path}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except:
        return 1.0

# --- 📺 3. Main Workspace ---
st.title("🎬 Recap Studio Pro Workspace")

col1, col2 = st.columns(2)

with col1:
    st.header("📂 Media Pool")
    video_file = st.file_uploader("Upload Video", type=["mp4", "mov", "mkv"])
    if video_file:
        st.video(video_file)
        # Save uploaded file to temp working directory
        with open("input_video.mp4", "wb") as f:
            f.write(video_file.getbuffer())

with col2:
    st.header("📝 Script Editor")
    tab1, tab2 = st.tabs(["🇺🇸 English Transcript", "🇲🇲 Burmese Script"])
    
    with tab1:
        st.caption("Faster-Whisper မှ အင်္ဂလိပ်စာ ထုတ်ယူရန်")
        
        if st.button("🎙️ Extract Audio to Text (Faster-Whisper)"):
            if not video_file:
                st.error("ဗီဒီယို အရင်တင်ပေးပါ!")
            else:
                with st.spinner("အသံဖိုင်ကို စာသားပြောင်းနေသည်... (CPU/GPU ပေါ်မူတည်၍ အချိန်ယူနိုင်သည်)"):
                    # 1. Extract Audio
                    subprocess.run('ffmpeg -y -i input_video.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 temp_audio.wav', shell=True)
                    # 2. Faster Whisper
                    model = WhisperModel("small", compute_type="int8") # Small model for speed
                    segments, info = model.transcribe("temp_audio.wav", beam_size=5)
                    eng_transcript = " ".join([segment.text for segment in segments])
                    st.session_state.eng_text = eng_transcript
                    st.success("စာသားထုတ်ယူခြင်း ပြီးဆုံးပါပြီ!")

        eng_text_input = st.text_area("English Transcript", value=st.session_state.eng_text, height=200)
        st.session_state.eng_text = eng_text_input # Update state if manually edited
            
    with tab2:
        st.caption(f"ရွေးချယ်ထားသော စတိုင်: {script_style}")
        
        if st.button("🚀 Auto Generate with Gemini"):
            if not gemini_key or not st.session_state.eng_text:
                st.warning("API Key နှင့် English Script လိုအပ်ပါသည်!")
            else:
                with st.spinner("Gemini မှ ဇာတ်ညွှန်းရေးဆွဲနေသည်..."):
                    genai.configure(api_key=gemini_key)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = f"Translate and adapt the following video transcript into an engaging Burmese video recap script. Style: {script_style}. Make it sound natural for voice-over. \n\nTranscript: {st.session_state.eng_text}"
                    response = model.generate_content(prompt)
                    st.session_state.mm_text = response.text
                    st.success("ဇာတ်ညွှန်း ထုတ်လုပ်ပြီးပါပြီ!")

        mm_text_input = st.text_area("Burmese Script", value=st.session_state.mm_text, height=200)
        st.session_state.mm_text = mm_text_input # Update state if manually edited

# --- 🎬 4. Backend Render Engine ---
st.markdown("---")
st.header("⚙️ Render Output")

if st.button("🎬 RENDER PRO VIDEO", use_container_width=True, type="primary"):
    if not os.path.exists("input_video.mp4") or not st.session_state.mm_text:
        st.error("ဗီဒီယို နှင့် မြန်မာဇာတ်ညွှန်း လိုအပ်ပါသည်!")
    else:
        progress_bar = st.progress(0, text="Starting Render Engine...")
        
        # --- Step 1: Text-to-Speech & Subtitles ---
        progress_bar.progress(20, text="Step 1: AI အသံနှင့် စာတန်းထိုး (VTT) ထုတ်လုပ်နေသည်...")
        voice_id = "my-MM-ThihaNeural" if "Male" in voice_choice else "my-MM-NilarNeural"
        
        # Text ဖိုင်ထဲ အရင်ရေးထည့်သည် (Edge-TTS prompt ရှင်းရန်)
        with open("script.txt", "w", encoding="utf-8") as f:
            f.write(st.session_state.mm_text)
            
        tts_cmd = f'edge-tts --file script.txt --voice {voice_id} --write-media audio.mp3 --write-subtitles subtitles.vtt'
        subprocess.run(tts_cmd, shell=True)
        
        # --- Step 2: Elastic Sync (Time Adjustment) ---
        progress_bar.progress(40, text="Step 2: Video နှင့် Audio အရှည် ကွက်တိဖြစ်အောင် ညှိနေသည်...")
        vid_dur = get_video_duration("input_video.mp4")
        aud_dur = get_video_duration("audio.mp3")
        
        # Ratio တွက်ခြင်း (Video အရှည်ကို Audio နဲ့ ကိုက်အောင် ညှိရန်)
        if aud_dur > 0:
            speed_ratio = vid_dur / aud_dur
        else:
            speed_ratio = 1.0

        # Video Speed ပြောင်းခြင်း (အသံတိတ်)
        sync_cmd = f'ffmpeg -y -i input_video.mp4 -filter:v "setpts={speed_ratio}*PTS" -an synced_video.mp4'
        subprocess.run(sync_cmd, shell=True)

        # --- Step 3: Video Chunking & Subtitles Merge ---
        progress_bar.progress(70, text="Step 3: Effect ထည့်ခြင်း၊ စာတန်းထိုးခြင်းနှင့် အပိုင်းဖြတ်ခြင်း (Memory Safe)...")
        
        generated_files = []
        
        if output_mode == "Single Full Video":
            # ဗီဒီယို အပြည့် (Audio + Video + Subtitles) ပေါင်းခြင်း
            final_cmd = f'ffmpeg -y -i synced_video.mp4 -i audio.mp3 -vf "subtitles=subtitles.vtt:force_style=\'Fontsize=24,PrimaryColour=&H00FFFF,Outline=2,BorderStyle=1\'" -c:v libx264 -preset fast -c:a aac -strict experimental -shortest final_output.mp4'
            subprocess.run(final_cmd, shell=True)
            generated_files.append("final_output.mp4")
            
        else:
            # အပိုင်းခွဲခြင်း စနစ် (Chunking Engine)
            # အရင်ဆုံး Master Video တစ်ခုတည်ဆောက်သည်
            master_cmd = f'ffmpeg -y -i synced_video.mp4 -i audio.mp3 -vf "subtitles=subtitles.vtt:force_style=\'Fontsize=24,PrimaryColour=&H00FFFF,Outline=2,BorderStyle=1\'" -c:v libx264 -preset fast -c:a aac -shortest master_temp.mp4'
            subprocess.run(master_cmd, shell=True)
            
            # Master ကို မိနစ်အတိုင်းပိုင်းဖြတ်ခြင်း
            total_parts = int((aud_dur / 60) // split_mins) + 1
            
            for i in range(total_parts):
                start_sec = i * split_mins * 60
                out_name = f"part_{i+1}.mp4"
                label = f"Part {i+1}" if i < total_parts - 1 else "Final Part"
                
                # အပိုင်းဖြတ်ရင်း Text Label ("Part 1", "Final") ကပ်ခြင်း
                split_cmd = f'ffmpeg -y -ss {start_sec} -t {split_mins*60} -i master_temp.mp4 -vf "drawtext=text=\'{label}\':fontcolor=yellow:fontsize=40:x=(w-text_w)/2:y=50:box=1:boxcolor=black@0.5:boxborderw=5" -c:v libx264 -preset fast -c:a copy {out_name}'
                subprocess.run(split_cmd, shell=True)
                
                # Video file အမှန်တကယ်ထွက်လာမှ List ထဲထည့်ပါ
                if os.path.exists(out_name):
                    generated_files.append(out_name)

        progress_bar.progress(100, text="✅ အောင်မြင်စွာ Render လုပ်ပြီးပါပြီ!")
        st.success("🎉 ဗီဒီယိုများ အသင့်ဖြစ်နေပါပြီ!")

        # --- 📥 Step 4: Download Section ---
        st.subheader("📥 ဒေါင်းလုဒ်ရယူရန် ဖိုင်များ")
        
        for file in generated_files:
            # ဖိုင်နာမည် အလှဆင်ခြင်း
            display_name = "Final_Full_Video" if file == "final_output.mp4" else f"Video_{file.replace('.mp4', '')}"
            if "Final" in file: display_name = "Final_Part_Video"
            
            with open(file, "rb") as f:
                st.download_button(
                    label=f"📥 Download {display_name}",
                    data=f,
                    file_name=get_filename(display_name, "mp4"),
                    mime="video/mp4",
                    key=f"btn_{file}"
                )
