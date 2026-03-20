from typing import List, Dict
from app.models.evaluation_result import Issue
from difflib import SequenceMatcher
import re

from app.services.tadarus_service import get_score_band, normalize_quran, build_pronunciation_issues


def normalize(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    return re.sub(r"\s+", " ", text)


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def tahfidz_issue(code: str, message: str, location: str = "transcription"):
    return {
        "category": "tahfidz",
        "code": code,
        "message": message,
        "location": location,
    }


def evaluate_tahfidz(transcription: str, target_text: str = "") -> Dict:
    issues: List[Issue] = []
    suggestions: List[str] = []

    if not transcription or not transcription.strip():
        issues.append(tahfidz_issue("EMPTY", "Tidak ada suara terdeteksi", "audio"))
        suggestions.append("Pastikan mikrofon aktif dan ulangi hafalan.")
        return {
            "scores": {"final": 0, "tahfidz": 0, "band": get_score_band(0)},
            "issues": issues,
            "suggestions": suggestions,
        }

    text_norm = normalize(transcription)
    target_norm = normalize(target_text)
    sim = similarity(text_norm, target_norm)
    score_sim = int(round(sim * 100))
    band = get_score_band(score_sim)

    expected = normalize_quran(target_text, keep_spaces=False)
    actual = normalize_quran(transcription, keep_spaces=False)
    pronunciation_issues = build_pronunciation_issues(expected, actual, category="tahfidz")

    if score_sim >= 90:
        suggestions.append("Hafalan sudah sangat baik dan sesuai.")
    elif score_sim >= 70:
        issues.append(tahfidz_issue("NEAR_MISS", "Hafalan hampir benar", "transcription"))
        suggestions.append("Perbaiki detail hafalan sesuai teks ayat.")
    else:
        issues.append(tahfidz_issue("MISMATCH", "Hafalan tidak sesuai dengan target ayat", "transcription"))
        suggestions.append("Ulangi hafalan dengan lebih teliti.")

    if "اللَّهُ" in text_norm:
        suggestions.append("Ayat tentang sifat Allah terdeteksi.")
    if len(text_norm.split()) < len(target_norm.split()):
        issues.append(tahfidz_issue("INCOMPLETE", "Hafalan belum lengkap", "transcription"))
        suggestions.append("Pastikan menghafal seluruh ayat tanpa terputus.")

    issues.append(tahfidz_issue("QUALITY_BAND", f"Kategori nilai: {band['label']} ({band['min']}-{band['max']}).", "overall"))
    issues.extend(pronunciation_issues[:10])

    return {
        "scores": {
            "final": score_sim,
            "tahfidz": score_sim,
            "band": band,
        },
        "issues": issues,
        "suggestions": suggestions,
    }
