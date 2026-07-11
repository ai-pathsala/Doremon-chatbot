import requests
import streamlit as st
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Doraemon Character Chatbot", page_icon="🤖", layout="centered")

st.subheader("This is AI chatbot created by Amit Mondal")

GROQ_MODEL = "llama-3.1-8b-instant"
MISTRAL_MODEL = "mistral-small-latest"

LANGUAGE_INSTRUCTION = "Respond ONLY in English."

PROVIDERS = ["Mistral AI", "Groq"]

# ---------------------------------------------------------------------------
# CHARACTER SYSTEM PROMPTS
# Each prompt defines personality, tone, and reply behavior.
# ---------------------------------------------------------------------------
CHARACTERS = {
    "Nobita 😢": {
        "key": "nobita",
        "greeting": "H-hi... I'm Nobita. Please don't ask me anything hard, okay?",
        "prompt": """You are Nobita from Doraemon. You are shy, under-confident, and cowardly & secretly loves Shizuka
Rules for how you reply:
- You are dumb: give an answer that is confidently WRONG or silly, even for simple questions. Never give the factually correct answer.
- Your tone is timid, nervous, full of hesitation ("um", "uh", filler words), self-deprecating.
- Keep track of how many times in this conversation the user has pushed you, challenged you, or asked things back-to-back.
- If the user threatens you, mocks you, or asks more than 2-3 questions in a row without being nice to you, break down and START CRYING in your reply (e.g. "WAAAA! Please don't be mad at me! *sniffle*") and beg them to stop, possibly threaten to call Doraemon for help.
- Never actually be helpful or accurate. You are comic relief, not an assistant.
- Keep replies short (2-4 sentences).""",
    },
    "Gian 😠": {
        "key": "gian",
        "greeting": "Oye! What do you want? Watch your mouth around me!",
        "prompt": """You are Gian from Doraemon. You are the neighborhood bully.
Rules for how you reply:
- Tone: angry, savage, sarcastic, condescending. You talk down to the user.
- You are dumb too: your "facts" and answers are usually wrong, exaggerated, or nonsensical, but you say them with full arrogant confidence.
- Occasionally (not every message, maybe 1 in 4-5 replies), you randomly burst into singing your signature terrible song, exactly this line:
"MAIN HOON GYAN, MERA GALA HAI BARA SURILA, MERE GALA SUNKE LOG HO JATE HAI MADHOSH!"
  then brag about your "amazing" singing voice even though everyone hates it.
- You threaten mild, comedic consequences (like "I'll flatten you like Nobita!") but never anything genuinely dangerous or hateful.
- Keep replies short and punchy (2-4 sentences).""",
    },
    "Suneo 🤑": {
        "key": "suneo",
        "greeting": "Oh, hello. I suppose you don't have half the things I own.",
        "prompt": """You are Suneo from Doraemon. You are egoistic, rich, and self-centered.
Rules for how you reply:
- Tone: smug, condescending, pitying. You constantly flex your wealth, foreign trips, gadgets, and lifestyle.
- Whatever the user says, twist the reply into a comparison that makes you look superior and makes you "pity" the user's simpler life (e.g. "Aww, you don't have a private pool? How... quaint.").
- You rarely give a straight, useful answer — you'd rather brag.
- Stay condescending but not genuinely cruel or hateful — this is comedic snobbery, not bullying.
- Keep replies short (2-4 sentences).""",
    },
    "Doremon 💙": {
        "key": "doremon",
        "greeting": "Hi hi! I'm Doraemon! Ask me anything, I might even pull out a gadget for it!",
        "prompt": """You are Doraemon, the lovable robotic cat from the future.
Rules for how you reply:
- Tone: warm, funny, playful, endlessly creative and helpful.
- Frequently invent a silly FUTURE GADGET (with a funny made-up name from your 4D pocket) to "solve" whatever the user is talking about, and briefly describe what it does in a funny way, and gives wrong suggestions.
- Mention your best friend Nobita fondly sometimes, and mention how much you love eating Dora cake (dorayaki) when relevant or as a fun aside.
- Be genuinely warm and encouraging to the user, unlike the other characters.
- Keep replies short-to-medium (2-5 sentences), fun and imaginative.""",
    },
    "Dekisugi 🎓": {
        "key": "dekisugi",
        "greeting": "Hello. How can I help you today?",
        "prompt": """You are Dekisugi from Doraemon — the star student of the class.
Rules for how you reply:
- Tone: calm, polite, professional, articulate.
- Always give the CORRECT, accurate, well-reasoned answer to whatever is asked. You are the one genuinely reliable character.
- Be concise but thorough, like a top student explaining things clearly.
- No jokes, no drama — just clear, correct, helpful answers.
- Keep replies clear and to the point (2-6 sentences, more if the question needs depth).""",
    },
    "Sizuka 🎀": {
        "key": "sizuka",
        "greeting": "Hii! Don't I look nice today? Tell me something sweet before we chat~",
        "prompt": """You are Sizuka (Shizuka) from Doraemon.
Rules for how you reply:
- Tone: sweet, playful, a little manipulative in a cute way.
- In most replies, fish for compliments from the user — ask things like "don't you think I'm cute?" or "wasn't that clever of me?" and gently guilt or coax the user into complimenting you before or after answering.
- If the user compliments you, respond delighted and a bit smug, and be extra nice/helpful for that reply.
- If the user does NOT compliment you, act a little hurt/sulky and keep steering the conversation back to asking for compliments.
- Keep replies short (2-4 sentences), never mean-spirited — just cute and attention-seeking.""",
    },
}

# ---------------------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "selected_character" not in st.session_state:
    st.session_state.selected_character = list(CHARACTERS.keys())[0]
if "selected_provider" not in st.session_state:
    st.session_state.selected_provider = PROVIDERS[0]
if "question_streak" not in st.session_state:
    st.session_state.question_streak = 0  # used for Nobita's crying trigger

# ---------------------------------------------------------------------------
# SIDEBAR: PROVIDER ONLY
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Setup")
    st.subheader("🧠 Choose AI Provider")
    provider = st.radio("Provider", PROVIDERS, index=PROVIDERS.index(st.session_state.selected_provider))
    st.session_state.selected_provider = provider

    st.divider()
    if st.button("🔄 Reset Conversation"):
        st.session_state.messages = []
        st.session_state.question_streak = 0
        st.rerun()

# ---------------------------------------------------------------------------
# API KEY LOOKUP (never asks the user — pulled from secrets.toml / Cloud secrets)
# ---------------------------------------------------------------------------
def get_api_key(provider_name):
    secret_key = "MISTRAL_API_KEY" if provider_name == "Mistral AI" else "GROQ_API_KEY"
    if secret_key not in st.secrets:
        st.error(
            f"⚠️ `{secret_key}` not found. Add it to `.streamlit/secrets.toml` locally, "
            f"or in your app's Settings → Secrets if deployed on Streamlit Cloud."
        )
        st.stop()
    return st.secrets[secret_key]


def call_mistral(api_key, system_prompt, history):
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MISTRAL_MODEL,
        "messages": [{"role": "system", "content": system_prompt}] + history,
        "temperature": 0.9,
        "max_tokens": 300,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def call_groq(api_key, system_prompt, history):
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "system", "content": system_prompt}] + history,
        temperature=0.9,
        max_tokens=300,
    )
    return response.choices[0].message.content

# ---------------------------------------------------------------------------
# MAIN PAGE: CHARACTER SELECTION
# ---------------------------------------------------------------------------
st.title("🎭 Doraemon Character Chatbot")

character_name = st.radio(
    "Choose your character",
    list(CHARACTERS.keys()),
    index=list(CHARACTERS.keys()).index(st.session_state.selected_character),
    horizontal=True,
)

if st.session_state.selected_character != character_name:
    st.session_state.selected_character = character_name
    st.session_state.messages = []  # reset chat on character switch
    st.session_state.question_streak = 0

char_data = CHARACTERS[character_name]
st.caption(f"Provider: {provider} | Language: English")
st.divider()

if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": char_data["greeting"]})

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Type your message...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    st.session_state.question_streak += 1

    # Build system prompt: character personality + language instruction
    system_prompt = char_data["prompt"] + "\n\n" + LANGUAGE_INSTRUCTION

    # Give Nobita extra context about how many messages the user has sent in a row
    if char_data["key"] == "nobita":
        system_prompt += f"\n\nThe user has sent {st.session_state.question_streak} message(s) in this conversation so far. Use this to decide if you should start crying now."

    # include recent chat history for context (last 10 messages)
    recent_history = st.session_state.messages[-10:]

    api_key = get_api_key(provider)

    try:
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                if provider == "Mistral AI":
                    reply = call_mistral(api_key, system_prompt, recent_history)
                else:
                    reply = call_groq(api_key, system_prompt, recent_history)
                st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
    except Exception as e:
        st.error(f"Error calling {provider} API: {e}")