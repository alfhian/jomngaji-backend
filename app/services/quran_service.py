import json
import os
from typing import Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SURAH_META_JSON = os.path.join(DATA_DIR, "surah_meta.json")
SURAH_JSON_DIR = os.path.join(DATA_DIR, "quran-complete")

# =========================
# INTERNAL STORAGE
# =========================
_surah_meta: Dict[int, dict] = {}
_loaded = False

# =========================
# LOAD METADATA
# =========================
def _load_meta():
    global _loaded
    if _loaded:
        return

    with open(SURAH_META_JSON, encoding="utf-8") as f:
        raw = json.load(f)
        for k, v in raw.items():
            _surah_meta[int(k)] = v

    _loaded = True

# =========================
# PUBLIC API
# =========================
def get_all_surahs() -> List[dict]:
    _load_meta()

    result = []
    for num in range(1, 115):
        meta = _surah_meta.get(num)
        if not meta:
            continue

        result.append({
            "number": num,
            "arabic": meta["arabic"],
            "latin": meta["latin"],
            "ayah_count": meta["ayah_count"],
            "revelation": meta["revelation"],
        })

    return result

def get_surah(surah_number: int) -> Optional[dict]:
    _load_meta()

    meta = _surah_meta.get(surah_number)
    if not meta:
        return None

    file_path = os.path.join(SURAH_JSON_DIR, f"Alquran_{surah_number}.json")
    if not os.path.exists(file_path):
        return None

    with open(file_path, encoding="utf-8") as f:
        raw = json.load(f)

    ayahs = []
    for i, ayah in enumerate(raw.get("ayahs", []), start=1):
        ayahs.append({
            "surah": surah_number,
            "ayah": i,
            "text": ayah.get("arb"),
            "transliteration": ayah.get("transliterasi"),
            "translation": ayah.get("ind"),
            "tafsir": {
                "kemenag": ayah.get("kemenag_ringkas"),
                "jalalain": ayah.get("jalalain"),
                "quraish": ayah.get("quraish_shihab"),
                "ibnu_katsir": ayah.get("ibnu_katsir"),
                "saadi": ayah.get("saadi"),
            }
        })

    return {
        "number": surah_number,
        "arabic": raw.get("ar", meta["arabic"]),
        "latin": raw.get("name", meta["latin"]),
        "english": raw.get("en"),
        "indonesian": raw.get("id"),
        "revelation": raw.get("revelationType", meta["revelation"]),
        "ayah_count": raw.get("numberOfAyahs", meta["ayah_count"]),
        "ayahs": ayahs,
    }

def get_ayah(surah_number: int, ayah_number: int) -> Optional[dict]:
    surah = get_surah(surah_number)
    if not surah:
        return None

    for ayah in surah["ayahs"]:
        if ayah["ayah"] == ayah_number:
            return ayah

    return None

def search_surah_by_name(query: str) -> List[dict]:
    _load_meta()
    query = query.strip().lower()
    return [
        meta for meta in _surah_meta.values()
        if query in meta["latin"].lower() or query in meta["arabic"]
    ]

def get_surah_range(surah_number: int, start: int, end: int) -> List[dict]:
    surah = get_surah(surah_number)
    if not surah:
        return []

    return [
        ayah for ayah in surah["ayahs"]
        if start <= ayah["ayah"] <= end
    ]
