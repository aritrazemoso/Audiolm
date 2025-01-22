import json
from .logger import logger as logging
import ssl
import uuid
import base64
import asyncio

from fastapi import WebSocket
import os
from fastapi.websockets import WebSocketState

from .WebsocketClient import Client
from .vad.vad_factory import VADFactory
from .asr.asr_factory import ASRFactory
from .utils_interview.audio_stream_util import AudioStreamManager
from .utils_interview.chatgpt_util import ChatGPTClient
from .utils_interview.elevenlabs_util import ElevenLabsClient
import datetime
from typing import Dict, List
from enum import Enum
from .types import InterviewHistory
from dataclasses import asdict
from .util import save_audio_to_file
import traceback
from .constant import AUDIO_SAVE_PATH
from src.utility.ResumeStorageUtil import ResumeStorage


SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

voice_id = "pNInz6obpgDQGcFmaJgB"
model_id = "eleven_turbo_v2_5"


class ChatHistory:
    def __init__(self):
        self.conversations = {}  # userid -> list of messages

    def add_message(self, user_id: str, message: InterviewHistory):
        if user_id not in self.conversations:
            self.conversations[user_id] = []
        self.conversations[user_id].append(message)

    def get_history(self, user_id: str) -> List[InterviewHistory]:
        return self.conversations.get(user_id, [])


class QuestionType(Enum):
    INTRO_QUESTION = "intro_question"
    FOLLOWUP_QUESTION = "followup_question"
    ANSWER = "answer"


class EventType(Enum):
    ASK_QUESTION = "askQuestion"
    AUDIO_PACKET = "audioPacket"
    END_QUESTION = "endQuestion"
    START_ANSWER = "startAnswer"
    END_ANSWER = "endAnswer"
    TRANSCRIPTION = "final_transcription"
    ASK_FOR_RESUME = "askForResume"
    RECEIVE_RESUME = "receiveResume"
    SUCCESS_FULL_RESUME_RECEIVED = "successFullResumeReceived"
    ANSWER = "answer"


class WebSocketHandler:
    def __init__(self, sampling_rate=16000, samples_width=2):
        self.vad_pipeline = VADFactory.create_vad_pipeline(
            "silero", auth_token=os.environ["HUGGINGFACE_API_KEY"]
        )
        self.asr_pipeline = ASRFactory.create_asr_pipeline("groq")
        self.sampling_rate = sampling_rate
        self.samples_width = samples_width
        self.connected_clients: Dict[str, Client] = {}
        self.active_sessions: Dict[str, Dict] = {}  # Store session state
        self.elevenlabs_client = ElevenLabsClient(voice_id=voice_id, model_id=model_id)
        self.chatgpt_client = ChatGPTClient()

        self.audio_stream_manager = AudioStreamManager(
            self.elevenlabs_client, self.chatgpt_client
        )
        self.chat_history = ChatHistory()
        self.resume_storage = ResumeStorage()

    async def handle_ask_question(self, client_id: str, websocket: WebSocket):
        """Handle the start of a new question"""
        self.active_sessions[client_id] = {
            "transcriptions": [],
            "processing_tasks": [],
            "current_audio": bytearray(),
        }
        # await websocket.send_json(
        #     {"type": EventType.ASK_QUESTION.value, "status": "ready"}
        # )

    async def handle_audio_packet(
        self, client_id: str, websocket: WebSocket, audio_data: bytes
    ):
        """Process incoming audio packet"""
        session = self.active_sessions[client_id]
        client = self.connected_clients[client_id]

        # Append audio data
        client.append_audio_data(audio_data)

        # Create and track processing task
        task = asyncio.create_task(
            client.process_audio(
                websocket,
                self.vad_pipeline,
                asr_pipeline=self.asr_pipeline,
                transcriptions_list=session["transcriptions"],
            )
        )
        session["processing_tasks"].append(task)

        session["current_audio"].extend(audio_data)  # Store audio_data

        # Clean up completed tasks
        session["processing_tasks"] = [
            t for t in session["processing_tasks"] if not t.done()
        ]

    async def handle_end_question(
        self, client_id: str, websocket: WebSocket, user_id: str
    ):
        """Process the end of a question and generate response"""
        session = self.active_sessions[client_id]

        # Wait for all processing tasks to complete
        if session["processing_tasks"]:
            await asyncio.gather(*session["processing_tasks"])

        response_id = str(uuid.uuid4())

        # Compile final transcription
        full_text = " ".join(t["text"] for t in session["transcriptions"])
        final_transcription = {
            "type": EventType.TRANSCRIPTION.value,
            "text": full_text,
            "segments": session["transcriptions"],
            "response_id": response_id,
        }

        user_answer_file_name = f"{response_id}_answer.wav"

        ## Store the user answer audio
        file_save_task = asyncio.create_task(
            save_audio_to_file(
                session["current_audio"], user_answer_file_name, AUDIO_SAVE_PATH
            )
        )

        # Store in chat history

        # Send transcription
        await websocket.send_json(final_transcription)

        self.chat_history.add_message(
            user_id,
            InterviewHistory(
                role="user",
                content=full_text,
                timestamp=datetime.datetime.now(),
                question_type=QuestionType.ANSWER.value,
                audio=user_answer_file_name,
            ),
        )

        # Generate and stream audio response
        [gptResponse, gptResponseAudio] = await self.audio_stream_manager.handle_stream(
            websocket,
            full_text,
            await self.resume_storage.get_resume(user_id),
            response_id,
            history=self.chat_history.get_history(user_id),
        )

        print("Gpt Response Audio type", type(gptResponseAudio))

        print("user_answer_save", await file_save_task)

        # Save response history
        self.chat_history.add_message(
            user_id,
            InterviewHistory(
                role="assistant",
                content=gptResponse,
                timestamp=datetime.datetime.now(),
                question_type=QuestionType.FOLLOWUP_QUESTION.value,
                audio=gptResponseAudio,
            ),
        )

        # Clear session data
        self.active_sessions[client_id] = {
            "transcriptions": [],
            "processing_tasks": [],
            "current_audio": bytearray(),
        }

    async def handle_introduction2(self, websocket: WebSocket, user_id: str):
        response_id = str(uuid.uuid4())

        [gptResponse, gptResponseAudio] = await self.audio_stream_manager.handle_stream(
            websocket,
            None,
            await self.resume_storage.get_resume(user_id),
            response_id,
            self.chat_history.get_history(user_id),
        )

        # Save response history
        self.chat_history.add_message(
            user_id,
            InterviewHistory(
                role="assistant",
                content=gptResponse,
                timestamp=datetime.datetime.now(),
                question_type=QuestionType.FOLLOWUP_QUESTION.value,
                audio=gptResponseAudio,
            ),
        )

    async def ask_for_resume(self, websocket: WebSocket, user_id: str):
        resume = await self.resume_storage.get_resume(user_id)

        async def ask_for_resume():
            await websocket.send_json(
                {
                    "type": EventType.ASK_FOR_RESUME.value,
                }
            )

        if not resume:
            await ask_for_resume()
            while True:
                if websocket.client_state == WebSocketState.DISCONNECTED:
                    break
                message = await websocket.receive()

                if "text" in message:
                    data = json.loads(s=message["text"])
                    event_type = data.get("type")

                    if event_type == EventType.RECEIVE_RESUME.value:
                        resume = await self.resume_storage.get_resume(user_id)
                        if resume:
                            await websocket.send_json(
                                {
                                    "type": EventType.SUCCESS_FULL_RESUME_RECEIVED.value,
                                    "resume": json.loads(resume),
                                }
                            )
                            break
                        else:
                            await ask_for_resume()
                    else:
                        await ask_for_resume()

                else:
                    await ask_for_resume()

        else:
            await websocket.send_json(
                {
                    "type": EventType.SUCCESS_FULL_RESUME_RECEIVED.value,
                    "resume": json.loads(resume),
                }
            )

    async def handle_introduction(self, websocket: WebSocket, user_id: str):

        ## Check history is there

        history = self.chat_history.get_history(user_id)
        if (
            history
            or len(
                list(
                    filter(
                        lambda response: response.question_type
                        == QuestionType.INTRO_QUESTION,
                        history,
                    )
                )
            )
            > 0
        ):
            return

        id = "5dceaaa6-471b-44de-a7f4-9327680b96f2"
        intro_audio = await self.elevenlabs_client.text_to_speech(
            "Hello! Introduce Yourself", id
        )

        await websocket.send_json(
            {
                "type": EventType.ASK_QUESTION.value,
                "text": "Hello! Introduce Yourself",
                "audio": intro_audio,
                "status": "ready",
                "response_id": id,
            }
        )

        history = self.chat_history.add_message(
            user_id,
            InterviewHistory(
                role="assistant",
                content="Hello! Introduce Yourself",
                timestamp=datetime.datetime.now(),
                question_type=QuestionType.INTRO_QUESTION.value,
                audio=intro_audio,
                id=id,
            ),
        )

    async def handle_websocket(self, websocket: WebSocket, user_id: str):
        client_id = user_id
        client = Client(client_id, self.sampling_rate, self.samples_width)
        self.connected_clients[client_id] = client

        logging.info(f"Client {client_id} connected ")

        try:
            await self.ask_for_resume(websocket, user_id)
            # Send existing chat history
            history = self.chat_history.get_history(user_id)
            if history:
                await websocket.send_json(
                    {
                        "type": "chat_history",
                        "history": [asdict(response) for response in history],
                    }
                )

            else:
                await self.handle_introduction2(websocket, user_id)

            while True:
                if websocket.client_state == WebSocketState.DISCONNECTED:
                    break
                message = await websocket.receive()

                if "text" in message:
                    data = json.loads(s=message["text"])
                    event_type = data.get("type")

                    if event_type == EventType.START_ANSWER.value:
                        await self.handle_ask_question(client_id, websocket)
                    elif event_type == EventType.END_ANSWER.value:
                        await self.handle_end_question(client_id, websocket, user_id)

                elif "bytes" in message:
                    # Handle audio packet
                    await self.handle_audio_packet(
                        client_id, websocket, audio_data=message["bytes"]
                    )

        except Exception as e:
            logging.error(
                f"Error in websocket handler: {str(e)}\n{traceback.format_exc()}"
            )
        finally:
            if client_id in self.connected_clients:
                del self.connected_clients[client_id]
            if client_id in self.active_sessions:
                del self.active_sessions[client_id]
            logging.info(f"Client {client_id} disconnected")
