from typing import List, Dict
from app.models.evaluation_result import Issue
from difflib import SequenceMatcher
import re

# =========================================================
# CONSTANTS
# =========================================================

IKHFA_LETTERS = set(list("تثجدذزسشصضطظفقك"))  # huruf ikhfa (Arab)

# =========================================================
# HELPERS
# =========================================================

def normalize(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    return re.sub(r"\s+", " ", text)

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

def tajwid_issue(code: str, message: str, location: str = "transcription"):
    return {
        "category": "tajwid",
        "code": code,
        "message": message,
        "location": location,
    }

# =========================================================
# ANALYZE TAJWID (RULE BASED)
# =========================================================

def analyze_tajwid(arabic_text: str) -> (Dict[str, float], List[Issue], List[str]):
    issues: List[Issue] = []
    suggestions: List[str] = []

    indications = 0

    # Deteksi Nun bertemu huruf ikhfa (tanpa diakritik)
    for i, ch in enumerate(arabic_text):
        if ch == "ن" and i + 1 < len(arabic_text):
            if arabic_text[i + 1] in IKHFA_LETTERS:
                indications += 1

    score = 0.8 if indications == 0 else max(0.5, 0.8 - indications * 0.05)

    if indications > 0:
        issues.append(Issue(
            category="tajwid",
            code="IKHFA",
            message="Periksa hukum ikhfa pada bacaan nun.",
            location=None
        ))
        suggestions.append("Perhatikan ikhfa: tipiskan nun sebelum huruf ikhfa, tanpa dengung berlebihan.")

    return {"tajwid": score}, issues, suggestions

# =========================================================
# CORE EVALUATION
# =========================================================

def evaluate_tajwid(transcription: str, target_text: str):
    issues = []
    suggestions = []

    print("[TAJWID] Raw transcription:", transcription)
    print("[TAJWID] Target text:", target_text)

    if not transcription or not transcription.strip():
        issues.append(tajwid_issue("EMPTY", "Tidak ada suara terdeteksi", "audio"))
        suggestions.append("Pastikan mikrofon aktif dan ulangi bacaan.")
        return {
            "scores": {"final": 0, "tajwid": 0},
            "issues": issues,
            "suggestions": suggestions,
        }

    text_norm = normalize(transcription)
    target_norm = normalize(target_text)

    sim = similarity(text_norm, target_norm)
    score_sim = int(round(sim * 100))

    print(f"[TAJWID] Similarity ratio={sim:.3f} → score_sim={score_sim}")

    if score_sim >= 80:
        suggestions.append("Pengucapan hukum Nun Mati & Tanwin sudah cukup jelas.")
    elif score_sim >= 50:
        issues.append(tajwid_issue("NEAR_MISS", "Pengucapan hampir benar", "transcription"))
        suggestions.append("Perjelas bacaan hukum Nun/Tanwin.")
    else:
        issues.append(tajwid_issue("MISMATCH", "Tidak sesuai dengan target bacaan", "transcription"))
        suggestions.append("Ulangi bacaan sesuai contoh.")

    # Rule-based analisis
    rule_scores, rule_issues, rule_suggestions = analyze_tajwid(text_norm)
    print("[TAJWID] Rule-based score:", rule_scores)
    print("[TAJWID] Rule-based issues:", rule_issues)
    print("[TAJWID] Rule-based suggestions:", rule_suggestions)

    # Gabungkan similarity + rule
    score_final = int((score_sim/100 + rule_scores["tajwid"]) / 2 * 100)
    print(f"[TAJWID] Final score={score_final} (combined similarity+rule)")

    issues.extend([i.dict() if isinstance(i, Issue) else i for i in rule_issues])
    suggestions.extend(rule_suggestions)

    print("[TAJWID] Final issues:", issues)
    print("[TAJWID] Final suggestions:", suggestions)

    return {
        "scores": {
            "final": score_final,   # ✅ tambahkan field final
            "tajwid": score_final
        },
        "issues": issues,
        "suggestions": suggestions
    }


