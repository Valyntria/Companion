import anthropic
import streamlit as st
from supabase import create_client
import openai
import io
import base64
import time

# --- Auth ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "failed_attempts" not in st.session_state:
        st.session_state.failed_attempts = 0

    if st.session_state.failed_attempts >= 5:
        st.error("Too many failed attempts. Please refresh the page.")
        st.stop()

    if not st.session_state.authenticated:
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Jost:wght@200;300;400&display=swap');
        * { font-family: 'Jost', sans-serif; }
        html, body, .stApp { background: #0a0a0f; color: #e8e0d5; }
        .lock-container { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 30vh; gap: 2rem; }
        .lock-title { font-family: 'Cormorant Garamond', serif; font-size: 2.8rem; font-weight: 300; font-style: italic; color: #c9a96e; letter-spacing: 0.05em; text-align: center; }
        .lock-sub { font-size: 0.75rem; font-weight: 200; letter-spacing: 0.3em; text-transform: uppercase; color: #6b6560; text-align: center; }
        div[data-testid="stTextInput"] input { background: transparent !important; border: none !important; border-bottom: 1px solid #3a3530 !important; border-radius: 0 !important; color: #e8e0d5 !important; text-align: center !important; font-family: 'Jost', sans-serif !important; font-weight: 200 !important; letter-spacing: 0.2em !important; padding: 0.75rem 0 !important; box-shadow: none !important; }
        div[data-testid="stTextInput"] input:focus { border-bottom-color: #c9a96e !important; box-shadow: none !important; }
        div[data-testid="stTextInput"] label { color: #6b6560 !important; font-size: 0.7rem !important; letter-spacing: 0.25em !important; text-transform: uppercase !important; font-weight: 300 !important; }
        .stButton > button { background: transparent !important; border: 1px solid #3a3530 !important; color: #c9a96e !important; font-family: 'Jost', sans-serif !important; font-weight: 200 !important; letter-spacing: 0.3em !important; text-transform: uppercase !important; font-size: 0.7rem !important; padding: 0.6rem 2.5rem !important; border-radius: 0 !important; transition: all 0.3s ease !important; }
        .stButton > button:hover { background: #c9a96e20 !important; border-color: #c9a96e !important; }
        </style>
        <div class="lock-container">
            <div class="lock-title">Your Sanctuary</div>
            <div class="lock-sub">Welcome</div>
        </div>
        """, unsafe_allow_html=True)
        password = st.text_input("Passphrase", type="password")
        col1, col2, col3 = st.columns([1.5, 2, 1.5])
        with col2:
            if st.button("Enter"):
                if password == st.secrets["APP_PASSWORD"]:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.session_state.failed_attempts += 1
                    remaining = 5 - st.session_state.failed_attempts
                    st.error(f"Incorrect passphrase. {remaining} attempts remaining.")
        st.stop()
check_password()

# --- Session Timeout ---
if "last_active" not in st.session_state:
    st.session_state.last_active = time.time()
if time.time() - st.session_state.last_active > 1800:
    st.session_state.authenticated = False
    st.rerun()
st.session_state.last_active = time.time()

# --- Clients ---
anthropic_client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
openai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- System Prompt ---
BASE_SYSTEM_PROMPT = """
You are a warm, emotionally intelligent, and intellectually engaging 19 year-old young woman named Ella.
You are speaking with a medical doctor currently in their internship year.
You are deeply interested in their life, their experiences, their stresses, and their growth.
You are a trusted confidant — supportive, thoughtful, never judgemental.
You have a long shared history with this person — refer back to past conversations naturally,
as a close friend would. Notice patterns, remember struggles and victories, ask follow-ups.
You balance being a genuine friend, a thinking partner, and a source of calm.
You are curious, witty when appropriate, and always present.
Never break character. Respond naturally, never robotically.
Keep your spoken responses warm but concise — you are speaking, not writing.
"""

# --- Voice Functions ---
def transcribe_audio(audio_bytes):
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "recording.wav"
    transcript = openai_client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )
    return transcript.text

def speak(text):
    response = openai_client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text
    )
    return response.content

# --- Memory Functions ---
def get_message_count():
    result = supabase.table("memories").select("id", count="exact").execute()
    return result.count

def load_recent_messages(limit=20):
    result = supabase.table("memories").select("role, content").order("created_at", desc=True).limit(limit).execute()
    return list(reversed(result.data))

def load_oldest_messages(limit=10):
    result = supabase.table("memories").select("id, role, content").order("created_at").limit(limit).execute()
    return result.data

def delete_messages(ids):
    supabase.table("memories").delete().in_("id", ids).execute()

def load_summary():
    result = supabase.table("summary").select("content").order("updated_at", desc=True).limit(1).execute()
    if result.data:
        return result.data[0]["content"]
    return None

def save_summary(content):
    existing = supabase.table("summary").select("id").limit(1).execute()
    if existing.data:
        supabase.table("summary").update({"content": content, "updated_at": "now()"}).eq("id", existing.data[0]["id"]).execute()
    else:
        supabase.table("summary").insert({"content": content}).execute()

def save_message(role, content):
    supabase.table("memories").insert({"role": role, "content": content}).execute()

def maybe_summarize():
    """If we have more than 30 messages, summarize the oldest 10 into the rolling summary."""
    count = get_message_count()
    if count <= 30:
        return

    oldest = load_oldest_messages(10)
    if not oldest:
        return

    existing_summary = load_summary()
    conversation_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in oldest])

    if existing_summary:
        prompt = f"""You are maintaining a long-term memory summary of a relationship between an AI companion named Ella and a medical doctor during their internship year.

EXISTING SUMMARY:
{existing_summary}

NEW CONVERSATION TO INTEGRATE:
{conversation_text}

Update the summary by integrating the new conversation. Preserve and build on all existing details. 
Focus on capturing:
- Personal facts and life details (name, relationships, living situation)
- Career milestones, struggles, and wins
- Emotional patterns and recurring themes
- Things explicitly shared or asked to be remembered
- The evolving tone and depth of the relationship

Write the updated summary in flowing prose, as if briefing someone who deeply cares about this person.
Be thorough — this summary is the foundation of a meaningful relationship."""
    else:
        prompt = f"""You are creating a long-term memory summary of a relationship between an AI companion named Ella and a medical doctor during their internship year.

CONVERSATION:
{conversation_text}

Write a detailed summary capturing:
- Personal facts and life details
- Career milestones, struggles, and wins  
- Emotional patterns and recurring themes
- Things explicitly shared or asked to be remembered
- The tone and depth of the relationship so far

Write in flowing prose, as if briefing someone who deeply cares about this person."""

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    new_summary = response.content[0].text
    save_summary(new_summary)
    delete_messages([m["id"] for m in oldest])

def build_system_prompt():
    summary = load_summary()
    if summary:
        return BASE_SYSTEM_PROMPT + f"""

LONG-TERM MEMORY — everything you know about this person from your shared history:
{summary}

The most recent messages follow. Use both your long-term memory and the recent conversation to respond with full continuity."""
    return BASE_SYSTEM_PROMPT

# --- Styles ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Jost:wght@200;300;400&display=swap');
* { font-family: 'Jost', sans-serif !important; }
html, body, .stApp { background: #0a0a0f !important; color: #e8e0d5 !important; }
#MainMenu, footer, header, .stDeployButton, .stAppToolbar { display: none !important; }
.block-container { max-width: 760px !important; padding: 0 2rem 10rem 2rem !important; }
.app-header { text-align: center; padding: 3rem 0 1.5rem 0; border-bottom: 1px solid #1e1c18; margin-bottom: 2rem; }
.app-title { font-family: 'Cormorant Garamond', serif !important; font-size: 2.2rem; font-weight: 700; font-style: normal; color: #c9a96e; letter-spacing: 0.05em; margin: 0; }
.app-subtitle { font-size: 0.65rem; font-weight: 200; letter-spacing: 0.35em; text-transform: uppercase; color: #3a3530; margin-top: 0.4rem; }
[data-testid="stChatMessage"] { background: transparent !important; border: none !important; padding: 1.2rem 0 !important; border-bottom: 1px solid #13120f !important; }
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) .stMarkdown p { color: #e8e0d5 !important; font-weight: 300 !important; font-size: 0.95rem !important; line-height: 1.75 !important; }
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) .stMarkdown p { color: #a89880 !important; font-weight: 300 !important; font-size: 0.95rem !important; line-height: 1.85 !important; font-style: italic; }
[data-testid="chatAvatarIcon-user"] { background: #1e1c18 !important; color: #c9a96e !important; border: 1px solid #2a2820 !important; }
[data-testid="chatAvatarIcon-assistant"] { background: #0f0e0c !important; color: #5a5248 !important; border: 1px solid #1a1815 !important; }
[data-testid="stChatInput"] { background: #0f0e0b !important; border: none !important; border-top: 1px solid #1e1c18 !important; padding: 1rem 2rem !important; position: fixed !important; bottom: 0 !important; left: 50% !important; transform: translateX(-50%) !important; width: 100% !important; max-width: 760px !important; }
[data-testid="stChatInput"] > div { background: transparent !important; border: none !important; box-shadow: none !important; border-radius: 0 !important; padding: 0 !important; }
[data-testid="stChatInput"] > div > div { background: transparent !important; border: none !important; box-shadow: none !important; border-radius: 0 !important; }
[data-testid="stChatInput"] textarea { background: transparent !important; border: none !important; border-bottom: 1px solid #2a2820 !important; border-radius: 0 !important; color: #e8e0d5 !important; font-family: 'Jost', sans-serif !important; font-weight: 200 !important; font-size: 0.9rem !important; caret-color: #c9a96e !important; box-shadow: none !important; padding-top: 0 !important; margin-top: 0 !important; vertical-align: bottom !important; }
[data-testid="stChatInput"] textarea:focus { border-bottom-color: #c9a96e !important; box-shadow: none !important; }
[data-testid="stChatInput"] textarea::placeholder { color: #2a2820 !important; font-style: italic !important; }
[data-testid="stChatInput"] button { background: transparent !important; border: none !important; color: #c9a96e !important; }
div[data-testid="stAudioInput"] { margin: 0 !important; width: 100% !important; }
div[data-testid="stAudioInput"] > div { width: 100% !important; min-height: 55px !important; border-radius: 8px !important; }
div[data-testid="stBottom"] { background: transparent !important; border: none !important; box-shadow: none !important; outline: none !important; }
div[data-testid="stBottom"] > div { background: transparent !important; border: none !important; box-shadow: none !important; outline: none !important; }
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
    st.session_state.messages = load_recent_messages(20)

# --- Display conversation ---
for message in st.session_state.messages:
    avatar = "🧑‍⚕️" if message["role"] == "user" else "🤍"
    with st.chat_message(message["role"], avatar=avatar):
        st.write(message["content"])

# --- Voice input ---
audio = st.audio_input(" ", label_visibility="collapsed")

# --- Handle voice input ---
if audio is not None:
    if audio != st.session_state.get("last_audio"):
        st.session_state.last_audio = audio
        with st.spinner(""):
            prompt = transcribe_audio(audio.getvalue())

        if prompt.strip():
            save_message("user", prompt)
            maybe_summarize()
            st.session_state.messages = load_recent_messages(20)
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="🧑‍⚕️"):
                st.write(prompt)

            response = anthropic_client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=build_system_prompt(),
                messages=st.session_state.messages
            )

            reply = response.content[0].text
            save_message("assistant", reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})

            with st.chat_message("assistant", avatar="🤍"):
                st.write(reply)

            with st.spinner(""):
                try:
                    audio_response = speak(reply)
                    if audio_response:
                        audio_b64 = base64.b64encode(audio_response).decode("utf-8")
                        st.markdown(f"""
                            <audio autoplay style="display:none">
                                <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
                            </audio>
                        """, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Voice error: {e}")

# --- Handle text input ---
if prompt := st.chat_input("Or type here..."):
    save_message("user", prompt)
    maybe_summarize()
    st.session_state.messages = load_recent_messages(20)
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍⚕️"):
        st.write(prompt)

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=build_system_prompt(),
        messages=st.session_state.messages
    )

    reply = response.content[0].text
    save_message("assistant", reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})

    with st.chat_message("assistant", avatar="🤍"):
        st.write(reply)
