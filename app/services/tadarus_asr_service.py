import os
import re
import torch
from typing import Optional
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from pydub import AudioSegment

# =========================================================
# CONFIG
# =========================================================
# Pilih model:
# - "openai/whisper-tiny" → cepat, cukup untuk baseline
# - "Seyfelislem/whisper-medium-arabic" → lebih akurat untuk Arab (tanpa harakat)
WHISPER_MODEL_NAME = os.getenv("TADARUS_WHISPER_MODEL", "openai/whisper-tiny")

# Device
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Bahasa & task
LANGUAGE = "ar"  # Arabic
TASK = "transcribe"  # jangan "translate" agar tetap Arab

# =========================================================
# GLOBAL SINGLETONS (cache model & processor)
# =========================================================
_processor: Optional[WhisperProcessor] = None
_model: Optional[WhisperForConditionalGeneration] = None

# =========================================================
# NORMALIZATION HELPERS
# =========================================================
# Harakat (diacritics) — kita TIDAK hapus di sini, karena kamu ingin target tetap berharakat.
DIACRITICS_PATTERN = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
TATWEEL_PATTERN = re.compile(r"[\u0640]")  # tatweel ـ
PRESENTATION_FORMS_PATTERN = re.compile(r"[\uFB50-\uFDFF\uFE70-\uFEFF]")  # ligatures

def clean_transcript(text: str) -> str:
    """
    Bersihkan hasil transkripsi dari ligature/presentation forms & tatweel,
    tapi TIDAK menghapus harakat (biar konsisten dengan pilihan kamu).
    """
    if not text:
        return ""
    # Hapus presentation forms & tatweel (kadang muncul dari font/renderer)
    text = PRESENTATION_FORMS_PATTERN.sub("", text)
    text = TATWEEL_PATTERN.sub("", text)
    # Hapus karakter non-Arabic kecuali spasi
    text = re.sub(r"[^\u0600-\u06FF\s]", "", text)
    # Normalisasi spasi
    text = re.sub(r"\s+", " ", text).strip()
    return text

# =========================================================
# AUDIO HELPERS
# =========================================================
def load_audio_mono_16k(path: str) -> torch.Tensor:
    """
    Load audio file, konversi ke mono 16k PCM untuk Whisper.
    Return: torch.Tensor float32 [samples]
    """
    audio = AudioSegment.from_file(path)
    audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)  # 16-bit PCM
    samples = audio.get_array_of_samples()
    # Convert ke float32 range [-1, 1]
    import numpy as np
    np_samples = np.array(samples).astype(np.float32) / 32768.0
    return torch.from_numpy(np_samples)

# =========================================================
# MODEL LOADER
# =========================================================
def _ensure_model_loaded():
    global _processor, _model
    if _processor is None or _model is None:
        _processor = WhisperProcessor.from_pretrained(WHISPER_MODEL_NAME)
        _model = WhisperForConditionalGeneration.from_pretrained(WHISPER_MODEL_NAME)
        _model.to(DEVICE)
        _model.eval()

# =========================================================
# MAIN: TRANSCRIBE TADARUS
# =========================================================
def transcribe_tadarus(path: str) -> str:
    _ensure_model_loaded()

    print("\n========== [TADARUS ASR] ==========")
    print(f"[AUDIO PATH] {path}")

    # 1) Load audio
    audio_tensor = load_audio_mono_16k(path)
    duration = len(audio_tensor) / 16000
    print(f"[AUDIO] duration = {duration:.2f}s")

    # 2) Preprocess
    inputs = _processor(
        audio_tensor,
        sampling_rate=16000,
        return_tensors="pt",
    )

    input_features = inputs.input_features.to(DEVICE)

    forced_decoder_ids = _processor.get_decoder_prompt_ids(
        language=LANGUAGE,
        task=TASK
    )

    # 3) Generate
    with torch.no_grad():
        generated_ids = _model.generate(
            input_features,
            forced_decoder_ids=forced_decoder_ids,
            num_beams=1,
            do_sample=False,
            max_length=448,
        )

    # 4) Decode
    raw_text = _processor.batch_decode(
        generated_ids,
        skip_special_tokens=True
    )[0]

    clean_text = clean_transcript(raw_text)

    # 5) LOG DETAIL
    print("---------- [ASR RESULT] ----------")
    print(f"[RAW ] {raw_text}")
    print(f"[CLEAN] {clean_text}")
    print("=================================\n")

    return clean_text

