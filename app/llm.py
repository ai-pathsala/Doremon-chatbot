import requests
from groq import Groq


# llama-3.1-8b-instant and llama-3.3-70b-versatile were deprecated by Groq
# (June 2026). openai/gpt-oss-120b is the recommended free-tier replacement
# and follows "stay in character / stay in Hinglish" instructions noticeably
# better than the old 8B model did.
GROQ_MODEL = "openai/gpt-oss-120b"

MISTRAL_MODEL = "mistral-small-latest"


# ----------------------------------
# HINGLISH ADHERENCE CHECK
# ----------------------------------
# Groq/Mistral sometimes drift into full English mid-conversation even when
# told not to. Instead of just hoping the prompt holds, we score the reply
# and retry once with a stronger nudge if it looks too English.

_HINGLISH_MARKERS = [
    "hai", "hoon", "hu", "hun", "tum", "tumhara", "tumhe", "kya", "nahi",
    "nahin", "mera", "meri", "tera", "teri", "acha", "accha", "matlab",
    "kar", "karo", "karta", "karti", "raha", "rahi", "rahe", "bhi", "toh",
    "to", "bhai", "yaar", "dost", "kyun", "kaise", "kab", "kahan", "abhi",
    "thoda", "bahut", "hain", "tha", "thi", "the", "aap", "mujhe", "usse",
    "wala", "wali", "sab", "kuch", "koi", "chalo", "arre", "haan", "nai"
]


def _hinglish_score(text):
    words = [w.strip(".,!?\"'").lower() for w in text.split()]
    words = [w for w in words if w]
    if not words:
        return 1.0  # empty text, don't trigger a pointless retry
    marker_hits = sum(1 for w in words if w in _HINGLISH_MARKERS)
    return marker_hits / len(words)


def _needs_retry(text, min_words=6, min_score=0.08):
    word_count = len(text.split())
    if word_count < min_words:
        return False  # too short to judge fairly
    return _hinglish_score(text) < min_score


_RETRY_NUDGE = (
    "\n\nIMPORTANT: Your previous reply had too many plain English "
    "sentences. Rewrite your ENTIRE reply in Hinglish only (Hindi words in "
    "Roman/English script, mixed naturally with a few English words), like "
    "a real Indian friend texting. Do not use full English sentences."
)


# ----------------------------------
# GROQ
# ----------------------------------

def call_groq(api_key, system_prompt, history, temperature):
    client = Groq(api_key=api_key)

    def _ask(sys_prompt):
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "system", "content": sys_prompt}] + history,
            temperature=temperature,
            max_tokens=400
        )
        return response.choices[0].message.content

    reply = _ask(system_prompt)

    if _needs_retry(reply):
        reply = _ask(system_prompt + _RETRY_NUDGE)

    return reply


# ----------------------------------
# MISTRAL
# ----------------------------------

def call_mistral(api_key, system_prompt, history, temperature):
    url = "https://api.mistral.ai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    def _ask(sys_prompt):
        data = {
            "model": MISTRAL_MODEL,
            "messages": [{"role": "system", "content": sys_prompt}] + history,
            "temperature": temperature,
            "max_tokens": 400
        }
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    reply = _ask(system_prompt)

    if _needs_retry(reply):
        reply = _ask(system_prompt + _RETRY_NUDGE)

    return reply
