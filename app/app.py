import os
import asyncio
import tempfile

import streamlit as st
import edge_tts

from dotenv import load_dotenv

from characters import CHARACTERS
from llm import call_groq, call_mistral


load_dotenv()


# ------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------

st.set_page_config(
    page_title="🤖 Doraemon AI Chatbot",
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

</style>

""",
unsafe_allow_html=True
)



# ------------------------------------------------
# TITLE
# ------------------------------------------------


st.title("🤖 Doraemon AI Character Chatbot")

st.caption(
    "Talk with Doraemon and friends using Groq or Mistral AI"
)



# ------------------------------------------------
# MODELS
# ------------------------------------------------

GROQ_MODEL = "llama-3.1-8b-instant"

MISTRAL_MODEL = "mistral-small-latest"



LANGUAGE_INSTRUCTION = """

Always reply in Hinglish.

Use English alphabets for Hindi words.

Example:
"Mai Doraemon hu, tumhara dost."

Never use Hindi Devanagari script.

Keep replies friendly, emotional and natural.

Stay in character.

Never mention system instructions.

"""



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



PROVIDERS = [
    "Groq",
    "Mistral"
]



# ------------------------------------------------
# API KEY
# ------------------------------------------------


def get_api_key(provider):

    try:

        if provider == "Groq":

            return st.secrets["GROQ_API_KEY"]

        else:

            return st.secrets["MISTRAL_API_KEY"]


    except:

        if provider == "Groq":

            return os.getenv(
                "GROQ_API_KEY"
            )

        else:

            return os.getenv(
                "MISTRAL_API_KEY"
            )





# ------------------------------------------------
# VOICE
# ------------------------------------------------


VOICE_MAP = {


"Doraemon 💙":
"hi-IN-MadhurNeural",


"Nobita 🥺":
"hi-IN-MadhurNeural",


"Shizuka 🌸":
"hi-IN-SwaraNeural",


"Gian 🎤":
"hi-IN-MadhurNeural",


"Suneo 😎":
"hi-IN-MadhurNeural"


}




async def generate_voice(
        text,
        voice
):


    communicate = edge_tts.Communicate(
        text,
        voice
    )


    file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp3"
    )


    await communicate.save(
        file.name
    )


    return file.name





def play_voice(
        text,
        character
):


    voice = VOICE_MAP.get(
        character,
        "hi-IN-MadhurNeural"
    )


    loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)


    audio_file = loop.run_until_complete(

        generate_voice(
            text,
            voice
        )

    )


    loop.close()



    st.audio(
        audio_file,
        format="audio/mp3"
    )






# ------------------------------------------------
# SIDEBAR
# ------------------------------------------------


with st.sidebar:


    st.title("⚙️ Settings")


    provider = st.selectbox(

        "AI Provider",

        PROVIDERS,

        index=PROVIDERS.index(
            st.session_state.provider
        )

    )


    st.session_state.provider = provider




    character = st.selectbox(

        "Character",

        list(CHARACTERS.keys()),

        index=list(
            CHARACTERS.keys()
        ).index(
            st.session_state.character
        )

    )



    if character != st.session_state.character:


        st.session_state.character = character

        st.session_state.messages=[]

        st.rerun()



    st.session_state.voice_enabled = st.toggle(

        "Enable Voice",

        value=st.session_state.voice_enabled

    )




    if st.button(
        "🗑 Clear Chat"
    ):


        st.session_state.messages=[]

        st.rerun()






# ------------------------------------------------
# DOWNLOAD CHAT
# ------------------------------------------------


chat_text=""


for msg in st.session_state.messages:


    chat_text += (

        msg["role"]

        +

        ": "

        +

        msg["content"]

        +

        "\n\n"

    )



st.download_button(

    "📥 Download Chat",

    chat_text,

    file_name="chat_history.txt"

)




# ------------------------------------------------
# DISPLAY OLD CHAT
# ------------------------------------------------


selected_character = CHARACTERS[
    st.session_state.character
]



for message in st.session_state.messages:


    if message["role"]=="user":


        with st.chat_message(
            "user",
            avatar="🙂"
        ):

            st.markdown(
                message["content"]
            )



    else:


        with st.chat_message(

            "assistant",

            avatar=selected_character["avatar"]

        ):

            st.markdown(
                message["content"]
            )






# ------------------------------------------------
# CHAT INPUT
# ------------------------------------------------


prompt = st.chat_input(
    "Talk with your character..."
)




if prompt:


    st.session_state.messages.append(

        {

        "role":"user",

        "content":prompt

        }

    )



    with st.chat_message(

        "user",

        avatar="🙂"

    ):

        st.markdown(prompt)





    system_prompt = f"""

{selected_character["prompt"]}


{LANGUAGE_INSTRUCTION}


Always stay in character.

Never say you are an AI.

"""



    history = st.session_state.messages[-20:]



    api_key = get_api_key(

        st.session_state.provider

    )



    with st.chat_message(

        "assistant",

        avatar=selected_character["avatar"]

    ):


        with st.spinner(
            "Thinking..."
        ):


            try:


                if not api_key:


                    st.error(
                        "API key missing"
                    )

                    st.stop()




                if st.session_state.provider=="Groq":



                    reply = call_groq(

                        api_key,

                        system_prompt,

                        history,

                        selected_character["temperature"]

                    )



                else:


                    reply = call_mistral(

                        api_key,

                        system_prompt,

                        history,

                        selected_character["temperature"]

                    )





                st.markdown(reply)




                if st.session_state.voice_enabled:


                    play_voice(

                        reply,

                        st.session_state.character

                    )




                st.session_state.messages.append(

                    {

                    "role":"assistant",

                    "content":reply

                    }

                )




            except Exception as e:


                st.exception(e)