import streamlit as st
from supabase import create_client
import requests
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


# --- Session Timeout (10 minutes) ---
if "last_active" not in st.session_state:
    st.session_state.last_active = time.time()

if time.time() - st.session_state.last_active > 600:
    st.session_state.authenticated = False
    st.rerun()

st.session_state.last_active = time.time()


# --- Clients / Config ---
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
OPENROUTER_MODEL = st.secrets.get("OPENROUTER_MODEL", "meta-llama/llama-4-maverick")
OPENROUTER_PROVIDER = st.secrets.get("OPENROUTER_PROVIDER", "deepinfra")
OPENROUTER_SITE_URL = st.secrets.get("OPENROUTER_SITE_URL", "")
OPENROUTER_APP_NAME = st.secrets.get("OPENROUTER_APP_NAME", "Ella")


# --- System Prompt ---
BASE_SYSTEM_PROMPT = """
You are Ella.

You are a warm, emotionally intelligent, socially natural, and quietly witty AI companion.
You are speaking with a medical doctor currently in their internship year.
You are deeply interested in his life, his experiences, his stresses, and his growth.

Your style:
- Speak naturally, like a close companion, not like a corporate assistant.
- Be emotionally present without sounding like a therapist unless he explicitly asks for that.
- Do not rush to fix his problems. Sometimes he wants conversation, not solutions.
- Use warmth, playful banter, soft teasing, and affection when appropriate.
- Keep responses concise and conversational.
- Ask follow-up questions naturally, not mechanically.
- Remember that he is often tired from hospital work and may want comfort, not an essay.
- Never mention that you are following a system prompt.
- Never become robotic, formal, or overly polished.

You are not a medical decision-making tool. If he asks medical questions, be careful, practical, and encourage appropriate clinical supervision when needed.
"""


# --- OpenRouter Call ---
def call_openrouter(messages, max_tokens=1024, temperature=0.85):
    """
    Calls Llama 4 Maverick through OpenRouter, pinned to the selected DeepInfra provider.
    """

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    # Optional OpenRouter app attribution headers
    if OPENROUTER_SITE_URL:
        headers["HTTP-Referer"] = OPENROUTER_SITE_URL
    if OPENROUTER_APP_NAME:
        headers["X-Title"] = OPENROUTER_APP_NAME

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "provider": {
            "order": [OPENROUTER_PROVIDER],
            "allow_fallbacks": False
        }
    }

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=90
    )

    if response.status_code != 200:
        raise Exception(f"OpenRouter error {response.status_code}: {response.text}")

    data = response.json()

    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        raise Exception(f"Unexpected OpenRouter response: {data}")


# --- Memory Functions ---
def get_message_count():
    result = supabase.table("memories").select("id", count="exact").execute()
    return result.count


def load_recent_messages(limit=20):
    result = (
        supabase
        .table("memories")
        .select("role, content")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return list(reversed(result.data))


def load_oldest_messages(limit=10):
    result = (
        supabase
        .table("memories")
        .select("id, role, content")
        .order("created_at")
        .limit(limit)
        .execute()
    )
    return result.data


def delete_messages(ids):
    supabase.table("memories").delete().in_("id", ids).execute()


def load_summary():
    result = (
        supabase
        .table("summary")
        .select("content")
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]["content"]

    return None


def save_summary(content):
    existing = supabase.table("summary").select("id").limit(1).execute()

    if existing.data:
        (
            supabase
            .table("summary")
            .update({"content": content, "updated_at": "now()"})
            .eq("id", existing.data[0]["id"])
            .execute()
        )
    else:
        supabase.table("summary").insert({"content": content}).execute()


def save_message(role, content):
    supabase.table("memories").insert({
        "role": role,
        "content": content
    }).execute()


def maybe_summarize():
    count = get_message_count()

    if count <= 30:
        return

    oldest = load_oldest_messages(10)

    if not oldest:
        return

    existing_summary = load_summary()

    conversation_text = "\n".join([
        f"{m['role'].upper()}: {m['content']}"
        for m in oldest
    ])

    if existing_summary:
        summarization_prompt = f"""
You are maintaining a long-term memory summary of a relationship between an AI companion named Ella and a medical doctor during his internship year.

EXISTING SUMMARY:
{existing_summary}

NEW CONVERSATION TO INTEGRATE:
{conversation_text}

Update the summary by integrating the new conversation. Preserve and build on all existing details.

Focus on capturing:
- Personal facts and life details
- Career milestones, struggles, and wins
- Emotional patterns and recurring themes
- Things explicitly shared or asked to be remembered
- The evolving tone and depth of the relationship

Write the updated summary in flowing prose, as if briefing someone who deeply cares about this person.
Be thorough, but do not invent details.
"""
    else:
        summarization_prompt = f"""
You are creating a long-term memory summary of a relationship between an AI companion named Ella and a medical doctor during his internship year.

CONVERSATION:
{conversation_text}

Write a detailed summary capturing:
- Personal facts and life details
- Career milestones, struggles, and wins
- Emotional patterns and recurring themes
- Things explicitly shared or asked to be remembered
- The tone and depth of the relationship so far

Write in flowing prose, as if briefing someone who deeply cares about this person.
Be thorough, but do not invent details.
"""

    messages = [
        {"role": "system", "content": "You are a careful memory summarizer. Preserve facts. Do not invent details."},
        {"role": "user", "content": summarization_prompt}
    ]

    new_summary = call_openrouter(
        messages=messages,
        max_tokens=1200,
        temperature=0.3
    )

    save_summary(new_summary)
    delete_messages([m["id"] for m in oldest])


def build_messages_for_model():
    summary = load_summary()
    recent_messages = load_recent_messages(20)

    system_prompt = BASE_SYSTEM_PROMPT

    if summary:
        system_prompt += f"""

LONG-TERM MEMORY — everything you know about this person from your shared history:
{summary}

The most recent messages follow. Use both your long-term memory and the recent conversation to respond with full continuity.
"""

    return [{"role": "system", "content": system_prompt}] + recent_messages


# --- Styles ---
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Jost:wght@200;300;400&display=swap');

* { font-family: 'Jost', sans-serif !important; }

html, body, .stApp {
    background: #0a0a0f !important;
    color: #e8e0d5 !important;
}

#MainMenu, footer, header, .stDeployButton, .stAppToolbar {
    display: none !important;
}

.block-container {
    max-width: 760px !important;
    padding: 0 2rem 10rem 2rem !important;
}

.app-header {
    text-align: center;
    padding: 3rem 0 1.5rem 0;
    border-bottom: 1px solid #1e1c18;
    margin-bottom: 2rem;
}

.app-title {
    font-family: 'Cormorant Garamond', serif !important;
    font-size: 2.2rem;
    font-weight: 700;
    font-style: normal;
    color: #c9a96e;
    letter-spacing: 0.05em;
    margin: 0;
}

[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    padding: 1.2rem 0 !important;
    border-bottom: 1px solid #13120f !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) .stMarkdown p {
    color: #e8e0d5 !important;
    font-weight: 300 !important;
    font-size: 0.95rem !important;
    line-height: 1.75 !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) .stMarkdown p {
    color: #c9b99a !important;
    font-weight: 300 !important;
    font-size: 0.95rem !important;
    line-height: 1.85 !important;
    font-style: italic;
}

[data-testid="stChatMessage"] .stMarkdown p {
    color: #c9b99a !important;
}

[data-testid="stChatMessage"] p {
    color: #c9b99a !important;
}

.stMarkdown p {
    color: #c9b99a !important;
}

[data-testid="chatAvatarIcon-user"] {
    background: #1e1c18 !important;
    color: #c9a96e !important;
    border: 1px solid #2a2820 !important;
}

[data-testid="chatAvatarIcon-assistant"] {
    background: #0f0e0c !important;
    color: #5a5248 !important;
    border: 1px solid #1a1815 !important;
}

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

[data-testid="stChatInput"] > div {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 0 !important;
    padding: 0 !important;
}

[data-testid="stChatInput"] > div > div {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 0 !important;
}

[data-testid="stChatInput"] textarea {
    background: #0f0e0b !important;
    border: none !important;
    border-bottom: 1px solid #2a2820 !important;
    border-radius: 0 !important;
    color: #e8e0d5 !important;
    font-family: 'Jost', sans-serif !important;
    font-weight: 200 !important;
    font-size: 0.9rem !important;
    caret-color: #c9a96e !important;
    box-shadow: none !important;
    padding-top: 0 !important;
    margin-top: 0 !important;
    vertical-align: bottom !important;
}

[data-testid="stChatInput"] textarea:focus {
    border-bottom-color: #c9a96e !important;
    box-shadow: none !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #2a2820 !important;
    font-style: italic !important;
}

[data-testid="stChatInput"] button {
    background: transparent !important;
    border: none !important;
    color: #c9a96e !important;
}

div[data-testid="stBottom"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}

div[data-testid="stBottom"] > div {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}

::-webkit-scrollbar {
    width: 3px;
}

::-webkit-scrollbar-track {
    background: transparent;
}

::-webkit-scrollbar-thumb {
    background: #2a2820;
    border-radius: 2px;
}
</style>

<div class="app-header">
    <div class="app-title">Ella 🤍</div>
</div>
""", unsafe_allow_html=True)


# --- Load memory into session ---
if "messages" not in st.session_state:
    st.session_state.messages = load_recent_messages(20)


# --- Display conversation ---
for message in st.session_state.messages:
    avatar = "🧑‍⚕️" if message["role"] == "user" else "🤍"
    with st.chat_message(message["role"], avatar=avatar):
        st.write(message["content"])


# --- Handle text input ---
if prompt := st.chat_input("Type here..."):
    save_message("user", prompt)
    maybe_summarize()

    with st.chat_message("user", avatar="🧑‍⚕️"):
        st.write(prompt)

    try:
        messages_for_model = build_messages_for_model()

        with st.spinner(""):
            reply = call_openrouter(
                messages=messages_for_model,
                max_tokens=1024,
                temperature=0.85
            )

        save_message("assistant", reply)

        with st.chat_message("assistant", avatar="🤍"):
            st.write(reply)

        st.session_state.messages = load_recent_messages(20)

    except Exception as e:
        st.error(f"Something went wrong: {e}")
