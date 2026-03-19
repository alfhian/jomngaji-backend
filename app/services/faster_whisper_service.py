import os
from typing import Optional

from faster_whisper import WhisperModel

FW_MODEL_SIZE = os.getenv("FW_MODEL_SIZE", "small")
FW_DEVICE = os.getenv("FW_DEVICE", "cpu")
FW_COMPUTE_TYPE = os.getenv("FW_COMPUTE_TYPE", "int8")

_model: Optional[WhisperModel] = None


def get_faster_whisper_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(
            FW_MODEL_SIZE,
            device=FW_DEVICE,
            compute_type=FW_COMPUTE_TYPE,
        )
    return _model


def transcribe_arabic(path: str, beam_size: int = 1) -> str:
    model = get_faster_whisper_model()
    segments, _ = model.transcribe(
        path,
        language="ar",
        task="transcribe",
        beam_size=beam_size,
        vad_filter=True,
    )
    return " ".join(segment.text.strip() for segment in segments if segment.text).strip()
