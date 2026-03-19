import re
import torch
from transformers import pipeline

_asr_pipeline = None

def clean_transcript(text: str) -> str:
    # Ambil hanya huruf Arab
    text = re.sub(r"[^\u0600-\u06FF]", "", text)
    # Hilangkan pengulangan huruf lebih dari 2 kali
    text = re.sub(r"(.)\1{2,}", r"\1", text)
    return text.strip()

def _load_pipeline():
    from transformers import pipeline
    import torch
    global _asr_pipeline
    if _asr_pipeline is None:
        print("[INFO] Load openai/whisper-tiny...")
        _asr_pipeline = pipeline(
            "automatic-speech-recognition",
            model="openai/whisper-tiny",
            device=0 if torch.cuda.is_available() else "cpu",
            generate_kwargs={"task": "transcribe", "language": "ar"}
        )

    return _asr_pipeline

def transcribe_audio(file_path: str) -> str:
    try:
        print(f"[INFO] Transkripsi file: {file_path}")
        asr = _load_pipeline()
        result = asr(file_path)
        text = result.get("text", "").strip()

        # 🔧 Normalisasi hasil transkripsi
        text = clean_transcript(text)

        print(f"[INFO] Hasil transkripsi (bersih): {text}")
        return text
    except Exception as e:
        print(f"[ERROR] Gagal transkripsi: {e}")
        raise
