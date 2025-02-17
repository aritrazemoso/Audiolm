from dataclasses import dataclass
from typing import AsyncGenerator, Optional, Dict, Any
import websockets
import asyncio
import json
import base64
from fastapi import WebSocket
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings as ElevenLabsVoiceSettings
from asyncio import Queue
from src.util import save_audio_bytes_to_file, check_file_exists
from src.constant import AUDIO_SAVE_PATH
import os
from uuid import uuid4


@dataclass
class VoiceSettings:
    stability: float = 0.5
    similarity_boost: float = 0.8
    use_speaker_boost: bool = False


class ElevenLabsClient:
    def __init__(self, voice_id: str, model_id: str):
        self.api_key = os.environ["ELEVENLABS_API_KEY"]
        self.voice_id = voice_id
        self.model_id = model_id
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.voice_settings = VoiceSettings()
        self.client = ElevenLabs(api_key=self.api_key)

    @property
    def ws_url(self) -> str:
        return f"wss://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream-input?model_id={self.model_id}"

    async def connect(self) -> None:
        self.websocket = await websockets.connect(self.ws_url)
        await self._send_initial_config()

    async def _send_initial_config(self) -> None:
        if not self.websocket:
            raise RuntimeError("WebSocket not connected")

        config = {
            "text": " ",
            "voice_settings": {
                "stability": self.voice_settings.stability,
                "similarity_boost": self.voice_settings.similarity_boost,
                "use_speaker_boost": self.voice_settings.use_speaker_boost,
            },
            "generation_config": {
                "flush": True,
            },
            "xi_api_key": self.api_key,
        }
        await self.websocket.send(json.dumps(config))

    async def stream_text(self, text: str) -> None:
        if not self.websocket:
            raise RuntimeError("WebSocket not connected")

        await self.websocket.send(
            json.dumps({"text": text, "try_trigger_generation": True})
        )

    async def send_eos(self) -> None:
        if not self.websocket:
            raise RuntimeError("WebSocket not connected")

        await self.websocket.send(
            json.dumps({"text": "", "try_trigger_generation": True, "eos": True})
        )

    async def text_to_speech(
        self,
        text: str,
        file_name: Optional[str] = str(uuid4()),
    ) -> None:
        filename = f"{file_name}.mp3"
        if await check_file_exists(filename, AUDIO_SAVE_PATH):
            return filename
        response = self.client.text_to_speech.convert(
            voice_id=self.voice_id,  # Adam pre-made voice
            output_format="mp3_22050_32",
            text=text,
            model_id="eleven_turbo_v2_5",  # use the turbo model for low latency
            voice_settings=ElevenLabsVoiceSettings(
                stability=0.95,
                similarity_boost=0.75,
                style=0.06,
                use_speaker_boost=True,
            ),
        )

        await save_audio_bytes_to_file(response, filename, AUDIO_SAVE_PATH)

        return filename

    async def close(self) -> None:
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
