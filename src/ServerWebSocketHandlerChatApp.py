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
import datetime


SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

voice_id = "pNInz6obpgDQGcFmaJgB"
model_id = "eleven_turbo_v2_5"


class ChatHistory:
    def __init__(self):
        self.conversations = {}  # userid -> list of messages

    def add_message(self, user_id: str, message: dict):
        if user_id not in self.conversations:
            self.conversations[user_id] = []
        self.conversations[user_id].append(message)

    def get_history(self, user_id: str) -> list:
        return self.conversations.get(user_id, [])


class WebSocketHandler:
    def __init__(
        self,
        sampling_rate=16000,
        samples_width=2,
    ):
        self.vad_pipeline = VADFactory.create_vad_pipeline(
            "silero", auth_token=os.environ["HUGGINGFACE_API_KEY"]
        )
        self.asr_pipeline = ASRFactory.create_asr_pipeline("groq")
        self.sampling_rate = sampling_rate
        self.samples_width = samples_width
        self.connected_clients = {}
        self.transcriptions = {}
        self.processing_tasks = {}
        self.chatgpt_handler = ChatGPTHandler(api_key=os.environ["GROQ_API_KEY"])
        self.elevenlabs_client = ElevenLabsClient(voice_id=voice_id, model_id=model_id)
        self.chatgpt_client = ChatGPTClient()
        self.chat_history = ChatHistory()

        self.audio_stream_manager = AudioStreamManager(
            self.elevenlabs_client, self.chatgpt_client
        )

    async def handle_audio(self, client: Client, websocket: WebSocket, user_id: str):
        client_tasks = []
        self.processing_tasks[client.client_id] = client_tasks
        self.transcriptions[client.client_id] = []

        # Send chat history to client on connection
        history = self.chat_history.get_history(user_id)
        if history:
            await websocket.send_text(
                json.dumps({"type": "chat_history", "history": history})
            )

        while True:
            message = await websocket.receive()
            if isinstance(message.get("bytes"), bytes):
                client.append_audio_data(audio_data=message.get("bytes"))
            elif isinstance(message.get("text"), str):
                config = json.loads(message.get("text"))
                if config.get("type") == "config":
                    client.update_config(config["data"])
                    logging.debug(f"Updated config: {client.config}")
                    continue
                elif config.get("isFinal") == True:
                    if client_tasks:
                        logging.info(
                            f"Waiting for {len(client_tasks)} pending tasks to complete"
                        )
                        results = await asyncio.gather(*client_tasks)
                        logging.info("All processing tasks completed")

                        full_text = " ".join(
                            t["text"] for t in self.transcriptions[client.client_id]
                        )

                        # Create final transcription
                        final_transcription = {
                            "type": "final_transcription",
                            "client_id": client.client_id,
                            "transcriptions": self.transcriptions[client.client_id],
                            "full_text": full_text,
                            "total_processing_time": sum(
                                t.get("processing_time", 0)
                                for t in self.transcriptions[client.client_id]
                            ),
                        }

                        # Store user message in chat history
                        self.chat_history.add_message(
                            user_id,
                            {
                                "role": "user",
                                "content": full_text,
                                "timestamp": datetime.datetime.now().isoformat(),
                            },
                        )

                        await websocket.send_text(json.dumps(final_transcription))

                        # Get ChatGPT response and audio stream
                        chatgpt_response = await self.chatgpt_handler.ask_chatgpt(
                            websocket,
                            question=full_text,
                            context="You are a helpful assistant. Please respond to the following transcribed speech.",
                            return_response=True,  # Modified to return the response
                        )

                        # Store assistant response in chat history
                        self.chat_history.add_message(
                            user_id,
                            {
                                "role": "assistant",
                                "content": chatgpt_response,
                                "timestamp": datetime.datetime.now().isoformat(),
                            },
                        )

                        await self.audio_stream_manager.handle_stream(
                            websocket, chatgpt_response
                        )

                    await websocket.close()
                    break
            else:
                logging.warning(f"Unexpected message type from {client.client_id}")

            task = asyncio.create_task(
                client.process_audio(
                    websocket,
                    self.vad_pipeline,
                    asr_pipeline=self.asr_pipeline,
                    transcriptions_list=self.transcriptions[client.client_id],
                )
            )
            client_tasks.append(task)

            # Clean up completed tasks
            client_tasks[:] = [t for t in client_tasks if not t.done()]

    async def handle_websocket(self, websocket: WebSocket, user_id: str):
        client_id = str(uuid.uuid4())
        client = Client(client_id, SAMPLE_RATE, SAMPLE_WIDTH)

        self.connected_clients[client_id] = client

        print(f"Client {client_id} connected with user_id {user_id}")

        try:
            await self.handle_audio(client, websocket, user_id)
        except websockets.ConnectionClosed as e:
            print(f"Connection with {client_id} closed: {e}")
        finally:
            print(f"Client {client_id} disconnected")
            if client_id in self.processing_tasks:
                del self.processing_tasks[client_id]
            if client_id in self.transcriptions:
                del self.transcriptions[client_id]
