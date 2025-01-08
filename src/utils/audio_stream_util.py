from dataclasses import dataclass
from typing import AsyncGenerator, Literal, Optional, Dict, Any
import websockets
import asyncio
import json
import base64
from fastapi import WebSocket
from asyncio import Queue
from .chatgpt_util import ChatGPTClient
from .elevenlabs_util import ElevenLabsClient


class AudioStreamManager:
    def __init__(
        self, elevenlabs_client: ElevenLabsClient, chatgpt_client: ChatGPTClient
    ):
        self.elevenlabs = elevenlabs_client
        self.chatgpt = chatgpt_client

    async def stream_audio(
        self, client_ws: WebSocket, websocket: websockets.WebSocketClientProtocol
    ) -> None:
        """Stream audio directly from ElevenLabs to client."""
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                if data.get("audio"):
                    # Directly send audio to client
                    audio_chunk = base64.b64decode(data["audio"])
                    await client_ws.send_bytes(audio_chunk)
                elif data.get("isFinal"):
                    await client_ws.send_json({"type": "audio_end"})
                    break
            except websockets.exceptions.ConnectionClosed as e:
                print("ElevenLabs connection closed:", e)
                await client_ws.send_json(
                    {"type": "error", "content": "Audio stream connection closed"}
                )
                break

    async def handle_stream(self, client_ws: WebSocket, query: str) -> None:
        """Handle the complete streaming process."""
        try:
            # Connect to ElevenLabs
            await self.elevenlabs.connect()
            accumulated_text = ""

            # Start streaming audio in parallel with text processing
            stream_task = asyncio.create_task(
                self.stream_audio(client_ws, self.elevenlabs.websocket)
            )

            # Process ChatGPT response and send to ElevenLabs
            async for text_chunk in self.chatgpt.stream_response(query):
                # Send text to client
                await client_ws.send_json(
                    {"type": "chatgpt_response", "content": text_chunk}
                )

                # Accumulate and stream to ElevenLabs
                accumulated_text += text_chunk
                if (
                    text_chunk.endswith((".", "!", "?", "\n"))
                    or len(accumulated_text) > 100
                ):
                    await self.elevenlabs.stream_text(accumulated_text)
                    accumulated_text = ""

            # Handle any remaining text
            if accumulated_text:
                await self.elevenlabs.stream_text(accumulated_text)

            # Send end of stream signal
            await self.elevenlabs.send_eos()

            # Wait for audio streaming to complete
            await stream_task

        except Exception as e:
            print(f"Error in stream handling: {e}")
            await client_ws.send_json({"type": "error", "content": str(e)})
        finally:
            await self.elevenlabs.close()
