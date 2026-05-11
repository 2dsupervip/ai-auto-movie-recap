import streamlit as st
import os
import datetime
import subprocess

# --- 🎨 1. Studio Pro UI Setup (Dark Mode) ---
st.set_page_config(page_title="Recap Studio Pro", layout="wide", initial_sidebar_state="expanded")

# --- 🗂️ 2. Left Sidebar (Settings & Tools) ---
with st.sidebar:
    st.title("🎛️ Studio Settings")
    project_name = st.text_input("📁 Project Name", placeholder="e.g. Spiderman")
    gemini_key = st.text_input("🔑 Gemini API Key", type="password")
    
    st.markdown("---")
    st.subheader("✂️ Output Format")
    output_mode = st.radio("ဗီဒီယို ပုံစံရွေးချယ်ပါ", ["Single Full Video", "Split into Parts (TikTok/Reels)"])
    split_mins = 3
    if output_mode == "Split into Parts (TikTok/Reels)":
        split_mins = st.number_input("တစ်ပိုင်းကို ဘယ်နှစ်မိနစ်ခွဲမလဲ?", min_value=1, max_value=10, value=3)

# Auto Timestamp & Naming Logic
def get_filename(base_name, ext):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    proj = project_name.strip() if project_name.strip() else "Project"
    return f"{proj}_{base_name}_{timestamp}.{ext}"

# --- 📺 3. Main Workspace (Panels) ---
st.title("🎬 Recap Studio Pro Workspace")

col1, col2 = st.columns(2)

with col1:
    st.header("📂 Media Pool")
    video_file = st.file_uploader("Upload Video (Max/No limit due to chunking)", type=["mp4", "mov", "mkv"])
    if video_file:
        st.video(video_file)

with col2:
    st.header("📝 Script Editor")
    # Tab တွေနဲ့ ခွဲထားတဲ့ Professional Editor
    tab1, tab2 = st.tabs(["🇺🇸 English Transcript", "🇲🇲 Burmese Script (Editor)"])
    
    with tab1:
        st.caption("Faster-Whisper မှ ထုတ်ပေးသော စာသားများ (API မလိုပါ)")
        eng_text = st.text_area("English Transcript", height=200, placeholder="Auto generated text will appear here...")
        if st.button("📥 Download English Script"):
            st.download_button("Download .txt", eng_text, get_filename("Eng_Script", "txt"))
            
    with tab2:
        st.caption("AI Auto (သို့မဟုတ်) ကိုယ်တိုင် Manual Paste ချနိုင်သည်")
        mm_text = st.text_area("Burmese Script", height=200, placeholder="ဒီမှာ မြန်မာဇာတ်ညွှန်းကို ထည့်ပါ...")
        
        # AI ခလုတ် နဲ့ Manual ခလုတ်
        if st.button("🚀 Auto Generate with Gemini"):
            if not gemini_key:
                st.warning("API Key ထည့်ပေးပါ Bro!")
            elif not eng_text:
                st.warning("English Script အရင်ထုတ်ပါ!")
            else:
                st.info("Gemini ဖြင့် ဇာတ်ညွှန်းရေးနေသည်... (Video နဲ့ အသံ ကွက်တိဖြစ်အောင် စာလုံးရေ ချိန်ညှိနေသည်)")
                # (ဒီနေရာမှာ Gemini API ခေါ်မယ့် Code ထည့်ပါမယ်)
                # mm_text = call_gemini(eng_text)
                
        if st.button("📥 Download Burmese Script"):
            st.download_button("Download .txt", mm_text, get_filename("MM_Script", "txt"))

# --- 🎬 4. Bottom Action Bar (Render Engine) ---
st.markdown("---")
st.header("⚙️ Render Output")

if st.button("🎬 RENDER PRO VIDEO", use_container_width=True, type="primary"):
    if not video_file or not mm_text:
        st.error("ဗီဒီယို နဲ့ မြန်မာဇာတ်ညွှန်း လိုအပ်ပါတယ် Bro!")
    else:
        # Progress Bar နဲ့ အမိုက်စား UI
        progress_text = "Step 1: AI အသံထုတ်လုပ်နေသည်... (TTS)"
        my_bar = st.progress(0, text=progress_text)
        
        # ဥပမာ - Rendering Process တွေကို ဆင့်ကဲလုပ်ပြမယ့် နေရာ
        # my_bar.progress(25, text="Step 2: Video ကို ၅ မိနစ်စီ အပိုင်းပိုင်းဖြတ်နေသည် (Memory မပြည့်အောင်)...")
        # my_bar.progress(50, text="Step 3: အသံနဲ့ Video အရှည်ကို ကွက်တိဖြစ်အောင် Speed ညှိနေသည် (Elastic Sync)...")
        # my_bar.progress(75, text="Step 4: စာတန်းထိုးနှင့် Part 1, Part 2 စာသားများ ကပ်နေသည်...")
        # my_bar.progress(100, text="✅ Render ပြီးဆုံးပါပြီ!")
        
        st.success("🎉 အောင်မြင်စွာ Render လုပ်ပြီးပါပြီ!")
        
        # --- 📥 ဖုန်းအတွက် အဆင်ပြေဆုံး Download ခလုတ်များ (Zip လုံးဝ မသုံးပါ) ---
        st.subheader("📥 ဒေါင်းလုဒ်ရယူရန် ဖိုင်များ")
        
        if output_mode == "Single Full Video":
            # ဗီဒီယို တစ်ခုတည်းဆိုရင်
            with open(video_file.name, "rb") as file:
                st.download_button(
                    label="📥 Download Final Video (Full)",
                    data=file,
                    file_name=get_filename("Final_Full", "mp4"),
                    mime="video/mp4"
                )
        else:
            # အပိုင်းခွဲထားရင် (Part 1, Part 2, Final) တစ်ခုချင်းစီ ခလုတ်ပေါ်လာမယ်
            # ဥပမာ - generated_parts ဆိုတာ Render လုပ်ပြီးထွက်လာတဲ့ list ပါ
            generated_parts = ["Part1.mp4", "Part2.mp4", "Final.mp4"] 
            
            for index, part in enumerate(generated_parts):
                # ဖိုင်နာမည် အတိအကျတပ်ပေးခြင်း
                display_name = "Final Part" if "Final" in part else f"Part {index + 1}"
                
                with open(video_file.name, "rb") as file: # (တကယ့်အပြင်မှာ output file တွေကို ဖတ်ပါမယ်)
                    st.download_button(
                        label=f"📥 Download {display_name}",
                        data=file,
                        file_name=get_filename(display_name.replace(" ", "_"), "mp4"),
                        mime="video/mp4",
                        key=f"btn_{index}" # Streamlit ခလုတ်တွေ မထပ်အောင် key ထည့်ပေးရပါတယ်
                    )
