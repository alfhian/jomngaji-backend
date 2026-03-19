from typing import List, Dict
from app.models.evaluation_result import Issue
from difflib import SequenceMatcher
import re

from app.services.tadarus_service import get_score_band, normalize_quran, build_pronunciation_issues

# =========================================================
# CONSTANTS
# =========================================================
IKHFA_LETTERS = set(list("تثجدذزسشصضطظفقك"))


def normalize(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def tajwid_issue(code: str, message: str, location: str = "transcription"):
    return {
        "category": "tajwid",
        "code": code,
        "message": message,
        "location": location,
    }


def analyze_tajwid(arabic_text: str) -> (Dict[str, float], List[Issue], List[str]):
    issues: List[Issue] = []
    suggestions: List[str] = []

    indications = 0
    for i, ch in enumerate(arabic_text):
        if ch == "ن" and i + 1 < len(arabic_text) and arabic_text[i + 1] in IKHFA_LETTERS:
            indications += 1

    score = 0.8 if indications == 0 else max(0.5, 0.8 - indications * 0.05)

    if indications > 0:
        issues.append(Issue(
            category="tajwid",
            code="IKHFA",
            message="Periksa hukum ikhfa pada bacaan nun.",
            location=None,
        ))
        suggestions.append("Perhatikan ikhfa: tipiskan nun sebelum huruf ikhfa, tanpa dengung berlebihan.")

    return {"tajwid": score}, issues, suggestions


def evaluate_tajwid(transcription: str, target_text: str):
    issues = []
    suggestions = []

    if not transcription or not transcription.strip():
        issues.append(tajwid_issue("EMPTY", "Tidak ada suara terdeteksi", "audio"))
        suggestions.append("Pastikan mikrofon aktif dan ulangi bacaan.")
        return {
            "scores": {"final": 0, "tajwid": 0, "band": get_score_band(0)},
            "issues": issues,
            "suggestions": suggestions,
        }

    text_norm = normalize(transcription)
    target_norm = normalize(target_text)

    sim = similarity(text_norm, target_norm)
    score_sim = int(round(sim * 100))

    rule_scores, rule_issues, rule_suggestions = analyze_tajwid(text_norm)
    score_final = int((score_sim / 100 + rule_scores["tajwid"]) / 2 * 100)
    band = get_score_band(score_final)

    expected = normalize_quran(target_text, keep_spaces=False)
    actual = normalize_quran(transcription, keep_spaces=False)
    pronunciation_issues = build_pronunciation_issues(expected, actual, category="tajwid")

    if score_sim >= 80:
        suggestions.append("Pengucapan hukum Nun Mati & Tanwin sudah cukup jelas.")
    elif score_sim >= 50:
        issues.append(tajwid_issue("NEAR_MISS", "Pengucapan hampir benar", "transcription"))
        suggestions.append("Perjelas bacaan hukum Nun/Tanwin.")
    else:
        issues.append(tajwid_issue("MISMATCH", "Tidak sesuai dengan target bacaan", "transcription"))
        suggestions.append("Ulangi bacaan sesuai contoh.")

    issues.append(tajwid_issue("QUALITY_BAND", f"Kategori nilai: {band['label']} ({band['min']}-{band['max']}).", "overall"))
    issues.extend(pronunciation_issues[:10])
    issues.extend([i.dict() if isinstance(i, Issue) else i for i in rule_issues])

    suggestions.extend(rule_suggestions)
    if pronunciation_issues:
        suggestions.append("Latih ulang kata yang salah huruf secara perlahan sebelum membaca satu ayat penuh.")

    return {
        "scores": {
            "final": score_final,
            "tajwid": score_final,
            "band": band,
            "similarity": score_sim,
        },
        "issues": issues,
        "suggestions": suggestions,
    }
