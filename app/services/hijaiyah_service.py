from difflib import SequenceMatcher
import re

# =========================================================
# CONSTANTS
# =========================================================

# Huruf vokal panjang
VOWELS = {"ا", "أ", "إ", "آ", "و", "ي"}

# Harakat Arab
ARABIC_DIACRITICS = r"[ًٌٍَُِّْ]"

# =========================================================
# HELPERS
# =========================================================

def normalize(text: str) -> str:
    """
    Normalisasi khusus Arabic:
    - strip spasi
    - hapus harakat
    - hapus spasi dalam string
    """
    if not text:
        return ""

    text = text.strip()
    text = re.sub(ARABIC_DIACRITICS, "", text)
    text = re.sub(r"\s+", "", text)

    return text


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def hijaiyah_issue(code: str, message: str, location: str = "transcription"):
    """
    Semua issue hijaiyah HARUS lewat sini
    supaya Pydantic tidak error
    """
    return {
        "category": "hijaiyah",
        "code": code,
        "message": message,
        "location": location,
    }


# =========================================================
# CORE EVALUATION
# =========================================================

def evaluate_hijaiyah(
    transcription: str,
    target_letter: str,
):
    """
    Evaluate bacaan satu huruf hijaiyah.

    Return:
    {
        "scores": {
            "hijaiyah": int (0-100)
        },
        "issues": list[dict],
        "suggestions": list[str]
    }
    """

    issues = []
    suggestions = []

    # =====================================================
    # 1️⃣ VALIDASI INPUT
    # =====================================================

    if not transcription or not transcription.strip():
        issues.append(
            hijaiyah_issue(
                code="EMPTY_AUDIO",
                message="Tidak ada suara terdeteksi",
                location="audio",
            )
        )
        suggestions.append("Pastikan mikrofon aktif dan ulangi bacaan.")

        return {
            "scores": {"hijaiyah": 0},
            "issues": issues,
            "suggestions": suggestions,
        }

    if not target_letter or not target_letter.strip():
        # Ini error sistem, bukan user
        return {
            "scores": {"hijaiyah": 0},
            "issues": [
                hijaiyah_issue(
                    code="SYSTEM_ERROR",
                    message="Target huruf tidak tersedia",
                    location="system",
                )
            ],
            "suggestions": [],
        }

    # =====================================================
    # 2️⃣ NORMALISASI
    # =====================================================

    text_norm = normalize(transcription)
    target_norm = normalize(target_letter)

    # fallback kalau ASR menghasilkan simbol aneh
    if not text_norm:
        text_norm = transcription.strip()

    if not target_norm:
        target_norm = target_letter.strip()

    # helper konversi score
    def score_pct(value: float) -> int:
        return int(round(value * 100))

    # =====================================================
    # 3️⃣ MATCH EXACT
    # =====================================================

    if text_norm == target_norm:
        return {
            "scores": {"hijaiyah": 100},
            "issues": [],
            "suggestions": ["Pengucapan sudah tepat."],
        }

    # =====================================================
    # 4️⃣ BENAR TAPI ADA TAMBAHAN (contoh: بَ → با)
    # =====================================================

    if target_norm and text_norm.startswith(target_norm):
        tail = text_norm[len(target_norm):]

        if tail:
            issues.append(
                hijaiyah_issue(
                    code="EXTRA_LETTER",
                    message="Huruf benar tetapi ada tambahan suara di akhir",
                )
            )
            suggestions.append("Huruf sudah benar, hindari tambahan suara.")

            return {
                "scores": {"hijaiyah": 85},
                "issues": issues,
                "suggestions": suggestions,
            }

    # =====================================================
    # 5️⃣ MIRIP (NEAR MISS)
    # =====================================================

    sim = similarity(text_norm, target_norm)

    # Untuk satu huruf, threshold harus lebih ketat
    if len(target_norm) == 1:
        if sim >= 0.75:
            issues.append(
                hijaiyah_issue(
                    code="NEAR_MISS",
                    message="Pengucapan hampir benar",
                )
            )
            suggestions.append("Perjelas makhraj huruf.")

            return {
                "scores": {"hijaiyah": score_pct(sim)},
                "issues": issues,
                "suggestions": suggestions,
            }
    else:
        if sim >= 0.6:
            issues.append(
                hijaiyah_issue(
                    code="NEAR_MISS",
                    message="Pengucapan hampir benar",
                )
            )
            suggestions.append("Perjelas pengucapan huruf.")

            return {
                "scores": {"hijaiyah": score_pct(sim)},
                "issues": issues,
                "suggestions": suggestions,
            }

    # =====================================================
    # 6️⃣ SALAH TOTAL
    # =====================================================

    issues.append(
        hijaiyah_issue(
            code="MISMATCH",
            message="Tidak sesuai dengan huruf target",
        )
    )
    suggestions.append("Dengarkan contoh lalu ulangi kembali.")

    return {
        "scores": {"hijaiyah": 40},
        "issues": issues,
        "suggestions": suggestions,
    }