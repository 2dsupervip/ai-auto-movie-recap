import streamlit as st
import os
import datetime
import subprocess
import urllib.request
from google import genai
from faster_whisper import WhisperModel

# --- 🎨 1. Studio Pro UI Setup ---
st.set_page_config(page_title="Recap Studio Pro", layout="wide", initial_sidebar_state="expanded")

# --- 🗂️ Variables & Session State ---
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

# --- Helper Functions ---
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

def ensure_myanmar_font():
    font_path = "Padauk.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/padauk/Padauk-Regular.ttf"
        urllib.request.urlretrieve(url, font_path)
    return font_path

# --- 📺 Main Workspace ---
st.title("🎬 Recap Studio Pro Workspace")

col1, col2 = st.columns(2)

with col1:
    st.header("📂 Media Pool")
    video_file = st.file_uploader("Upload Video", type=["mp4", "mov", "mkv"])
    if video_file:
        st.video(video_file)
        with open("input_video.mp4", "wb") as f:
            f.write(video_file.getbuffer())

with col2:
    st.header("📝 Script Editor")
    tab1, tab2 = st.tabs(["🇺🇸 English Transcript", "🇲🇲 Burmese Script"])
    
    with tab1:
        if st.button("🎙️ Extract Audio to Text"):
            if not video_file: st.error("ဗီဒီယို အရင်တင်ပေးပါ!")
            else:
                with st.spinner("အသံဖတ်နေသည်..."):
                    subprocess.run('ffmpeg -y -i input_video.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 temp_audio.wav', shell=True)
                    model = WhisperModel("small", compute_type="int8") 
                    segments, _ = model.transcribe("temp_audio.wav")
                    st.session_state.eng_text = " ".join([s.text for s in segments])
                    st.success("စာသားထုတ်ယူပြီးပါပြီ!")
        st.text_area("English Transcript", value=st.session_state.eng_text, height=200, key="eng_ta")
            
    with tab2:
        if st.button("🚀 Auto Generate with Gemini"):
            if not gemini_key or not st.session_state.eng_text: st.warning("လိုအပ်ချက်များ မပြည့်စုံပါ!")
            else:
                with st.spinner("Gemini မှ ဇာတ်ညွှန်းရေးဆွဲနေသည်..."):
                    try:
                        vid_duration = get_video_duration("input_video.mp4")
                        estimated_words = int((vid_duration / 60) * 130)
                        client = genai.Client(api_key=gemini_key)
                        # 🌟 Bro အကြံပြုထားသော မြန်မာ Prompt အား အသုံးပြုခြင်း
                        prompt = f"""အောက်ပါ အင်္ဂလိပ်စာသားကို ဆွဲဆောင်မှုရှိတဲ့ 'မြန်မာ Recap ဇာတ်ညွှန်း' အဖြစ် ဘာသာပြန်ပေးပါ။
                        စတိုင် (Style): {script_style} ဖြင့် ဇာတ်လမ်းပြန်ပြောပြတဲ့ဟန် (Storytelling style) ကို သုံးပါ။
                        အရေးကြီးသော သတ်မှတ်ချက်များ (IMPORTANT CONSTRAINTS):
                        ၁။ အသံထွက်ဖတ်ရာတွင် သဘာဝကျပြီး မြန်မာစကားပြောဟန် (Conversational tone) ဖြစ်ရမည်။
                        ၂။ ဗီဒီယိုအရှည်မှာ {vid_duration:.1f} စက္ကန့် ဖြစ်သည်။
                        ၃။ အသံနှင့် ဗီဒီယို အရှည် ကွက်တိဖြစ်စေရန် မြန်မာစာလုံးရေကို အတိအကျ {estimated_words} လုံး ဝန်းကျင်သာ အသုံးပြုပြီး အနှစ်ချုပ် (Recap) ရေးပေးပါ။
                        Transcript: {st.session_state.eng_text}"""
                        
                        response = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
                        st.session_state.mm_text = response.text
                        st.success("ဇာတ်ညွှန်း ထုတ်လုပ်ပြီးပါပြီ!")
                    except Exception as e: st.error(f"Error: {e}")

        st.text_area("Burmese Script", value=st.session_state.mm_text, height=200, key="mm_ta")

# --- 🎬 4. Backend Render Engine ---
st.markdown("---")
st.header("⚙️ Render Output")

if st.button("🎬 RENDER PRO VIDEO", use_container_width=True, type="primary"):
    if not os.path.exists("input_video.mp4") or not st.session_state.mm_text:
        st.error("ဗီဒီယို နှင့် မြန်မာဇာတ်ညွှန်း လိုအပ်ပါသည်!")
    else:
        progress_bar = st.progress(0, text="Starting Render Engine...")
        
        # --- Step 1: TTS & SRT ---
        progress_bar.progress(20, text="Step 1: AI အသံနှင့် စာတန်းထိုး (SRT) ထုတ်လုပ်နေသည်...")
        voice_id = "my-MM-ThihaNeural" if "Male" in voice_choice else "my-MM-NilarNeural"
        with open("script.txt", "w", encoding="utf-8") as f: f.write(st.session_state.mm_text)
        subprocess.run(f'edge-tts --file script.txt --voice {voice_id} --write-media audio.mp3 --write-subtitles subtitles.srt', shell=True)
        
        # --- Step 2: Elastic Sync ---
        progress_bar.progress(40, text="Step 2: Video နှင့် Audio အရှည် ကွက်တိဖြစ်အောင် ညှိနေသည်...")
        vid_dur = get_video_duration("input_video.mp4")
        aud_dur = get_video_duration("audio.mp3")
        speed_ratio = vid_dur / aud_dur if aud_dur > 0 else 1.0
        subprocess.run(f'ffmpeg -y -i input_video.mp4 -filter:v "setpts={speed_ratio}*PTS" -an synced_video.mp4', shell=True)

        # --- Step 3: Subtitles & Local Blur (Bottom 25%) ---
        progress_bar.progress(70, text="Step 3: အောက်ခြေကို ဝါး (Blur) ၍ မြန်မာဖောင့်ဖြင့် စာတန်းထိုးနေသည်...")
        font_file = ensure_myanmar_font()
        
        # 🌟 Blur Filter + Subtitle Filter (Tofu Fix)
        # အောက်ခြေ ၂၅% ကို ဝါးပြီး စာတန်းထိုးမည့် Master Filter
        video_filters = (
            f"split[v1][v2];"
            f"[v1]crop=iw:ih*0.25:0:ih*0.75,boxblur=20:5[blurred];"
            f"[v2][blurred]overlay=0:main_h-overlay_h[finalv];"
            f"[finalv]subtitles=subtitles.srt:fontsdir=.:force_style='Fontname=Padauk,Fontsize=22,PrimaryColour=&H00FFFF,Outline=1,BorderStyle=1'"
        )
        
        generated_files = []
        if output_mode == "Single Full Video":
            subprocess.run(f'ffmpeg -y -i synced_video.mp4 -i audio.mp3 -vf "{video_filters}" -c:v libx264 -preset fast -c:a aac -shortest final_output.mp4', shell=True)
            generated_files.append("final_output.mp4")
        else:
            subprocess.run(f'ffmpeg -y -i synced_video.mp4 -i audio.mp3 -vf "{video_filters}" -c:v libx264 -preset fast -c:a aac -shortest master_temp.mp4', shell=True)
            total_parts = int((aud_dur / 60) // split_mins) + 1
            for i in range(total_parts):
                start = i * split_mins * 60
                out = f"part_{i+1}.mp4"
                label = f"Part {i+1}" if i < total_parts - 1 else "Final Part"
                subprocess.run(f'ffmpeg -y -ss {start} -t {split_mins*60} -i master_temp.mp4 -vf "drawtext=text=\'{label}\':fontcolor=yellow:fontsize=40:x=(w-text_w)/2:y=50:box=1:boxcolor=black@0.5" -c:v libx264 -preset fast -c:a copy {out}', shell=True)
                if os.path.exists(out): generated_files.append(out)

        progress_bar.progress(100, text="✅ Render ပြီးဆုံးပါပြီ!")
        for file in generated_files:
            with open(file, "rb") as f:
                st.download_button(label=f"📥 Download {file}", data=f, file_name=get_filename(file, "mp4"), mime="video/mp4", key=f"btn_{file}")
