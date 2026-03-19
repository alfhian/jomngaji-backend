from difflib import SequenceMatcher
import re

from app.services.tadarus_service import get_score_band, normalize_quran, build_pronunciation_issues

VOWELS = {"ا", "أ", "إ", "آ", "و", "ي"}
ARABIC_DIACRITICS = r"[ًٌٍَُِّْ]"


def normalize(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    text = re.sub(ARABIC_DIACRITICS, "", text)
    text = re.sub(r"\s+", "", text)
    return text


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def hijaiyah_issue(code: str, message: str, location: str = "transcription"):
    return {
        "category": "hijaiyah",
        "code": code,
        "message": message,
        "location": location,
    }


def evaluate_hijaiyah(transcription: str, target_letter: str):
    issues = []
    suggestions = []

    if not transcription or not transcription.strip():
        issues.append(hijaiyah_issue("EMPTY_AUDIO", "Tidak ada suara terdeteksi", "audio"))
        suggestions.append("Pastikan mikrofon aktif dan ulangi bacaan.")
        return {
            "scores": {"hijaiyah": 0, "band": get_score_band(0)},
            "issues": issues,
            "suggestions": suggestions,
        }

    if not target_letter or not target_letter.strip():
        return {
            "scores": {"hijaiyah": 0, "band": get_score_band(0)},
            "issues": [hijaiyah_issue("SYSTEM_ERROR", "Target huruf tidak tersedia", "system")],
            "suggestions": [],
        }

    text_norm = normalize(transcription)
    target_norm = normalize(target_letter)

    if not text_norm:
        text_norm = transcription.strip()
    if not target_norm:
        target_norm = target_letter.strip()

    if text_norm == target_norm:
        return {
            "scores": {"hijaiyah": 100, "band": get_score_band(100)},
            "issues": [],
            "suggestions": ["Pengucapan sudah tepat."],
        }

    sim = similarity(text_norm, target_norm)
    score = int(round(sim * 100))
    band = get_score_band(score)

    expected = normalize_quran(target_letter, keep_spaces=False)
    actual = normalize_quran(transcription, keep_spaces=False)
    pronunciation_issues = build_pronunciation_issues(expected, actual, max_issues=5, category="hijaiyah")

    if target_norm and text_norm.startswith(target_norm) and len(text_norm) > len(target_norm):
        issues.append(hijaiyah_issue("EXTRA_LETTER", "Huruf benar tetapi ada tambahan suara di akhir"))
        suggestions.append("Huruf sudah benar, hindari tambahan suara.")
        score = min(score, 85)
        band = get_score_band(score)
    elif sim >= 0.75 if len(target_norm) == 1 else sim >= 0.6:
        issues.append(hijaiyah_issue("NEAR_MISS", "Pengucapan hampir benar"))
        suggestions.append("Perjelas makhraj huruf dan ulangi perlahan.")
    else:
        issues.append(hijaiyah_issue("MISMATCH", "Tidak sesuai dengan huruf target"))
        suggestions.append("Dengarkan contoh lalu ulangi kembali.")

    issues.append(hijaiyah_issue("QUALITY_BAND", f"Kategori nilai: {band['label']} ({band['min']}-{band['max']}).", "overall"))
    issues.extend(pronunciation_issues)

    return {
        "scores": {"hijaiyah": score, "band": band},
        "issues": issues,
        "suggestions": suggestions,
    }
