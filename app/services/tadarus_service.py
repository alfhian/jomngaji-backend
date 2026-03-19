import re
from collections import Counter
from difflib import SequenceMatcher

# =========================================================
# NORMALIZATION
# =========================================================
DIACRITICS_PATTERN = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06ED]")
TATWEEL_PATTERN = re.compile(r"[\u0640]")  # tatweel ـ
PRESENTATION_FORMS_PATTERN = re.compile(r"[\uFB50-\uFDFF\uFE70-\uFEFF]")

SCORE_BANDS = [
    {"min": 96, "max": 100, "code": "mumtaz", "label": "Mumtaz"},
    {"min": 90, "max": 95, "code": "excellent", "label": "Sangat Baik"},
    {"min": 83, "max": 89, "code": "very_good", "label": "Baik Sekali"},
    {"min": 75, "max": 82, "code": "good", "label": "Baik"},
    {"min": 65, "max": 74, "code": "fair", "label": "Cukup"},
    {"min": 50, "max": 64, "code": "needs_improvement", "label": "Perlu Peningkatan"},
    {"min": 35, "max": 49, "code": "basic", "label": "Dasar"},
    {"min": 0, "max": 34, "code": "beginner", "label": "Pemula"},
]


def normalize_quran(text: str, keep_spaces: bool = True) -> str:
    if not text:
        return ""

    text = PRESENTATION_FORMS_PATTERN.sub("", text)
    text = TATWEEL_PATTERN.sub("", text)
    text = re.sub(r"[^\u0600-\u06FF\s]", "", text)
    text = DIACRITICS_PATTERN.sub("", text)
    text = (
        text.replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ٱ", "ا")
        .replace("ى", "ي")
        .replace("ة", "ه")
    )

    if keep_spaces:
        return re.sub(r"\s+", " ", text).strip()

    return text.replace(" ", "")


def evaluate_similarity(a: str, b: str) -> int:
    return round(SequenceMatcher(None, a, b).ratio() * 100)


def get_score_band(score: int) -> dict:
    for band in SCORE_BANDS:
        if band["min"] <= score <= band["max"]:
            return band
    return SCORE_BANDS[-1]


def build_pronunciation_issues(expected_text: str, actual_text: str, max_issues: int = 20, category: str = "pronunciation") -> list[dict]:
    matcher = SequenceMatcher(None, expected_text, actual_text)
    issues: list[dict] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        expected_chunk = expected_text[i1:i2]
        actual_chunk = actual_text[j1:j2]

        if tag == "replace":
            issue_code = "letter_replace"
            message = (
                f"Huruf berbeda pada posisi {i1 + 1}-{i2}: "
                f"seharusnya '{expected_chunk}' tapi terbaca '{actual_chunk}'."
            )
        elif tag == "delete":
            issue_code = "letter_missing"
            message = (
                f"Ada huruf yang hilang di posisi {i1 + 1}-{i2}: "
                f"'{expected_chunk}' belum terbaca."
            )
        else:
            issue_code = "letter_extra"
            message = (
                f"Ada huruf tambahan di sekitar posisi {i1 + 1}: "
                f"terdengar '{actual_chunk}' padahal tidak ada pada ayat target."
            )

        issues.append(
            {
                "category": category,
                "code": issue_code,
                "location": "huruf",
                "start_index": i1,
                "end_index": i2,
                "expected": expected_chunk,
                "actual": actual_chunk,
                "message": message,
            }
        )

        if len(issues) >= max_issues:
            break

    return issues


def _build_suggestions(issues: list[dict], score: int) -> list[str]:
    if not issues and score >= 90:
        return ["Bacaan sangat baik, pertahankan kestabilan makhraj dan tempo."]

    counter = Counter(issue["code"] for issue in issues)
    suggestions: list[str] = []

    if counter["letter_replace"]:
        suggestions.append(
            "Fokus pada makhraj huruf yang sering tertukar; baca pelan per kata lalu naikkan tempo secara bertahap."
        )
    if counter["letter_missing"]:
        suggestions.append(
            "Ada huruf yang terlewat; hentikan sebentar di akhir setiap kata untuk memastikan semua huruf terbaca."
        )
    if counter["letter_extra"]:
        suggestions.append(
            "Kurangi penambahan bunyi spontan; ikuti teks ayat secara ketat saat latihan."
        )

    if score < 65:
        suggestions.append("Ulangi ayat per potongan 3-5 kata sambil meniru qari referensi.")

    return suggestions or ["Lanjutkan latihan rutin agar konsistensi bacaan meningkat."]


# =========================================================
# MAIN: EVALUATE TADARUS
# =========================================================
def evaluate_tadarus(original_text: str, user_text: str) -> tuple:
    original_sp = normalize_quran(original_text, keep_spaces=True)
    user_sp = normalize_quran(user_text, keep_spaces=True)

    original_ns = normalize_quran(original_text, keep_spaces=False)
    user_ns = normalize_quran(user_text, keep_spaces=False)

    score_sp = evaluate_similarity(original_sp, user_sp)
    score_ns = evaluate_similarity(original_ns, user_ns)
    score = max(score_sp, score_ns)

    print(f"[DEBUG] score_sp: {score_sp}, score_ns: {score_ns}, final_score: {score}")

    pronunciation_issues = build_pronunciation_issues(original_ns, user_ns, category="pronunciation")
    band = get_score_band(score)

    issues = [
        {
            "category": "quality_band",
            "code": band["code"],
            "location": "overall",
            "message": f"Kategori nilai: {band['label']} ({band['min']}-{band['max']}).",
        },
        *pronunciation_issues,
    ]

    scores = {
        "tadarus": score,
        "band": band,
        "score_with_spaces": score_sp,
        "score_without_spaces": score_ns,
    }
    suggestions = _build_suggestions(pronunciation_issues, score)

    return scores, issues, suggestions
