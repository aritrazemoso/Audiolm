import os
from openai import AsyncOpenAI
from src.util import save_audio_to_file
from .asr_interface import ASRInterface


class GroqASR(ASRInterface):
    def __init__(self, **kwargs):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        self.client = AsyncOpenAI(
            api_key=api_key, base_url="https://api.groq.com/openai/v1"
        )

    async def transcribe(self, client):
        file_path = await save_audio_to_file(
            client.scratch_buffer, client.get_file_name()
        )

        with open(file_path, "rb") as audio:
            response = await self.client.audio.transcriptions.create(
                file=audio,
                language=client.config.get("language"),
                model="whisper-large-v3-turbo",
            )

        os.remove(file_path)

        return {
            "language": getattr(response, "language", "UNSUPPORTED_BY_GROQ"),
            "language_probability": getattr(response, "language_probability", None),
            "text": getattr(response, "text", "").strip(),
            "words": getattr(response, "words", "UNSUPPORTED_BY_GROQ"),
        }
