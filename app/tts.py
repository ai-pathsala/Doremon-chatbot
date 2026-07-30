import asyncio
import base64
import tempfile

import requests
import edge_tts
import streamlit as st


SARVAM_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_MODEL = "bulbul:v3"
SARVAM_MAX_CHARS = 2400  # API hard limit is 2500; leave a safety margin


# ------------------------------------------------
# TEXT CHUNKING (Sarvam caps ~2500 chars/request)
# ------------------------------------------------

def _chunk_text(text, limit=SARVAM_MAX_CHARS):
    if len(text) <= limit:
        return [text]

    chunks = []
    current = ""

    for sentence in text.replace("\n", " ").split(". "):
        piece = sentence if sentence.endswith(".") else sentence + "."
        if len(current) + len(piece) > limit:
            if current:
                chunks.append(current.strip())
            current = piece
        else:
            current += " " + piece

    if current.strip():
        chunks.append(current.strip())

    return chunks


# ------------------------------------------------
# SARVAM AI (Bulbul v3)
# ------------------------------------------------

def generate_voice_sarvam(text, api_key, character_data):
    speaker = character_data.get("speaker", "shubh")
    pace = character_data.get("pace", 1.0)
    temperature = character_data.get("temperature_tts", 0.6)
    language = character_data.get("language", "hi-IN")

    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }

    audio_bytes = b""

    for chunk in _chunk_text(text):
        payload = {
            "text": chunk,
            "target_language_code": language,
            "speaker": speaker,
            "pace": pace,
            "temperature": temperature,
            "model": SARVAM_MODEL,
            "output_audio_codec": "mp3",
            "enable_preprocessing": True
        }

        response = requests.post(
            SARVAM_URL, headers=headers, json=payload, timeout=60
        )
        response.raise_for_status()

        result = response.json()
        audio_bytes += base64.b64decode(result["audios"][0])

    return audio_bytes


# ------------------------------------------------
# EDGE TTS (fallback only)
# ------------------------------------------------

async def _edge_generate(text, voice, rate, pitch, volume):
    communicate = edge_tts.Communicate(
        text, voice, rate=rate, pitch=pitch, volume=volume
    )
    file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    await communicate.save(file.name)
    return file.name


def generate_voice_edge(text, character_data):
    voice = character_data.get("voice", "hi-IN-MadhurNeural")
    rate = character_data.get("rate", "+0%")
    pitch = character_data.get("pitch", "+0Hz")
    volume = character_data.get("volume", "+0%")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            _edge_generate(text, voice, rate, pitch, volume)
        )
    finally:
        loop.close()


# ------------------------------------------------
# PUBLIC ENTRY POINT
# ------------------------------------------------

def play_voice(text, character_data, sarvam_key):
    """
    Tries Sarvam AI first (better quality for Hindi). Falls back to Edge TTS
    automatically if no Sarvam key is set, or if the Sarvam call fails for
    any reason, so voice never just breaks silently.
    """
    if sarvam_key:
        try:
            audio_bytes = generate_voice_sarvam(text, sarvam_key, character_data)
            st.audio(audio_bytes, format="audio/mp3")
            return
        except Exception as e:
            st.caption(f"⚠️ Sarvam AI voice failed, using backup voice. ({e})")

    audio_file = generate_voice_edge(text, character_data)
    st.audio(audio_file, format="audio/mp3")