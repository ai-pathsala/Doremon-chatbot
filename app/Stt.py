import requests


SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_STT_MODEL = "saaras:v3"


def transcribe_audio(audio_bytes, api_key, language_code="hi-IN"):
    """
    Sends recorded audio (e.g. from st.audio_input, WAV bytes) to Sarvam AI's
    Saaras v3 model and returns the transcribed text. Works for files under
    30 seconds (Sarvam's synchronous REST limit) — fine for chat-style voice
    messages.
    """
    headers = {
        "api-subscription-key": api_key
    }

    files = {
        "file": ("audio.wav", audio_bytes, "audio/wav")
    }

    data = {
        "model": SARVAM_STT_MODEL,
        "language_code": language_code,
        "mode": "transcribe"
    }

    response = requests.post(
        SARVAM_STT_URL, headers=headers, files=files, data=data, timeout=60
    )
    response.raise_for_status()

    result = response.json()
    return result.get("transcript", "").strip()