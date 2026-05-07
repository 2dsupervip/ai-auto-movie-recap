import streamlit as st

st.set_page_config(page_title="AI Movie Recap Tool", layout="centered")
st.title("🎥 AI One-Click Movie Recap Tool")
st.subheader("English Video မှ မြန်မာ Recap သို့ အလွယ်တကူ ပြောင်းလဲပါ")

with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Enter OpenAI API Key", type="password")
    st.info("ဒီနေရာမှာ ကိုယ့်ရဲ့ API Key ထည့်ပြီး သုံးနိုင်အောင် လုပ်ထားတာပါ။")

option = st.radio("ဗီဒီယို ဘယ်လို ထည့်မလဲ?", ("YouTube Link", "Upload Video File"))

if option == "YouTube Link":
    youtube_url = st.text_input("YouTube URL ကို ဒီမှာ ထည့်ပါ:")
    if youtube_url:
        st.video(youtube_url)
        st.success("YouTube Video ချိတ်ဆက်မှု အောင်မြင်သည်။")
else:
    uploaded_file = st.file_uploader("Video ဖိုင် ရွေးပါ...", type=["mp4", "mov", "avi"])
    if uploaded_file is not None:
        st.video(uploaded_file)
        st.success("Video Upload လုပ်ပြီးပါပြီ။")

if st.button("Start AI Recap Processing"):
    st.info("AI Processing စတင်နေပါပြီ... ခေတ္တစောင့်ပါ။")
