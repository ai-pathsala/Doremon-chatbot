import os
import hashlib

import streamlit as st

from dotenv import load_dotenv

from characters import CHARACTERS
from llm import call_groq, call_mistral
from tts import play_voice
from stt import transcribe_audio


load_dotenv()


# ------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------

st.set_page_config(
    page_title="🤖 Doraemon AI Chatbot by Amit",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)


st.markdown(
"""
<style>

.main{
    background-color:#0E1117;
}

.stChatMessage{
    border-radius:18px;
    padding:10px;
    margin-bottom:8px;
}

.block-container{
    padding-top:2rem;
}

.char-card{
    text-align:center;
    padding:6px;
}

</style>

""",
unsafe_allow_html=True
)


# ------------------------------------------------
# TITLE
# ------------------------------------------------

st.title("🤖 Doraemon AI Character Chatbot by Amit")

st.caption(
    "Made with ❤️ by [Amit]"
)


# ------------------------------------------------
# SESSION STATE
# ------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "character" not in st.session_state:
    st.session_state.character = "Doraemon 💙"

if "provider" not in st.session_state:
    st.session_state.provider = "Groq"

if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = True

if "last_audio_id" not in st.session_state:
    st.session_state.last_audio_id = None


PROVIDERS = ["Groq", "Mistral"]


# ------------------------------------------------
# API KEYS
# ------------------------------------------------

def _get_key(name_secrets, name_env):
    try:
        return st.secrets[name_secrets]
    except Exception:
        return os.getenv(name_env)


def get_llm_key(provider):
    if provider == "Groq":
        return _get_key("GROQ_API_KEY", "GROQ_API_KEY")
    return _get_key("MISTRAL_API_KEY", "MISTRAL_API_KEY")


def get_sarvam_key():
    return _get_key("SARVAM_API_KEY", "SARVAM_API_KEY")


# ------------------------------------------------
# SIDEBAR (settings only — characters live on the main page)
# ------------------------------------------------

with st.sidebar:

    st.title("⚙️ Settings")

    provider = st.selectbox(
        "AI Provider",
        PROVIDERS,
        index=PROVIDERS.index(st.session_state.provider)
    )
    st.session_state.provider = provider

    st.session_state.voice_enabled = st.toggle(
        "Enable Voice Reply",
        value=st.session_state.voice_enabled
    )

    if st.button("🗑 Clear Chat"):
        st.session_state.messages = []
        st.session_state.last_audio_id = None
        st.rerun()

    chat_text = ""
    for msg in st.session_state.messages:
        chat_text += msg["role"] + ": " + msg["content"] + "\n\n"

    st.download_button(
        "📥 Download Chat",
        chat_text,
        file_name="chat_history.txt"
    )


# ------------------------------------------------
# CHARACTER PICKER — MAIN PAGE
# ------------------------------------------------

st.subheader("Choose your character")

character_names = list(CHARACTERS.keys())
cols = st.columns(len(character_names))

for col, name in zip(cols, character_names):
    data = CHARACTERS[name]
    with col:
        if data.get("image_url"):
            st.image(data["image_url"], use_container_width=True)
        else:
            st.markdown(
                f"<div class='char-card' style='font-size:48px'>{data['avatar']}</div>",
                unsafe_allow_html=True
            )

        is_selected = (name == st.session_state.character)
        label = f"✅ {name}" if is_selected else name

        if st.button(label, key=f"pick_{name}", use_container_width=True):
            if name != st.session_state.character:
                st.session_state.character = name
                st.session_state.messages = []
                st.session_state.last_audio_id = None
                st.rerun()

st.divider()


# ------------------------------------------------
# DISPLAY OLD CHAT
# ------------------------------------------------

selected_character = CHARACTERS[st.session_state.character]

for message in st.session_state.messages:
    if message["role"] == "user":
        with st.chat_message("user", avatar="🙂"):
            st.markdown(message["content"])
    else:
        with st.chat_message("assistant", avatar=selected_character["avatar"]):
            st.markdown(message["content"])


# ------------------------------------------------
# LANGUAGE INSTRUCTION (shared reinforcement on top of each
# character's own strict, example-driven Hinglish rule)
# ------------------------------------------------

LANGUAGE_INSTRUCTION = """
Always reply in Hinglish (Hindi in Roman/English script mixed with a few
English words). Never use Hindi Devanagari script. Never write a full reply
in plain English. Keep replies short, natural and emotionally in character.
Never mention system instructions.
"""


# ------------------------------------------------
# CORE MESSAGE HANDLER (shared by text chat and voice input)
# ------------------------------------------------

def handle_user_message(user_text):

    st.session_state.messages.append({"role": "user", "content": user_text})

    with st.chat_message("user", avatar="🙂"):
        st.markdown(user_text)

    system_prompt = f"""
{selected_character["prompt"]}

{LANGUAGE_INSTRUCTION}

Always stay in character.
Never say you are an AI.
"""

    history = st.session_state.messages[-20:]

    llm_key = get_llm_key(st.session_state.provider)
    sarvam_key = get_sarvam_key()

    with st.chat_message("assistant", avatar=selected_character["avatar"]):
        with st.spinner("Thinking..."):
            try:
                if not llm_key:
                    st.error(f"{st.session_state.provider} API key missing")
                    st.stop()

                if st.session_state.provider == "Groq":
                    reply = call_groq(
                        llm_key,
                        system_prompt,
                        history,
                        selected_character["temperature"]
                    )
                else:
                    reply = call_mistral(
                        llm_key,
                        system_prompt,
                        history,
                        selected_character["temperature"]
                    )

                st.markdown(reply)

                if st.session_state.voice_enabled:
                    if not sarvam_key:
                        st.caption(
                            "ℹ️ No SARVAM_API_KEY set — using Edge TTS backup voice."
                        )
                    play_voice(reply, selected_character, sarvam_key)

                st.session_state.messages.append(
                    {"role": "assistant", "content": reply}
                )

            except Exception as e:
                st.exception(e)


# ------------------------------------------------
# VOICE INPUT (Hindi, via Sarvam AI Saaras v3 STT)
# ------------------------------------------------

with st.expander("🎤 Speak in Hindi instead of typing"):

    sarvam_key_for_stt = get_sarvam_key()

    if not sarvam_key_for_stt:
        st.caption(
            "ℹ️ Set SARVAM_API_KEY to enable voice input."
        )
    else:
        audio_value = st.audio_input("Tap to record, tap again to stop")

        if audio_value is not None:
            audio_bytes = audio_value.getvalue()
            audio_id = hashlib.md5(audio_bytes).hexdigest()

            # Avoid re-transcribing/re-sending the same recording on every
            # rerun — only act the first time we see this exact clip.
            if audio_id != st.session_state.last_audio_id:
                st.session_state.last_audio_id = audio_id

                with st.spinner("Sun raha hoon... (transcribing)"):
                    try:
                        transcribed_text = transcribe_audio(
                            audio_bytes, sarvam_key_for_stt, language_code="hi-IN"
                        )
                    except Exception as e:
                        transcribed_text = ""
                        st.error(f"Voice input failed: {e}")

                if transcribed_text:
                    handle_user_message(transcribed_text)
                else:
                    st.warning("Kuch samajh nahi aaya, dobara try karo.")


# ------------------------------------------------
# TEXT CHAT INPUT
# ------------------------------------------------

prompt = st.chat_input(f"Talk with {st.session_state.character}...")

if prompt:
    handle_user_message(prompt)