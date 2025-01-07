import torch
import numpy as np
from .vad_interface import VADInterface
from src.WebsocketClient import Client
from src.util import save_audio_to_file


class SileroVAD(VADInterface):
    def __init__(self, **kwargs):
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=False,
        )
        self.model = model
        self.get_speech_timestamps = utils[0]
        self.sampling_rate = kwargs.get("sampling_rate", 16000)

    async def detect_activity(self, client: Client):
        # Load and normalize audio
        audio = np.frombuffer(client.scratch_buffer, dtype=np.int16).astype(np.float32)
        audio = audio / 32768.0
        audio_tensor = torch.from_numpy(audio)

        # Get timestamps using utility function
        speech_timestamps = self.get_speech_timestamps(
            audio_tensor, self.model, sampling_rate=self.sampling_rate
        )

        # Convert to segments format
        vad_segments = [
            {
                "start": ts["start"] / self.sampling_rate,
                "end": ts["end"] / self.sampling_rate,
                "confidence": 1.0,
            }
            for ts in speech_timestamps
        ]

        return vad_segments
