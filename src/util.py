import os
import wave
from typing import Iterator


async def save_audio_to_file(
    audio_data, file_name, audio_dir="audio_files", audio_format="wav"
):
    """
    Saves the audio data to a file.

    :param audio_data: The audio data to save.
    :param file_name: The name of the file.
    :param audio_dir: Directory where audio files will be saved.
    :param audio_format: Format of the audio file.
    :return: Path to the saved audio file.
    """

    os.makedirs(audio_dir, exist_ok=True)

    file_path = os.path.join(audio_dir, file_name)

    with wave.open(file_path, "wb") as wav_file:
        wav_file.setnchannels(1)  # Assuming mono audio
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(audio_data)

    return file_path


async def save_audio_bytes_to_file(
    audio_bytes: Iterator[bytes], file_name, audio_dir="audio_files"
):
    """
    Save the audio bytes to a file.

    :param audio_bytes: The audio bytes to save.
    :param file_name: The name of the file.
    :param audio_dir: Directory where audio files will be saved.
    :return: Path to the saved audio file.
    """

    os.makedirs(audio_dir, exist_ok=True)

    file_path = os.path.join(audio_dir, file_name)

    with open(file_path, "wb") as audio_file:
        for chunk in audio_bytes:
            audio_file.write(chunk)

    return file_path


async def save_audio_bytes_to_file_async(
    audio_bytes: Iterator[bytes], file_name, audio_dir="audio_files"
):
    """
    Save the audio bytes to a file.

    :param audio_bytes: The audio bytes to save.
    :param file_name: The name of the file.
    :param audio_dir: Directory where audio files will be saved.
    :return: Path to the saved audio file.
    """

    os.makedirs(audio_dir, exist_ok=True)

    file_path = os.path.join(audio_dir, file_name)

    with open(file_path, "wb") as audio_file:
        async for chunk in audio_bytes:
            audio_file.write(chunk)

    return file_path


async def check_file_exists(file_name, dir):
    file_path = os.path.join(dir, file_name)
    return os.path.exists(file_path)
