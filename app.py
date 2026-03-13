import anthropic
import streamlit as st
from supabase import create_client

# --- Auth ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Jost:wght@200;300;400&display=swap');
        * { font-family: 'Jost', sans-serif; }
        html, body, .stApp {
            background: #0a0a0f;
            color: #e8e0d5;
        }
        .lock-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 80vh;
            gap: 2rem;
        }
        .lock-title {
            font-family: 'Cormorant Garamond', serif;
            font-size: 2.8rem;
            font-weight: 300;
            font-style: normal;
            color: #c9a96e;
            letter-spacing: 0.05em;
            text-align: center;
        }
        .lock-sub {
            font-size: 0.75rem;
            font-weight: 200;
            letter-spacing: 0.3em;
            text-transform: uppercase;
            color: #6b6560;
            text-align: center;
        }
        div[data-testid="stTextInput"] input {
            background: transparent !important;
            border: none !important;
            border-bottom: 1px solid #3a3530 !important;
            border-radius: 0 !important;
            color: #e8e0d5 !important;
            text-align: center !important;
            font-family: 'Jost', sans-serif !important;
            font-weight: 200 !important;
            letter-spacing: 0.2em !important;
            padding: 0.75rem 0 !important;
            box-shadow: none !important;
        }
        div[data-testid="stTextInput"] input:focus {
            border-bottom-color: #c9a96e !important;
            box-shadow: none !important;
        }
        div[data-testid="stTextInput"] label {
            color: #6b6560 !important;
            font-size: 0.7rem !important;
            letter-spacing: 0.25em !important;
            text-transform: uppercase !important;
            font-weight: 300 !important;
        }
        .stButton > button {
            background: transparent !important;
            border: 1px solid #3a3530 !important;
            color: #c9a96e !important;
            font-family: 'Jost', sans-serif !important;
            font-weight: 200 !important;
            letter-spacing: 0.3em !important;
            text-transform: uppercase !important;
            font-size: 0.7rem !important;
            padding: 0.6rem 2.5rem !important;
            border-radius: 0 !important;
            transition: all 0.3s ease !important;
        }
        .stButton > button:hover {
            background: #c9a96e20 !important;
            border-color: #c9a96e !important;
        }
        </style>
        <div class="lock-container">
            <div class="lock-title">Your Sanctuary</div>
            <div class="lock-sub">Private & Encrypted</div>
        </div>
        """, unsafe_allow_html=True)
        password = st.text_input("Passphrase", type="password", label_visibility="visible")
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("Enter"):
                if password == st.secrets["APP_PASSWORD"]:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Incorrect passphrase.")
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

# --- Memory ---
def load_memories():
    result = supabase.table("memories").select("role, content").order("created_at").execute()
    return [{"role": r["role"], "content": r["content"]} for r in result.data]

def save_message(role, content):
    supabase.table("memories").insert({"role": role, "content": content}).execute()

# --- Global Styles ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Jost:wght@200;300;400&display=swap');

* { font-family: 'Jost', sans-serif !important; }

html, body, .stApp {
    background: #0a0a0f !important;
    color: #e8e0d5 !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header, .stDeployButton { display: none !important; }
.stAppToolbar { display: none !important; }
.block-container {
    max-width: 760px !important;
    padding: 0 2rem 6rem 2rem !important;
}

/* Header */
.app-header {
    text-align: center;
    padding: 3rem 0 1.5rem 0;
    border-bottom: 1px solid #1e1c18;
    margin-bottom: 2rem;
}
.app-title {
    font-family: 'Cormorant Garamond', serif !important;
    font-size: 2.2rem;
    font-weight: 300;
    font-style: normal;
    color: #c9a96e;
    letter-spacing: 0.05em;
    margin: 0;
}
.app-subtitle {
    font-size: 0.65rem;
    font-weight: 200;
    letter-spacing: 0.35em;
    text-transform: uppercase;
    color: #3a3530;
    margin-top: 0.4rem;
}

/* Chat messages */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    padding: 1.2rem 0 !important;
    border-bottom: 1px solid #13120f !important;
}

/* User messages */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) .stMarkdown p {
    color: #e8e0d5 !important;
    font-weight: 300 !important;
    font-size: 0.95rem !important;
    line-height: 1.75 !important;
}

/* Assistant messages */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) .stMarkdown p {
    color: #a89880 !important;
    font-weight: 300 !important;
    font-size: 0.95rem !important;
    line-height: 1.85 !important;
    font-style: normal;
}

/* Avatar icons */
[data-testid="chatAvatarIcon-user"] {
    background: #1e1c18 !important;
    color: #c9a96e !important;
    border: 1px solid #2a2820 !important;
    font-size: 0.7rem !important;
}
[data-testid="chatAvatarIcon-assistant"] {
    background: #0f0e0c !important;
    color: #5a5248 !important;
    border: 1px solid #1a1815 !important;
    font-size: 0.7rem !important;
}

/* Chat input */
[data-testid="stChatInput"] {
    background: #0f0e0b !important;
    border: none !important;
    border-top: 1px solid #1e1c18 !important;
    padding: 1rem 2rem !important;
    position: fixed !important;
    bottom: 0 !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    width: 100% !important;
    max-width: 760px !important;
}

[data-testid="stChatInput"] textarea {
    background: transparent !important;
    border: none !important;
    border-bottom: 1px solid #2a2820 !important;
    border-radius: 0 !important;
    color: #e8e0d5 !important;
    font-family: 'Jost', sans-serif !important;
    font-weight: 200 !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.03em !important;
    caret-color: #c9a96e !important;
    box-shadow: none !important;
    resize: none !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-bottom-color: #c9a96e !important;
    box-shadow: none !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: #2a2820 !important;
    font-style: normal !important;
}

/* Send button */
[data-testid="stChatInput"] button {
    background: transparent !important;
    border: none !important;
    color: #c9a96e !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #2a2820; border-radius: 2px; }
</style>

<div class="app-header">
    <div class="app-title">Ella 🤍</div>
</div>
""", unsafe_allow_html=True)

# --- Load memory ---
if "messages" not in st.session_state:
    st.session_state.messages = load_memories()

# --- Display conversation ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# --- Handle new input ---
if prompt := st.chat_input("What's on your mind today..."):
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
