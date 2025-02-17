from dataclasses import dataclass
import datetime
from typing import AsyncGenerator, Literal, Optional, Dict, Any
import aiofiles
import websockets
import asyncio
import json
import base64
from fastapi import WebSocket
from asyncio import Queue
from .chatgpt_util import ChatGPTClient
from .elevenlabs_util import ElevenLabsClient
from src.types import InterviewHistory
from typing import List
from src.constant import AUDIO_SAVE_PATH
from src.util import save_audio_bytes_to_file_async


class AudioStreamManager:
    def __init__(
        self, elevenlabs_client: ElevenLabsClient, chatgpt_client: ChatGPTClient
    ):
        self.elevenlabs = elevenlabs_client
        self.chatgpt = chatgpt_client

    async def stream_audio(
        self,
        client_ws: WebSocket,
        websocket: websockets.WebSocketClientProtocol,
        response_id: str,
    ) -> AsyncGenerator[bytes, None]:
        """Stream audio directly from ElevenLabs to client."""
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                if data.get("audio"):
                    # Directly send audio to client
                    await client_ws.send_json(
                        {
                            "type": "audio_chunk",
                            "content": data["audio"],
                            "response_id": response_id,
                        }
                    )
                    audio_chunk = base64.b64decode(s=data["audio"])
                    await client_ws.send_bytes(audio_chunk)
                    yield audio_chunk
                elif data.get("isFinal"):
                    await client_ws.send_json({"type": "audio_end"})
                    break
            except websockets.exceptions.ConnectionClosed as e:
                print("ElevenLabs connection closed:", e)
                await client_ws.send_json(
                    {"type": "error", "content": "Audio stream connection closed"}
                )
                break
            
    async def save_conversation(self, query, response):
        # Collect responses
        collected_response = {
            "query": query,
            "system_response": response
        }
        # Write collected responses to a JSON file
        file_path = "query_system_response.json"    
        # Read existing responses or create new
        try:
            async with aiofiles.open(file_path, 'r') as file:
                content = await file.read()
                existing_responses = json.loads(content) if content else []
        except FileNotFoundError:
            existing_responses = []

        # Append new response
        if isinstance(existing_responses, list):
            existing_responses.append(collected_response)
        else:
            existing_responses = [existing_responses, collected_response]

        # Write updated responses
        async with aiofiles.open(file_path, 'w') as file:
            await file.write(json.dumps(existing_responses, indent=4))

        return f"Responses saved to: {file_path}"
        
    async def generate_final_report(self, history):
        print("Generating final report")
        # Read all responses from the JSON file
        file_path = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_query_system_response.json"
        print("got file path")
        json_data = []
        for entry in history:
            json_data.append({
                "role": entry.role,
                "content": entry.content,
                "question_type": entry.question_type,
                "timestamp": entry.timestamp,
                "audio": entry.audio,
                "id": entry.id
            })
        
        evaluator_prompt = self.chatgpt.get_evaluator_prompt(json_data)
        evaluator_response = self.chatgpt.get_evaluator_response(evaluator_prompt)
        
        print("evaluator_response : ", evaluator_response)        
        
        #  Read existing responses or create new
        try:
            async with aiofiles.open(file_path, 'r') as file:
                content = await file.read()
                existing_responses = json.loads(content) if content else []
        except FileNotFoundError:
            existing_responses = []

        print("Chcecking for responses to create new")
        
        # Append new response
        if isinstance(existing_responses, list):
            existing_responses.append(json_data)
        else:
            existing_responses = [existing_responses, json_data]
        
        existing_responses.append(evaluator_response)
        print("Writing updated responses")
        # Write updated responses
        async with aiofiles.open(file_path, 'w') as file:
            await file.write(json.dumps(existing_responses, indent=4))

    async def handle_stream(
        self,
        client_ws: WebSocket,
        query: str,
        resume: str,
        response_id: str = "",
        history: Optional[List[InterviewHistory]] = None,
    ):
        """Handle the complete streaming process."""
        try:
            # Connect to ElevenLabs
            await self.elevenlabs.connect()
            accumulated_text = ""
            chatGptResponse = ""

            # Send initial configuration to ElevenLabs
            chatgpt_res_audio_file_name = f"{response_id}_chatgpt_res.mp3"

            # Start streaming audio in parallel with text processing
            stream_task = asyncio.create_task(
                save_audio_bytes_to_file_async(
                    self.stream_audio(
                        client_ws, self.elevenlabs.websocket, response_id
                    ),
                    chatgpt_res_audio_file_name,
                    AUDIO_SAVE_PATH,
                )
            )

            # Process ChatGPT response and send to ElevenLabs
            async for text_chunk in self.chatgpt.stream_response(
                query, resume, history
            ):
                # Send text to client
                await client_ws.send_json(
                    {
                        "type": "chatgpt_response",
                        "content": text_chunk,
                        "response_id": response_id,
                    }
                )

                chatGptResponse += text_chunk

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

            await self.save_conversation(query, chatGptResponse)

            # Wait for audio streaming to complete
            await stream_task
            if (("Thanks for taking the time to interview with us! We will reach out to you with next steps shortly.") in chatGptResponse or ("INTERVIEW COMPLETED") in chatGptResponse):
                await self.generate_final_report(history)
            return [chatGptResponse, chatgpt_res_audio_file_name]

        except Exception as e:
            print(f"Error in stream handling: {e}")
            await client_ws.send_json({"type": "error", "content": str(e)})
        finally:
            await self.elevenlabs.close()
