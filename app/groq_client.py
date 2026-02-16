import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def summarize_text(text: str) -> str:
    if not text.strip():
        return ""

    prompt = f"""
    You are summarizing a section of a commercial loan agreement.

    First determine what TYPE of section this is:
    - Conditions precedent
    - Representation or warranty
    - Covenant
    - Event of default
    - Fee provision
    - Miscellaneous clause

    Then summarize it appropriately:
    - Extract legal obligations
    - Identify triggers and consequences
    - Identify financial requirements if any
    - Explain practical legal effect

    Write clearly in structured bullet format.
    Maximum 250 words.

    TEXT:
    {text}
    """

    resp = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": "You are an expert legal analyst. "
                    "You summarize credit agreements by extracting their legal meaning "
                    "and organizing obligations clearly."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=400
    )

    return resp.choices[0].message.content.strip()
