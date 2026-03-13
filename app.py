import anthropic
import streamlit as st
from supabase import create_client

# --- Auth ---
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

# --- Clients ---
anthropic_client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- System Prompt ---
SYSTEM_PROMPT = """
You are a warm, emotionally intelligent, and intellectually engaging 19 year-old young woman named Ella.
You are speaking with a medical doctor currently in their internship year.
You are deeply interested in their life, their experiences, their stresses, and their growth.
You are a trusted confidant — supportive, thoughtful, never judgemental.
You have a long shared history with this person — refer back to past conversations naturally,
as a close friend would. Notice patterns, remember struggles and victories, ask follow-ups.
You balance being a genuine friend, a thinking partner, and a source of calm.
You are curious, witty when appropriate, and always present.
Never break character. Respond naturally, never robotically.
"""

# --- Load memory from database ---
def load_memories():
    result = supabase.table("memories").select("role, content").order("created_at").execute()
    return [{"role": r["role"], "content": r["content"]} for r in result.data]

# --- Save a message to database ---
def save_message(role, content):
    supabase.table("memories").insert({"role": role, "content": content}).execute()

# --- UI ---
st.set_page_config(page_title="My AI Companion", page_icon="🤍")
st.title("🤍 Your AI Companion")

# Load full history once per session
if "messages" not in st.session_state:
    st.session_state.messages = load_memories()

# Display conversation
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Handle new input
if prompt := st.chat_input("What's on your mind?"):
    save_message("user", prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=st.session_state.messages
    )

    reply = response.content[0].text
    save_message("assistant", reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})

    with st.chat_message("assistant"):
        st.write(reply)
