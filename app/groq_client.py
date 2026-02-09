import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def summarize_text(text: str) -> str:
    if not text.strip():
        return ""

    prompt = f"""
    Summarize the following legal section in clear, simple English.
    Keep it concise and accurate.

    TEXT:
    {text}
    """

    resp = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": "You are a legal document summarizer."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=400
    )

    return resp.choices[0].message.content.strip()
