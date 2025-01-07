from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Request
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
from configs.ServerWebSocketHandler import WebSocketHandler


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
                "role": "system",
                "content": "You are a helpful assistant. Please assist the user with their query. Please make the response within two lines",
            },
            {
                "role": "user",
                "content": user_query,
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
                        # "chunk_length_schedule": [120, 160, 250, 290],
                        "flush": True,
                    },
                    "xi_api_key": ELEVENLABS_API_KEY,
                }
            )
        )

        # Create queue for audio chunks
        audio_queue = Queue()

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
            yield chunk

        # Wait for both tasks to complete
        await asyncio.gather(listen_task, send_task)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Set up the Jinja2 template renderer
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")


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


class AudioDebugger:
    def __init__(self, debug_folder="debug_audio"):
        """
        Initialize the audio debugger with a specific folder for saving files.

        Args:
            debug_folder (str): The folder where debug audio files will be saved
        """
        self.debug_folder = Path(debug_folder)
        self.create_debug_folder()
        self.session_folder = None
        self.chunk_counter = 0

    def create_debug_folder(self):
        """Create the main debug folder if it doesn't exist."""
        try:
            self.debug_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"Debug folder created/verified at: {self.debug_folder}")
        except Exception as e:
            logger.error(f"Error creating debug folder: {str(e)}")

    def start_new_session(self):
        """
        Start a new debugging session with timestamp-based folder.
        Returns the session folder path.
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_folder = self.debug_folder / timestamp
        self.chunk_counter = 0

        try:
            self.session_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"New debug session started at: {self.session_folder}")
            return self.session_folder
        except Exception as e:
            logger.error(f"Error creating session folder: {str(e)}")
            return None

    def save_audio_chunk(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 44100,
        prefix: str = "chunk",
        format: str = "flac",
    ):
        """
        Save an audio chunk with debugging information.

        Args:
            audio_data (np.ndarray): The audio data to save
            sample_rate (int): The sample rate of the audio
            prefix (str): Prefix for the filename
            format (str): Audio format to save ('flac' or 'wav')

        Returns:
            Path: Path to the saved file
        """
        if self.session_folder is None:
            self.start_new_session()

        self.chunk_counter += 1

        # Create filename with metadata
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        filename = f"{prefix}_{timestamp}_{self.chunk_counter:04d}.{format}"
        filepath = self.session_folder / filename

        try:
            # Save audio file
            if format == "flac":
                sf.write(
                    filepath, audio_data, sample_rate, format="FLAC", subtype="PCM_24"
                )
            else:  # wav
                sf.write(
                    filepath, audio_data, sample_rate, format="WAV", subtype="PCM_24"
                )

            # Save metadata
            meta_filepath = filepath.with_suffix(".meta.txt")
            with open(meta_filepath, "w") as f:
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Sample Rate: {sample_rate}\n")
                f.write(f"Shape: {audio_data.shape}\n")
                f.write(f"Max Amplitude: {np.max(np.abs(audio_data))}\n")
                f.write(f"Mean Amplitude: {np.mean(np.abs(audio_data))}\n")

            logger.info(f"Saved debug audio chunk to: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error saving debug audio chunk: {str(e)}")
            return None

    def save_raw_bytes(
        self,
        audio_bytes: bytes,
        sample_rate: int = 44100,
        channels: int = 1,
        sampwidth: int = 4,
    ):
        """
        Save raw audio bytes for debugging.

        Args:
            audio_bytes (bytes): Raw audio bytes
            sample_rate (int): Sample rate of the audio
            channels (int): Number of audio channels
            sampwidth (int): Sample width in bytes

        Returns:
            Path: Path to the saved file
        """
        if self.session_folder is None:
            self.start_new_session()

        self.chunk_counter += 1

        # Create filename
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        filename = f"raw_{timestamp}_{self.chunk_counter:04d}.wav"
        filepath = self.session_folder / filename

        try:
            with wave.open(str(filepath), "wb") as wav_file:
                wav_file.setnchannels(channels)
                wav_file.setsampwidth(sampwidth)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_bytes)

            logger.info(f"Saved raw audio bytes to: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error saving raw audio bytes: {str(e)}")
            return None


def preprocess_audio(audio_np: np.ndarray, sample_rate: int = 44100) -> np.ndarray:
    """
    Preprocess audio data to improve quality, reduce noise, and enhance clarity.
    """
    try:
        # Normalize audio
        audio_np = audio_np / np.max(np.abs(audio_np))

        # Apply band-pass filter
        low_cutoff = 300 / (sample_rate / 2)
        high_cutoff = 3400 / (sample_rate / 2)
        b, a = signal.butter(4, [low_cutoff, high_cutoff], "bandpass")
        audio_np = signal.filtfilt(b, a, audio_np)

        # Apply noise reduction
        noise_sample = audio_np[:sample_rate]  # Use the first second as noise sample
        audio_np = nr.reduce_noise(y=audio_np, sr=sample_rate, y_noise=noise_sample)

        return audio_np
    except Exception as e:
        logger.error(f"Error preprocessing audio: {str(e)}")
        return audio_np


def save_audio_to_flac(audio_np: np.ndarray, sample_rate: int = 44100) -> str:
    """
    Save audio numpy array to a temporary FLAC file with high quality settings.
    """
    try:
        temp_file = tempfile.NamedTemporaryFile(suffix=".flac", delete=False)
        sf.write(
            temp_file.name,
            audio_np,
            samplerate=sample_rate,
            format="FLAC",
            subtype="PCM_24",  # Use 24-bit FLAC encoding
        )
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


def convert_audio_text_ndarray(filename) -> str:
    try:
        with open(filename, "rb") as f:
            data = f.read()
            response = requests.post(API_URL, headers=headers, data=data)
        return response
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        return ""


def convert_audio_text_groq(filename) -> str:

    try:
        transcription = client.audio.transcriptions.create(
            model="whisper-large-v3", file=filename
        )
        return transcription.text
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        return ""


def transcribe_audio_with_hf(audio_data: np.ndarray) -> str:
    """
    Transcribe audio data using Hugging Face Whisper API.
    """
    try:
        start = time()
        # Preprocess the audio for better quality
        audio_data = preprocess_audio(audio_data)

        flac_file_path = save_audio_to_flac(audio_data)

        # Send the audio to the Hugging Face API
        response = convert_audio_text_groq(flac_file_path)

        if response.status_code == 200:
            result = response.json()
            end = time()
            logger.info(f"Transcribe time: {end-start}")
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


websocketHandler = WebSocketHandler()


@app.websocket("/ws/audio")
async def audio_ws1(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected")
    await websocketHandler.handle_websocket(websocket)


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


# Serve HTML UI for recording and transmitting audio
@app.get("/app")
async def get(request: Request):
    return templates.TemplateResponse("app.html", {"request": request})


# Serve HTML UI for recording and transmitting audio
@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("appv7.html", {"request": request})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
