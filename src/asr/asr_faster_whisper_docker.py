import os
from openai import AsyncOpenAI
from src.util import save_audio_to_file
from .asr_interface import ASRInterface


## docker run --gpus=all --publish 8001:8000 --volume ~/.cache/huggingface:/root/.cache/huggingface --detach fedirz/faster-whisper-server:latest-cuda
class FasterWhisperDocker(ASRInterface):
    def __init__(self, **kwargs):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        self.client = AsyncOpenAI(
            base_url="http://localhost:8001/v1/", api_key="cant-be-empty"
        )

    async def transcribe(self, client):
        file_path = await save_audio_to_file(
            client.scratch_buffer, client.get_file_name()
        )

        with open(file_path, "rb") as audio:
            response = await self.client.audio.transcriptions.create(
                file=audio,
                language=client.config.get("language"),
                model="Systran/faster-whisper-large-v3",
                response_format="verbose_json",
            )

        os.remove(file_path)

        return {
            "language": getattr(response, "language", "UNSUPPORTED_BY_GROQ"),
            "language_probability": getattr(response, "language_probability", None),
            "text": getattr(response, "text", "").strip(),
            "words": getattr(response, "words", "UNSUPPORTED_BY_GROQ"),
        }
