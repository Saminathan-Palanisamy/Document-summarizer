# app/llm/groq_client.py

from groq import Groq

class GroqClient:
    def __init__(self, api_key: str, model: str):
        self.client = Groq(api_key=api_key)
        self.model = model

    def summarize(self, text: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert document summarizer."
                },
                {
                    "role": "user",
                    "content": f"Summarize the following content clearly:\n\n{text}"
                }
            ],
            max_tokens=300
        )

        return response.choices[0].message.content.strip()
