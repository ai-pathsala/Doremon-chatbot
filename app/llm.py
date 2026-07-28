import requests
from groq import Groq


GROQ_MODEL = "llama-3.1-8b-instant"

MISTRAL_MODEL = "mistral-small-latest"


# ----------------------------------
# GROQ
# ----------------------------------

def call_groq(
    api_key,
    system_prompt,
    history,
    temperature
):

    client = Groq(
        api_key=api_key
    )


    response = client.chat.completions.create(

        model=GROQ_MODEL,

        messages=[
            {
                "role":"system",
                "content":system_prompt
            }
        ] + history,


        temperature=temperature,

        max_tokens=400
    )


    return response.choices[0].message.content



# ----------------------------------
# MISTRAL
# ----------------------------------

def call_mistral(
    api_key,
    system_prompt,
    history,
    temperature
):

    url = "https://api.mistral.ai/v1/chat/completions"


    headers = {

        "Authorization":
        f"Bearer {api_key}",

        "Content-Type":
        "application/json"

    }


    data = {

        "model":MISTRAL_MODEL,


        "messages":[

            {
                "role":"system",
                "content":system_prompt
            }

        ] + history,


        "temperature":temperature,


        "max_tokens":400
    }


    response = requests.post(

        url,

        headers=headers,

        json=data,

        timeout=60

    )


    response.raise_for_status()


    return response.json()["choices"][0]["message"]["content"]