import openai
from openai import OpenAIError


class OpenAIService:
    """Thin wrapper around OpenAI chat completions."""

    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)

    def generate_response(self, prompt: str) -> str:
        """Return the assistant's reply for the given prompt."""
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
