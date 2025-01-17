import os
from aiohttp import ClientSession
import json
import websockets
from typing import Optional


class GladiaClient:
    def __init__(self):
        self.api_key = os.getenv("GLADIA_API_KEY")
        self.websocket_client: Optional[websockets.WebSocketClientProtocol] = None

    async def connect(self):
        if not self.api_key:
            raise ValueError("GLADIA_API_KEY environment variable not set")
        async with ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "X-Gladia-Key": self.api_key,
            }
            request_body = json.dumps(
                {
                    "encoding": "wav/pcm",
                    "sample_rate": 16000,
                    "bit_depth": 16,
                    "channels": 1,
                }
            )
            response = await session.post(
                "https://api.gladia.io/v2/live",
                headers=headers,
                data=request_body,
            )
            print(response)
            response_data = await response.json()
            self.websocket_url = response_data["url"]
        self.websocket_client = await websockets.connect(self.websocket_url)

    async def send_audio(self, audio_data):
        if not self.websocket_client:
            raise RuntimeError("WebSocket not connected")
        await self.websocket_client.send(audio_data)

    async def send_eos_audio(self):
        if not self.websocket_client:
            raise RuntimeError("WebSocket not connected")
        await self.websocket_client.send(
            json.dumps(
                {
                    "type": "stop_recording",
                }
            )
        )

    async def close(self):
        if self.websocket_client:
            await self.websocket_client.close()
            self.websocket_client = None
