from app.services.faster_whisper_service import transcribe_arabic


def transcribe_audio(audio_path: str) -> str:
    return transcribe_arabic(audio_path, beam_size=1)
