from dataclasses import dataclass
from typing import AsyncGenerator, Optional, Dict, Any
import websockets
import asyncio
import json
import base64
from fastapi import WebSocket
from asyncio import Queue
import os


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
        print(config)
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

    async def close(self) -> None:
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
