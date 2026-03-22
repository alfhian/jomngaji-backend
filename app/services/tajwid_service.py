from typing import List, Dict
from difflib import SequenceMatcher
import re

from app.services.tadarus_service import get_score_band, normalize_quran, build_pronunciation_issues

# =========================================================
# CONSTANTS
# =========================================================
IKHFA_LETTERS = set(list("تثجدذزسشصضطظفقك"))
HEAVY_LETTERS = set(list("خصضغطقظ"))


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


def analyze_tajwid(arabic_text: str) -> tuple[Dict[str, float], List[dict], List[str]]:
    issues: List[dict] = []
    suggestions: List[str] = []

    indications = 0
    for i, ch in enumerate(arabic_text):
        if ch == "ن" and i + 1 < len(arabic_text) and arabic_text[i + 1] in IKHFA_LETTERS:
            indications += 1

    heavy_count = sum(1 for ch in arabic_text if ch in HEAVY_LETTERS)
    score = 0.95 if indications == 0 else max(0.65, 0.95 - indications * 0.06)

    if indications > 0:
        issues.append(
            tajwid_issue(
                "IKHFA_PRACTICE",
                f"Terdapat {indications} bagian nun/tanwin yang perlu diperjelas hukum ikhfa-nya.",
                "transcription",
            )
        )
        suggestions.append("Perhatikan ikhfa: tipiskan nun sebelum huruf ikhfa, tanpa dengung berlebihan.")

    if heavy_count > 0:
        suggestions.append("Jaga ketebalan huruf isti'la (خ ص ض غ ط ق ظ) agar tidak berubah jadi huruf tipis.")

    return {"tajwid": score}, issues, suggestions


def _count_issue_codes(issues: List[dict]) -> dict:
    counts = {"letter_replace": 0, "letter_missing": 0, "letter_extra": 0}
    for issue in issues:
        code = issue.get("code")
        if code in counts:
            counts[code] += 1
    return counts


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

    expected = normalize_quran(target_text, keep_spaces=False)
    actual = normalize_quran(transcription, keep_spaces=False)
    pronunciation_issues = build_pronunciation_issues(expected, actual, category="tajwid", max_issues=20)
    issue_counts = _count_issue_codes(pronunciation_issues)

    length_ref = max(len(expected), 1)
    weighted_errors = (
        issue_counts["letter_replace"] * 1.0
        + issue_counts["letter_missing"] * 1.2
        + issue_counts["letter_extra"] * 0.8
    )
    detail_penalty = min(45, int(round((weighted_errors / length_ref) * 120)))
    score_rule = int(round(rule_scores["tajwid"] * 100))
    score_final = max(0, min(100, int(round(score_sim * 0.75 + score_rule * 0.25 - detail_penalty))))
    band = get_score_band(score_final)

    if score_sim >= 90 and detail_penalty <= 5:
        suggestions.append("Bacaan sangat baik; kelancaran, ketepatan huruf, dan konsistensi tajwid sudah bagus.")
    elif score_sim >= 80:
        suggestions.append("Bacaan cukup baik, lanjutkan latihan untuk merapikan bagian yang masih tertukar.")
    elif score_sim >= 60:
        issues.append(tajwid_issue("NEAR_MISS", "Pengucapan hampir benar", "transcription"))
        suggestions.append("Fokuskan latihan pada potongan kata yang masih tertukar huruf.")
    else:
        issues.append(tajwid_issue("MISMATCH", "Tidak sesuai dengan target bacaan", "transcription"))
        suggestions.append("Ulangi bacaan sesuai contoh.")

    issues.append(
        tajwid_issue(
            "ERROR_BREAKDOWN",
            (
                f"Rincian kesalahan: penggantian huruf {issue_counts['letter_replace']}, "
                f"huruf hilang {issue_counts['letter_missing']}, "
                f"huruf tambahan {issue_counts['letter_extra']}."
            ),
            "overall",
        )
    )
    issues.append(tajwid_issue("QUALITY_BAND", f"Kategori nilai: {band['label']} ({band['min']}-{band['max']}).", "overall"))
    issues.extend(pronunciation_issues[:10])
    issues.extend(rule_issues)

    suggestions.extend(rule_suggestions)
    if issue_counts["letter_replace"] > 0:
        suggestions.append("Perbaiki makhraj huruf yang sering tertukar dengan membaca kata per kata secara lambat.")
    if issue_counts["letter_missing"] > 0:
        suggestions.append("Jaga tempo bacaan agar tidak ada huruf yang terlewat.")
    if issue_counts["letter_extra"] > 0:
        suggestions.append("Kurangi tambahan bunyi spontan, ikuti teks target secara ketat.")
    if pronunciation_issues:
        suggestions.append("Latih ulang kata yang salah huruf secara perlahan sebelum membaca satu ayat penuh.")

    return {
        "scores": {
            "final": score_final,
            "tajwid": score_final,
            "band": band,
            "similarity": score_sim,
            "rule_score": score_rule,
            "detail_penalty": detail_penalty,
            "error_counts": issue_counts,
        },
        "issues": issues,
        "suggestions": suggestions,
    }
