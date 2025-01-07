import json
import logging
import ssl
import uuid
import base64
import asyncio

import websockets
from fastapi import WebSocket
import os

from .WebsocketClient import Client
from .vad.vad_factory import VADFactory
from .asr.asr_factory import ASRFactory


SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2


class WebSocketHandler:
    def __init__(
        self,
        sampling_rate=16000,
        samples_width=2,
    ):
        self.vad_pipeline = VADFactory.create_vad_pipeline(
            "silero", auth_token=os.environ["HUGGINGFACE_API_KEY"]
        )
        self.asr_pipeline = ASRFactory.create_asr_pipeline("faster_whisper_docker")
        self.sampling_rate = sampling_rate
        self.samples_width = samples_width
        self.connected_clients = {}
        self.transcriptions = {}
        self.processing_tasks = {}

    async def handle_audio(self, client: Client, websocket: WebSocket):
        client_tasks = []
        self.processing_tasks[client.client_id] = client_tasks
        self.transcriptions[client.client_id] = []
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
                    # Wait for all pending processing tasks to complete
                    if client_tasks:
                        logging.info(
                            f"Waiting for {len(client_tasks)} pending tasks to complete"
                        )
                        results = await asyncio.gather(*client_tasks)
                        logging.info("All processing tasks completed")

                        # Compile final transcription
                        final_transcription = {
                            "type": "final_transcription",
                            "client_id": client.client_id,
                            "transcriptions": self.transcriptions[client.client_id],
                            "total_processing_time": sum(
                                t.get("processing_time", 0)
                                for t in self.transcriptions[client.client_id]
                            ),
                        }
                        print(final_transcription)
                        # Send final transcription
                        # await websocket.send_text(json.dumps(final_transcription))

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
