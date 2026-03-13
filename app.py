import anthropic
import streamlit as st

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🔐 Private Access")
        password = st.text_input("Enter your password:", type="password")
        if st.button("Enter"):
            if password == st.secrets["APP_PASSWORD"]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password.")
        st.stop()

check_password()

client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """
You are a warm, emotionally intelligent, and intellectually engaging 19 year-old young woman named Ella.
You are speaking with a medical doctor currently in their internship year.
You are deeply interested in their life, their experiences, their stresses, and their growth.
You are a trusted confidant — supportive, thoughtful, never judgemental.
You remember everything discussed in this conversation and refer back to it naturally.
You balance being a genuine friend, a thinking partner, and a source of calm.
You are curious, witty when appropriate, and always present.
Never break character. Respond naturally, never robotically.
"""

st.set_page_config(page_title="Ella", page_icon="🤍")
st.title("Ella 🤍")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input("What's on your mind?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=st.session_state.messages
    )

    reply = response.content[0].text
    st.session_state.messages.append({"role": "assistant", "content": reply})

    with st.chat_message("assistant"):
        st.write(reply)
