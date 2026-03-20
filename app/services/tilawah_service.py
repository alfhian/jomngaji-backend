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


def tilawah_issue(code: str, message: str, location: str = "transcription"):
    return {
        "category": "tilawah",
        "code": code,
        "message": message,
        "location": location,
    }


def evaluate_tilawah(transcription: str, target_text: str = "") -> Dict:
    issues: List[Issue] = []
    suggestions: List[str] = []

    if not transcription or not transcription.strip():
        issues.append(tilawah_issue("EMPTY", "Tidak ada suara terdeteksi", "audio"))
        suggestions.append("Pastikan mikrofon aktif dan ulangi bacaan Tilawah.")
        return {
            "scores": {"final": 0, "tilawah": 0, "band": get_score_band(0)},
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
    pronunciation_issues = build_pronunciation_issues(expected, actual, category="tilawah")

    if score_sim >= 85:
        suggestions.append("Bacaan Tilawah sudah cukup jelas dan sesuai.")
    elif score_sim >= 60:
        issues.append(tilawah_issue("NEAR_MISS", "Pengucapan hampir benar", "transcription"))
        suggestions.append("Perjelas bacaan Tilawah sesuai contoh (Tartil/Hadr/Basmalah).")
    else:
        issues.append(tilawah_issue("MISMATCH", "Tidak sesuai dengan target bacaan Tilawah", "transcription"))
        suggestions.append("Ulangi bacaan sesuai contoh Tilawah.")

    if "بِاسْمِ" in text_norm:
        suggestions.append("Tilawah dengan Basmalah terdeteksi.")
    elif "وَرَتِّلِ" in text_norm:
        suggestions.append("Tilawah Tartil terdeteksi.")
    elif len(text_norm.split()) > 8:
        suggestions.append("Bacaan cepat (Hadr) terdeteksi, pastikan tetap sesuai tajwid.")

    issues.append(tilawah_issue("QUALITY_BAND", f"Kategori nilai: {band['label']} ({band['min']}-{band['max']}).", "overall"))
    issues.extend(pronunciation_issues[:10])

    return {
        "scores": {
            "final": score_sim,
            "tilawah": score_sim,
            "band": band,
        },
        "issues": issues,
        "suggestions": suggestions,
    }
