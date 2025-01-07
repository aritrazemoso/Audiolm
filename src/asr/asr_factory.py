from .local_whisper_asr import WhisperASR
from .groq_asr import GroqASR
from .asr_faster_whisper import FasterWhisperASR
from .asr_faster_whisper_docker import FasterWhisperDocker
from .asr_hugging_face import HuggingFaceAsr


class ASRFactory:
    @staticmethod
    def create_asr_pipeline(asr_type, **kwargs):
        if asr_type == "whisper":
            return WhisperASR(**kwargs)
        if asr_type == "faster_whisper":
            return FasterWhisperASR(**kwargs)
        if asr_type == "faster_whisper_docker":
            return FasterWhisperDocker(**kwargs)
        if asr_type == "hugging_face":
            return HuggingFaceAsr(**kwargs)
        if asr_type == "groq":
            return GroqASR(**kwargs)
        else:
            raise ValueError(f"Unknown ASR pipeline type: {asr_type}")
