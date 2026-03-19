import torch
import torchaudio
import numpy as np
from fastapi import UploadFile
from difflib import SequenceMatcher
from transformers import Wav2Vec2Processor, Wav2Vec2Model

from app.utils.audio_utils import save_upload, ensure_wav
from app.services.tadarus_asr_service import transcribe_tadarus
from app.services.tadarus_service import evaluate_tadarus, get_score_band

# =========================================================
SAMPLE_RATE = 16000
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

AYAT_WEIGHT = 0.8
AUDIO_WEIGHT = 0.2

# =========================================================
PROCESSOR = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base-960h")
MODEL = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base-960h").to(DEVICE)
MODEL.eval()

# =========================================================
def load_audio_16k(path: str) -> np.ndarray:
    wav, sr = torchaudio.load(path)

    if wav.numel() == 0:
        return np.array([])

    if wav.shape[0] > 1:
        wav = wav.mean(dim=0, keepdim=True)

    if sr != SAMPLE_RATE:
        wav = torchaudio.functional.resample(wav, sr, SAMPLE_RATE)

    return wav.squeeze().numpy()

def is_valid_audio(audio: np.ndarray, min_duration=1.2, min_rms=0.01) -> bool:
    if audio is None or len(audio) == 0:
        return False

    duration = len(audio) / SAMPLE_RATE
    if duration < min_duration:
        return False

    rms = np.sqrt(np.mean(audio ** 2))
    return rms >= min_rms

# =========================================================
def wav2vec_embedding(path: str) -> np.ndarray:
    audio = load_audio_16k(path)
    if len(audio) == 0:
        return np.zeros(768)

    inputs = PROCESSOR(
        audio,
        sampling_rate=SAMPLE_RATE,
        return_tensors="pt"
    ).input_values.to(DEVICE)

    with torch.no_grad():
        outputs = MODEL(inputs)
        emb = outputs.last_hidden_state.mean(dim=1)

    return emb.squeeze().cpu().numpy()

def audio_similarity(ref_path: str, user_path: str) -> float:
    ref = wav2vec_embedding(ref_path)
    usr = wav2vec_embedding(user_path)

    denom = np.linalg.norm(ref) * np.linalg.norm(usr)
    return float(np.dot(ref, usr) / denom) if denom != 0 else 0.0

# =========================================================
def normalize_arabic(text: str) -> str:
    harakat = "ًٌٍَُِّْـ"
    for h in harakat:
        text = text.replace(h, "")
    return text.replace(" ", "").strip()

def ayat_similarity(ref: str, user: str) -> float:
    r = normalize_arabic(ref)
    u = normalize_arabic(user)
    if not r or not u:
        return 0.0
    return SequenceMatcher(None, r, u).ratio()

# =========================================================
def evaluate_audio_only(
    *,
    user_audio: UploadFile,
    reference_audio: UploadFile,
    ayat_text: str,
) -> dict:

    print("\n========== [TADARUS EVALUATION] ==========")

    user_path = ensure_wav(save_upload(user_audio))
    ref_path = ensure_wav(save_upload(reference_audio))

    audio_data = load_audio_16k(user_path)
    if not is_valid_audio(audio_data):
        print("[INVALID AUDIO]")
        return {"valid": False, "reason": "invalid_audio"}

    # =========================
    # ASR
    # =========================
    user_text = transcribe_tadarus(user_path)

    print("---------- [TEXT MATCHING] ----------")
    print(f"[AYAT TEXT] {ayat_text}")
    print(f"[USER TEXT] {user_text}")

    ayat_score = ayat_similarity(ayat_text, user_text) * 100
    audio_score = audio_similarity(ref_path, user_path) * 100

    # Detail kesalahan pengucapan huruf dari evaluator tadarus
    text_scores, text_issues, text_suggestions = evaluate_tadarus(ayat_text, user_text)

    print(f"[AYAT SCORE ] {ayat_score:.2f}")
    print(f"[AUDIO SCORE] {audio_score:.2f}")

    final_score = round(
        ayat_score * AYAT_WEIGHT +
        audio_score * AUDIO_WEIGHT
    )

    final_score = max(0, min(100, final_score))

    print("---------- [FINAL SCORE] ----------")
    print(f"[FINAL] {final_score}")
    print("===================================\n")

    return {
        "valid": True,
        "texts": {
            "user": user_text,
            "reference": ayat_text,
        },
        "scores": {
            "final": final_score,
            "ayat": int(ayat_score),
            "audio": int(audio_score),
            "band": get_score_band(final_score),
            "ayat_band": text_scores.get("band", get_score_band(int(ayat_score))),
            "audio_band": get_score_band(int(audio_score)),
        },
        "issues": text_issues,
        "suggestions": text_suggestions,
    }

