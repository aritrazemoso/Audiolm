import json
import logging
import ssl
import uuid
import base64
import asyncio

import websockets
from fastapi import WebSocket
import os
from src.utils.ChatgptUtil import ChatGPTHandler

from .WebsocketClient import Client
from .vad.vad_factory import VADFactory
from .asr.asr_factory import ASRFactory
from .utils.audio_stream_util import AudioStreamManager
from .utils.chatgpt_util import ChatGPTClient
from .utils.elevenlabs_util import ElevenLabsClient
from .utils.gladia_util import GladiaClient


SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

voice_id = "pNInz6obpgDQGcFmaJgB"
model_id = "eleven_turbo_v2_5"
import logging


class WebSocketHandler:
    def __init__(
        self,
        sampling_rate=16000,
        samples_width=2,
    ):

        self.sampling_rate = sampling_rate
        self.samples_width = samples_width
        self.connected_clients = {}
        self.transcriptions = {}
        self.processing_tasks = {}
        self.chatgpt_handler = ChatGPTHandler(api_key=os.environ["GROQ_API_KEY"])
        self.elevenlabs_client = ElevenLabsClient(voice_id=voice_id, model_id=model_id)
        self.chatgpt_client = ChatGPTClient()

        self.audio_stream_manager = AudioStreamManager(
            self.elevenlabs_client, self.chatgpt_client
        )
        self.gladiaClient = {}

    async def handle_gladia_transcription(
        self,
        gloadia_websocket: websockets.WebSocketClientProtocol,
        client_websocket: WebSocket,
    ):
        while True:
            message = await gloadia_websocket.recv()
            data = json.loads(message)
            if data.get("type") == "transcript":
                logging.debug(f"Received transcript: {data}")
                print()
            if message.data.is_final == True:
                logging.debug(f"Received final message")
                break

    async def handle_audio(self, client: Client, websocket: WebSocket):
        client_tasks = []
        self.processing_tasks[client.client_id] = client_tasks
        self.transcriptions[client.client_id] = []
        gladiaClient = GladiaClient()

        await gladiaClient.connect()

        self.gladiaClient[client.client_id] = gladiaClient

        transcription_trask = asyncio.create_task(
            self.handle_gladia_transcription(gladiaClient.websocket_client, websocket)
        )

        while True:
            message = await websocket.receive()
            if isinstance(message.get("bytes"), bytes):
                gladiaClient.send_audio(audio_data=message.get("bytes"))
            elif isinstance(message.get("text"), str):
                config = json.loads(message.get("text"))
                if config.get("type") == "config":
                    client.update_config(config["data"])
                    logging.debug(f"Updated config: {client.config}")
                    continue
                elif config.get("isFinal") == True:
                    # Wait for all pending processing tasks to complete
                    gladiaClient.send_eos_audio()
                    if transcription_trask.done():
                        logging.info("All processing tasks completed")
                        break
                    else:
                        await asyncio.gather(transcription_trask)
                    await websocket.close()
                    await gladiaClient.close()
                    break
            else:
                logging.warning(f"Unexpected message type from {client.client_id}")

    async def handle_websocket(self, websocket):
        client_id = str(uuid.uuid4())
        client = Client(client_id, SAMPLE_RATE, SAMPLE_WIDTH)

        self.connected_clients[client_id] = client

        print(f"Client {client_id} connected")

        try:
            await self.handle_audio(client, websocket)
        except websockets.ConnectionClosed as e:
            print(f"Connection with {client_id} closed: {e}")
        finally:
            print(f"Client {client_id} disconnected")
            if client_id in self.processing_tasks:
                del self.processing_tasks[client_id]
            if client_id in self.transcriptions:
                del self.transcriptions[client_id]
