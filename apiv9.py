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
from typing import AsyncGenerator, Optional
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

from src.ServerWebSocketHandlerInterview import WebSocketHandler
from src.constant import AUDIO_SAVE_PATH, USER_DATA_PATH
from src.utility.PdfUtility import PDFProcessor


load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Set up the Jinja2 template renderer
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")


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

    # Define supported audio formats and their corresponding media types
    AUDIO_TYPES = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
    }

    # Get file extension and check if supported
    file_extension = audio_path.suffix.lower()
    if file_extension not in AUDIO_TYPES:
        raise HTTPException(
            status_code=400, detail="File is not a supported audio format"
        )

    return StreamingResponse(
        audio_stream_generator(str(audio_path)),
        media_type=AUDIO_TYPES[file_extension],
        headers={
            "Accept-Ranges": "bytes",
            "Content-Disposition": f"attachment; filename={audio_path.name}",
        },
    )


pdf_processor = PDFProcessor()


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), user_id: Optional[str] = None):
    """
    Upload and process a PDF file
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    try:
        # Extract text from PDF
        extracted_text = await pdf_processor.extract_text_from_pdf(file)

        # Extract information from text
        extracted_info = pdf_processor.extract_contact_info(extracted_text)

        # Add original text for reference
        extracted_info["original_text"] = extracted_text

        # Save to user file
        pdf_processor.save_json(user_id, extracted_info)

        return {
            "status": "success",
            "message": "File processed successfully",
            "extracted_info": extracted_info,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Optional: Add an endpoint to retrieve processed data
@app.get("/user_data/{user_id}")
async def get_user_data(user_id: str):
    """
    Retrieve processed data for a user
    """
    file_path = os.path.join(pdf_processor.output_dir, f"{user_id}.json")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="User data not found")

    with open(file_path, "r") as f:
        data = json.load(f)
    return data


# Serve HTML UI for recording and transmitting audio
@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("appv9_ms.html", {"request": request})


@app.get("/app")
async def get(request: Request):
    return templates.TemplateResponse("appv9_with_resume.html", {"request": request})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
