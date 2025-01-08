from typing import AsyncGenerator, Optional, Dict, Any
from openai import OpenAI
import os


class ChatGPTClient:
    def __init__(self, model: str = "llama3-8b-8192"):
        self.model = model
        self.client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )  # Your OpenAI client instance

    async def stream_response(self, query: str) -> AsyncGenerator[str, None]:
        """Stream response from ChatGPT."""
        prompt = self._format_prompt(query)

        chat_completion = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
            stream=True,
        )

        for chunk in chat_completion:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _format_prompt(self, query: str) -> str:
        """Format the prompt for ChatGPT."""
        return f"""
            You are a helpful assistant. Please assist the user with their query.
            Think that you are an voice assistant. 
            You need to give answer as short as possible.
            ```{query}```
        """
