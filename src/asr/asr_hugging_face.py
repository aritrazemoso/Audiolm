import os
from openai import AsyncOpenAI
from src.util import save_audio_to_file
from .asr_interface import ASRInterface
from aiohttp import ClientSession


API_URL = "https://api-inference.huggingface.co/models/openai/whisper-large-v3-turbo"


class HuggingFaceAsr(ASRInterface):
    async def convert_audio_text(self, file, headers):
        async with ClientSession() as session:
            async with session.post(API_URL, headers=headers, data=file) as response:
                return await response.json()

    def __init__(self, **kwargs):
        api_key = os.getenv("HUGGINGFACE_API_KEY")
        if not api_key:
            raise ValueError("Hugging Face environment variable not set")
        self.headers = {
            "Authorization": f"Bearer {api_key}",
        }

    async def transcribe(self, client):
        file_path = await save_audio_to_file(
            client.scratch_buffer, client.get_file_name()
        )

        with open(file_path, mode="rb") as audio:
            response = await self.convert_audio_text(audio, self.headers)
            print(response)

        os.remove(file_path)

        return {
            "language": "UNSUPPORTED_BY_HUGGINGFACE_WHISPER",
            "language_probability": None,
            "text": response.get("text", "").strip(),
            "words": "UNSUPPORTED_BY_HUGGINGFACE_WHISPER",
        }
