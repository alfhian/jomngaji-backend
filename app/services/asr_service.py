import re

from app.services.faster_whisper_service import transcribe_arabic


def clean_transcript(text: str) -> str:
    text = re.sub(r"[^\u0600-\u06FF\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(.)\1{2,}", r"\1", text)
    return text.strip()


def transcribe_audio(file_path: str) -> str:
    try:
        print(f"[INFO] Transkripsi file (faster-whisper): {file_path}")
        text = transcribe_arabic(file_path, beam_size=1)
        text = clean_transcript(text)
        print(f"[INFO] Hasil transkripsi (bersih): {text}")
        return text
    except Exception as e:
        print(f"[ERROR] Gagal transkripsi: {e}")
        raise
