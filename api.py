from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Request
import whisper
import torch
import io
from fastapi.responses import HTMLResponse, StreamingResponse
from pydub import AudioSegment
from io import BytesIO
import base64
from fastapi.templating import Jinja2Templates
import tempfile
import os
import asyncio
from openai import OpenAI
from dotenv import load_dotenv
from typing import AsyncGenerator
import websockets
import json
from scipy.io import wavfile
import base64
import numpy as np
import logging
import soundfile as sf

import requests

API_URL = "https://api-inference.huggingface.co/models/openai/whisper-large-v3-turbo"
headers = {"Authorization": "Bearer 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"}


def convert_audio_text(filename):
    with open(filename, "rb") as f:
        data = f.read()
        response = requests.post(API_URL, headers=headers, data=data)
        return response.json()


load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

voice_id = "pNInz6obpgDQGcFmaJgB"
model_id = "eleven_turbo_v2_5"

client = OpenAI(
    api_key=os.environ["GROQ_API_KEY"],  # This is the default and can be omitted
    base_url="https://api.groq.com/openai/v1",
)


async def listen(websocket) -> AsyncGenerator[bytes, None]:
    """Listen to the websocket for audio data and stream it."""
    while True:
        try:
            message = await websocket.recv()
            data = json.loads(message)
            if data.get("audio"):
                yield base64.b64decode(data["audio"])
            elif data.get("isFinal"):
                break
        except websockets.exceptions.ConnectionClosed as e:
            print("Connection closed")
            print(e)
            break


async def chatgpt_send_to_websocket(websocket, user_query: str):
    """Send text chunks to websocket from ChatGPT response."""
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": user_query,
            }
        ],
        model="llama3-8b-8192",
        stream=True,
    )

    for chunk in chat_completion:
        if chunk.choices[0].delta.content is not None:
            if chunk.choices[0].delta.content != "":
                await websocket.send(
                    json.dumps({"text": chunk.choices[0].delta.content})
                )
                print("Sending chunk ", {"text": chunk.choices[0].delta.content})
        else:
            await websocket.send(json.dumps({"text": ""}))
            print("End of audio stream")
    return "Complete"


async def generate_audio_stream(user_query: str) -> AsyncGenerator[bytes, None]:
    """Generate audio stream from text."""
    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id={model_id}"

    async with websockets.connect(uri) as websocket:
        # Send initial configuration
        await websocket.send(
            json.dumps(
                {
                    "text": " ",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.8,
                        "use_speaker_boost": False,
                    },
                    "generation_config": {
                        "chunk_length_schedule": [120, 160, 250, 290]
                    },
                    "xi_api_key": ELEVENLABS_API_KEY,
                }
            )
        )

        # Create task for sending text
        send_task = asyncio.create_task(
            chatgpt_send_to_websocket(websocket, user_query)
        )

        # Stream audio chunks
        async for chunk in listen(websocket):
            yield chunk

        await send_task


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Set up the Jinja2 template renderer
templates = Jinja2Templates(directory="templates")


def load_whisper_model(model_type: str = "base"):
    """
    Load and return the Whisper model.
    Args:
        model_type (str): The type of Whisper model to load ("tiny", "base", "small", "medium", "large")
    """
    return whisper.load_model(model_type)


async def listen_numpy(websocket: WebSocket) -> AsyncGenerator[np.ndarray, None]:
    """
    Listen to the websocket for audio data and stream it.
    Yields processed numpy arrays from the audio data.
    """
    while True:
        try:
            message = await websocket.receive_text()
            data = json.loads(message)

            if data.get("audio"):
                # Decode base64 audio data
                audio_bytes = base64.b64decode(data["audio"])
                # Convert bytes to numpy array
                audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
                # Convert to float32 and normalize
                audio_float = audio_data.astype(np.float32) / 32768.0
                yield audio_float
            elif data.get("isFinal"):
                logger.info("Received final message")
                break
        except Exception as e:
            logger.error(f"Error in listen: {str(e)}")
            break


def save_audio_to_flac(audio_np: np.ndarray, sample_rate: int = 16000) -> str:
    """
    Save audio numpy array to a temporary FLAC file.
    """
    try:
        temp_file = tempfile.NamedTemporaryFile(suffix=".flac", delete=False)
        sf.write(temp_file.name, audio_np, samplerate=sample_rate, format="FLAC")
        temp_file.close()
        return temp_file.name
    except Exception as e:
        logger.error(f"Error saving audio to FLAC: {str(e)}")
        raise


async def listen_raw(websocket: WebSocket) -> AsyncGenerator[bytes, None]:
    """
    Listen to the websocket for raw audio data.
    Yields raw audio bytes directly.
    """
    while True:
        try:
            message = await websocket.receive_text()
            data = json.loads(message)

            if data.get("audio"):
                # Decode base64 audio data and yield raw bytes
                audio_bytes = base64.b64decode(data["audio"])
                yield audio_bytes
            elif data.get("isFinal"):
                logger.info("Received final message")
                break
        except Exception as e:
            logger.error(f"Error in listen_raw: {str(e)}")
            break


def transcribe_audio(model: whisper.Whisper, audio_data: np.ndarray) -> str:
    """
    Transcribe audio data using Whisper model.
    """
    try:
        result = model.transcribe(audio_data)
        # result = convert_audio_text(audio_data)
        return result["text"].strip()
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        return ""


def convert_audio_text_ndarray(filename) -> str:
    try:
        with open(filename, "rb") as f:
            data = f.read()
            response = requests.post(API_URL, headers=headers, data=data)
        return response
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        return ""


def transcribe_audio_with_hf(audio_data) -> str:
    """
    Transcribe audio data using Hugging Face Whisper API.
    """
    try:
        flac_file_path = save_audio_to_flac(audio_data)

        # Send the audio to the Hugging Face API
        response = convert_audio_text_ndarray(flac_file_path)

        if response.status_code == 200:
            result = response.json()
            return result.get("text", "").strip()
        else:
            logger.error(f"HF API error: {response.status_code} - {response.text}")
            return ""
    except Exception as e:
        logger.error(f"HF transcription error: {str(e)}")
        return ""


def remove_overlap(prev, new):
    """Removes the common overlap (if any) between the end of the previous transcription
    and the beginning of the new transcription."""
    if prev and new:
        # Find the longest common suffix of prev and the prefix of new
        overlap_length = 0
        for i in range(min(len(prev), len(new))):
            if prev[-(i + 1) :] == new[: (i + 1)]:
                overlap_length = i + 1
            else:
                break
        return new[overlap_length:]
    return new


@app.websocket("/ws/audio")
async def audio_ws1(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected")

    # Initialize audio buffer
    audio_buffer = b""  # Raw audio buffer as bytes
    prevTranscription = None

    try:
        async for chunk_data in listen_raw(websocket):
            try:
                if chunk_data:
                    # Append raw bytes to buffer
                    audio_buffer += chunk_data

                    # Process when we have enough samples (1 second at 16kHz, 16-bit mono = 32000 bytes)
                    if len(audio_buffer) >= 32000:
                        # Convert raw bytes to numpy array
                        audio_np = (
                            np.frombuffer(audio_buffer, dtype=np.int16).astype(
                                np.float32
                            )
                            / 32768.0
                        )

                        # Avoid transcription if there's no significant audio data
                        if (
                            np.abs(audio_np).mean() > 0.001
                        ):  # Mean amplitude threshold for valid audio

                            transcription = transcribe_audio_with_hf(audio_np)
                            # if prevTranscription:
                            #     transcription = remove_overlap(
                            #         prevTranscription, transcription
                            #     )
                            # prevTranscription = transcription
                            await websocket.send_text(transcription)
                            logger.info(f"Transcribed: {transcription}")

                        # Keep a small overlap for continuity (retain last 8000 bytes, 0.25 seconds)
                        audio_buffer = audio_buffer[-4000:]
                        # audio_buffer = b""

            except Exception as e:
                logger.error(f"Error processing chunk: {str(e)}")
                continue

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        await websocket.close()


@app.websocket("/ws/audio/1")
async def audio_ws2(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected")

    # Load Whisper model
    model = load_whisper_model(model_type="base")
    audio_buffer = np.array([], dtype=np.float32)

    try:
        async for chunk_data in listen_numpy(websocket):
            try:
                # Append chunk to buffer
                audio_buffer = np.concatenate([audio_buffer, chunk_data])

                # Process when we have enough samples (1 second at 16kHz)
                if len(audio_buffer) >= 16000:
                    # Get transcription
                    transcription = transcribe_audio_with_hf(audio_buffer)

                    if transcription:
                        await websocket.send_text(transcription)
                        logger.info(f"Transcribed: {transcription}")

                    # Keep a small overlap for continuity
                    audio_buffer = audio_buffer[-4000:]  # Keep last 0.25 seconds

            except Exception as e:
                logger.error(f"Error processing chunk: {str(e)}")
                continue

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        await websocket.close()


@app.post("/transcribe/")
async def transcribe(file: UploadFile = File(...)):
    # model = load_whisper_model(model_type="turbo")  # Load the Whisper model
    # print(file)
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(await file.read())
        temp_file_path = temp_file.name
    transcription = convert_audio_text(temp_file_path)
    print(transcription)
    return {"transcription": transcription["text"]}


@app.get("/stream-audio/")
async def stream_audio(query: str):
    """
    Stream audio endpoint.
    Query parameter: query (str) - The text query to convert to speech
    """
    return StreamingResponse(
        generate_audio_stream(query),
        media_type="audio/mpeg",
        headers={"Content-Disposition": "attachment; filename=audio_stream.mp3"},
    )


@app.get("/stream-combined/")
async def stream_combined(query: str):
    """
    Stream both text and audio using Server-Sent Events.
    This allows real-time streaming of both content types.
    """

    async def event_generator():
        # Start audio generation
        uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id={model_id}"

        async with websockets.connect(uri) as websocket:
            # Send initial configuration to ElevenLabs
            await websocket.send(
                json.dumps(
                    {
                        "text": " ",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.8,
                            "use_speaker_boost": False,
                        },
                        "generation_config": {
                            "chunk_length_schedule": [120, 160, 250, 290]
                        },
                        "xi_api_key": ELEVENLABS_API_KEY,
                    }
                )
            )

            # Create chat completion stream
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": query}],
                model="llama3-8b-8192",
                stream=True,
            )

            for chunk in chat_completion:
                if chunk.choices[0].delta.content:
                    # Send text chunk
                    text_data = chunk.choices[0].delta.content
                    print(text_data)
                    yield f"event: text\ndata: {json.dumps({'text': text_data})}\n\n"

                    # Send to ElevenLabs
                    await websocket.send(json.dumps({"text": text_data}))

                    # Get audio chunk if available
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    if data.get("audio"):
                        audio_chunk = base64.b64decode(data["audio"])
                        # Send audio chunk encoded in base64
                        yield f"event: audio\ndata: {json.dumps({'audio': base64.b64encode(audio_chunk).decode()})}\n\n"
                    elif data.get("isFinal"):
                        break
                except websockets.exceptions.ConnectionClosed as e:
                    break
            # Send completion event
            yield f"event: complete\ndata: {json.dumps({'status': 'complete'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Serve HTML UI for recording and transmitting audio
@app.get("/app")
async def get(request: Request):
    return templates.TemplateResponse("app.html", {"request": request})


@app.get("/newapp")
async def get(request: Request):
    return templates.TemplateResponse("newapp.html", {"request": request})


# Serve HTML UI for recording and transmitting audio
@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
