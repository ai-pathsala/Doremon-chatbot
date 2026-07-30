import requests
from groq import Groq


# llama-3.1-8b-instant and llama-3.3-70b-versatile were deprecated by Groq
# (June 2026). openai/gpt-oss-120b is the free-tier replacement and follows
# "stay in Hinglish" instructions noticeably better than the old 8B model.
GROQ_MODEL = "openai/gpt-oss-120b"

MISTRAL_MODEL = "mistral-small-latest"

MAX_RETRIES = 2


# ----------------------------------
# HINGLISH ADHERENCE CHECK
# ----------------------------------
# Two checks, either of which triggers a retry:
#  1) Global ratio of Hinglish marker words across the whole reply.
#  2) Per-sentence scan — catches replies that mix one good Hinglish
#     sentence with one full-English sentence, which the global ratio alone
#     can miss.

_HINGLISH_MARKERS = {
    "hai", "hoon", "hu", "hun", "tum", "tumhara", "tumhe", "kya", "nahi",
    "nahin", "mera", "meri", "tera", "teri", "acha", "accha", "matlab",
    "kar", "karo", "karta", "karti", "raha", "rahi", "rahe", "bhi", "toh",
    "to", "bhai", "yaar", "dost", "kyun", "kaise", "kab", "kahan", "abhi",
    "thoda", "bahut", "hain", "tha", "thi", "the", "aap", "mujhe", "usse",
    "wala", "wali", "sab", "kuch", "koi", "chalo", "arre", "haan", "nai",
    "samjha", "samjhe", "pata", "dekh", "dekho", "suno", "chal", "hoga",
    "hogi", "karega", "karegi", "milta", "milti", "apna", "apne", "iske",
    "uske", "isse", "hume", "humein", "tujhe", "tere", "mere", "unko"
}


def _words(text):
    return [w.strip(".,!?\"'()").lower() for w in text.split()]


def _hinglish_ratio(text):
    words = [w for w in _words(text) if w]
    if not words:
        return 1.0  # empty text, don't trigger a pointless retry
    hits = sum(1 for w in words if w in _HINGLISH_MARKERS)
    return hits / len(words)


def _has_bad_sentence(text, min_len=5):
    for sentence in text.replace("!", ".").replace("?", ".").split("."):
        words = [w for w in _words(sentence) if w]
        if len(words) >= min_len:
            if not any(w in _HINGLISH_MARKERS for w in words):
                return True
    return False


def _needs_retry(text, min_words=6, min_ratio=0.08):
    word_count = len(text.split())
    if word_count < min_words:
        return False  # too short to fairly judge
    return _hinglish_ratio(text) < min_ratio or _has_bad_sentence(text)


_RETRY_NUDGE = (
    "\n\nIMPORTANT: Your previous reply had too many plain English "
    "sentences. Rewrite your ENTIRE reply in Hinglish only (Hindi words in "
    "Roman/English script, mixed naturally with a few English words), like "
    "a real Indian friend texting. Every sentence must contain Hindi words "
    "— do not write any full English sentence."
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

    sys_prompt = system_prompt
    reply = _ask(sys_prompt)

    attempts = 0
    while _needs_retry(reply) and attempts < MAX_RETRIES:
        sys_prompt = sys_prompt + _RETRY_NUDGE
        reply = _ask(sys_prompt)
        attempts += 1

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

    sys_prompt = system_prompt
    reply = _ask(sys_prompt)

    attempts = 0
    while _needs_retry(reply) and attempts < MAX_RETRIES:
        sys_prompt = sys_prompt + _RETRY_NUDGE
        reply = _ask(sys_prompt)
        attempts += 1

    return reply