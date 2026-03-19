import re
from difflib import SequenceMatcher

# =========================================================
# NORMALIZATION
# =========================================================
DIACRITICS_PATTERN = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06ED]")
TATWEEL_PATTERN = re.compile(r"[\u0640]")  # tatweel ـ
PRESENTATION_FORMS_PATTERN = re.compile(r"[\uFB50-\uFDFF\uFE70-\uFEFF]")

def normalize_quran(text: str, keep_spaces: bool = True) -> str:
    """
    Normalisasi teks Qur'an untuk evaluasi:
    - Hapus harakat (karena Whisper tidak output harakat)
    - Hapus ligature/presentation forms & tatweel
    - Normalisasi huruf umum (أ/إ/آ/ٱ → ا, ى → ي, ة → ه)
    - Normalisasi spasi
    """
    if not text:
        return ""
    # Hapus ligature & tatweel
    text = PRESENTATION_FORMS_PATTERN.sub("", text)
    text = TATWEEL_PATTERN.sub("", text)
    # Hapus non-Arabic kecuali spasi
    text = re.sub(r"[^\u0600-\u06FF\s]", "", text)
    # Hapus harakat
    text = DIACRITICS_PATTERN.sub("", text)
    # Normalisasi huruf
    text = (text.replace("أ", "ا")
                .replace("إ", "ا")
                .replace("آ", "ا")
                .replace("ٱ", "ا")
                .replace("ى", "ي")
                .replace("ة", "ه"))
    # Normalisasi spasi
    if keep_spaces:
        text = re.sub(r"\s+", " ", text).strip()
    else:
        text = text.replace(" ", "")
    return text

# =========================================================
# SIMILARITY
# =========================================================
def evaluate_similarity(a: str, b: str) -> int:
    ratio = SequenceMatcher(None, a, b).ratio()
    return round(ratio * 100)

# =========================================================
# MAIN: EVALUATE TADARUS
# =========================================================
def evaluate_tadarus(original_text: str, user_text: str) -> tuple:
    """
    Evaluasi bacaan Tadarus:
    - original_text = target ayat (berharakat)
    - user_text = hasil transkripsi Whisper (tanpa harakat)
    Return: (scores, issues, suggestions)
    """

    # Normalisasi dengan & tanpa spasi
    original_sp = normalize_quran(original_text, keep_spaces=True)
    user_sp = normalize_quran(user_text, keep_spaces=True)

    original_ns = normalize_quran(original_text, keep_spaces=False)
    user_ns = normalize_quran(user_text, keep_spaces=False)

    # Ambil skor terbaik
    score_sp = evaluate_similarity(original_sp, user_sp)
    score_ns = evaluate_similarity(original_ns, user_ns)
    score = max(score_sp, score_ns)

    # 👉 Logging untuk debug
    print(f"[DEBUG] original_text(raw): {original_text}")
    print(f"[DEBUG] user_text(raw): {user_text}")
    print(f"[DEBUG] original_sp: {original_sp}")
    print(f"[DEBUG] user_sp: {user_sp}")
    print(f"[DEBUG] original_ns: {original_ns}")
    print(f"[DEBUG] user_ns: {user_ns}")
    print(f"[DEBUG] score_sp: {score_sp}, score_ns: {score_ns}, final_score: {score}")

    # Feedback & issues
    if score > 90:
        feedback = "Bacaan sangat baik 👍"
        issues = []
    elif score > 75:
        feedback = "Cukup baik, beberapa bagian perlu diperhatikan"
        issues = [{
            "category": "kemiripan",
            "code": "partial_match",
            "location": "ayat",
            "message": "Sebagian kata tidak sepenuhnya cocok setelah normalisasi"
        }]
    else:
        feedback = "Perlu latihan lagi, coba ulangi dengan lebih teliti"
        issues = [{
            "category": "kemiripan",
            "code": "low_match",
            "location": "ayat",
            "message": "Kemiripan bacaan rendah setelah normalisasi harakat dan spasi"
        }]

    scores = {"tadarus": score}
    suggestions = [feedback]  # harus string langsung

    return scores, issues, suggestions
