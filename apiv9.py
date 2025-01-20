from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
    Request,
    HTTPException,
)
from fastapi.staticfiles import StaticFiles
import whisper
from fastapi.responses import StreamingResponse
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
from scipy import signal
import base64
import numpy as np
import logging
import soundfile as sf
import datetime
from pathlib import Path
import wave
from time import time
import noisereduce as nr
from asyncio import Queue
from deepgram import (
    DeepgramClient,
    PrerecordedOptions,
    FileSource,
)
from src.ServerWebSocketHandlerInterview import WebSocketHandler
from src.constant import AUDIO_SAVE_PATH


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


async def listen(websocket, audio_queue: Queue) -> None:
    """Listen to the websocket for audio data and put it in queue."""
    while True:
        try:
            message = await websocket.recv()
            data = json.loads(message)
            if data.get("audio"):
                await audio_queue.put(base64.b64decode(data["audio"]))
            elif data.get("isFinal"):
                await audio_queue.put(None)  # Signal end of stream
                break
        except websockets.exceptions.ConnectionClosed as e:
            print("Connection closed")
            print(e)
            await audio_queue.put(None)  # Signal end of stream
            break


async def chatgpt_send_to_websocket(websocket, user_query: str) -> None:
    """Send text chunks to websocket from ChatGPT response."""
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": """
                    You are a helpful assistant. Please assist the user with their query.
                    Think that you are an voice assistant. 
                    You need to give answer as short as possible.
                    ```{user_query}```
                    """.format(
                    user_query=user_query
                ),
            },
        ],
        model="llama3-8b-8192",
        stream=True,
    )

    try:
        for chunk in chat_completion:
            if chunk.choices[0].delta.content is not None:
                if chunk.choices[0].delta.content != "":
                    await websocket.send(
                        json.dumps({"text": chunk.choices[0].delta.content})
                    )
            else:
                await websocket.send(json.dumps({"text": ""}))
                print("End of text stream")
    except Exception as e:
        print(f"Error sending text: {e}")
        await websocket.send(json.dumps({"text": ""}))


async def generate_audio_stream(user_query: str) -> AsyncGenerator[bytes, None]:
    """Generate audio stream from text with concurrent send/receive."""
    start_time = time()
    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id={model_id}"

    async with websockets.connect(uri) as websocket:
        # Send initial configuration
        await websocket.send(
            json.dumps(
                {
                    "text": " ",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.4,
                        "use_speaker_boost": False,
                    },
                    "generation_config": {
                        # "chunk_length_schedule": [120, 160, 250, 290],
                        "flush": True,
                    },
                    "xi_api_key": ELEVENLABS_API_KEY,
                }
            )
        )

        # Create queue for audio chunks
        audio_queue = Queue()
        first_response_received = False
        # Create concurrent tasks
        listen_task = asyncio.create_task(listen(websocket, audio_queue))
        send_task = asyncio.create_task(
            chatgpt_send_to_websocket(websocket, user_query)
        )

        # Stream audio chunks from queue
        while True:
            chunk = await audio_queue.get()
            if chunk is None:  # End of stream
                break
            if not first_response_received:
                end_time = time()
                latency = end_time - start_time
                print(f"First response latency: {latency:.2f} seconds")
                first_response_received = True
            yield chunk

        # Wait for both tasks to complete
        await asyncio.gather(listen_task, send_task)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Set up the Jinja2 template renderer
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")


deepgram = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))


def convert_audio_text_deepgram(filename):
    with open(filename, "rb") as f:
        data = f.read()
    payload: FileSource = {
        "buffer": data,
    }
    # STEP 2: Configure Deepgram options for audio analysis
    options = PrerecordedOptions(
        model="nova-2",
        smart_format=True,
    )
    start_time = time()
    # STEP 3: Call the transcribe_file method with the text payload and options
    response = deepgram.listen.rest.v("1").transcribe_file(payload, options)
    end_time = time()
    print("time_taken : ", end_time - start_time)
    print(
        response.to_dict()
        .get("results")
        .get("channels")[0]["alternatives"][0]["transcript"]
    )
    # STEP 4: Print the response
    return {
        "text": response.to_dict()
        .get("results")
        .get("channels")[0]["alternatives"][0]["transcript"]
    }


websocketHandler = WebSocketHandler()


@app.websocket("/ws/audio/{user_id}")
async def audio_ws(websocket: WebSocket, user_id: str):
    await websocket.accept()
    logger.info(f"Client connected with user_id: {user_id}")
    await websocketHandler.handle_websocket(websocket, user_id)


CHUNK_SIZE = 32 * 1024  # 32KB chunks
AUDIO_DIR = "."  # Base directory for audio files


async def audio_stream_generator(file_path: str):
    with open(file_path, "rb") as audio_file:
        while chunk := audio_file.read(CHUNK_SIZE):
            yield chunk


@app.get("/audio/{file_path:path}")
async def stream_audio(file_path: str):
    # Convert to Path object for secure path handling
    audio_path = Path(AUDIO_SAVE_PATH) / file_path

    # Ensure the path doesn't escape the base directory
    try:
        audio_path = audio_path.resolve()
        if not str(audio_path).startswith(str(Path(AUDIO_SAVE_PATH).resolve())):
            raise HTTPException(
                status_code=403, detail="Access to this file path is forbidden"
            )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    if not audio_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    # Check if it's an audio file (basic check)
    if not str(audio_path).lower().endswith((".mp3", ".wav", ".ogg", ".m4a")):
        raise HTTPException(
            status_code=400, detail="File is not a supported audio format"
        )

    return StreamingResponse(
        audio_stream_generator(str(audio_path)),
        media_type="audio/mpeg",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Disposition": f"attachment; filename={audio_path.name}",
        },
    )


@app.post("/askchatpt/")
async def transcribe(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(await file.read())
        temp_file_path = temp_file.name
    start = time()
    transcription = convert_audio_text_deepgram(temp_file_path)
    print(transcription["text"])
    end = time()
    logger.info(f"Transcribe time: {end-start}")
    return StreamingResponse(
        generate_audio_stream(transcription["text"]),
        media_type="audio/mpeg",
        headers={"Content-Disposition": "attachment; filename=audio_stream.mp3"},
    )


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


# Serve HTML UI for recording and transmitting audio
@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("appv9_ms.html", {"request": request})


@app.get("/app")
async def get(request: Request):
    return templates.TemplateResponse("appv9.html", {"request": request})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
