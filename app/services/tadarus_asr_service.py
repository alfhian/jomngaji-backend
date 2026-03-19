import re

from app.services.faster_whisper_service import transcribe_arabic

DIACRITICS_PATTERN = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
TATWEEL_PATTERN = re.compile(r"[\u0640]")
PRESENTATION_FORMS_PATTERN = re.compile(r"[\uFB50-\uFDFF\uFE70-\uFEFF]")


def clean_transcript(text: str) -> str:
    if not text:
        return ""
    text = PRESENTATION_FORMS_PATTERN.sub("", text)
    text = TATWEEL_PATTERN.sub("", text)
    text = re.sub(r"[^\u0600-\u06FF\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def transcribe_tadarus(path: str) -> str:
    print("\n========== [TADARUS ASR - FASTER WHISPER] ==========")
    print(f"[AUDIO PATH] {path}")

    raw_text = transcribe_arabic(path, beam_size=1)
    clean_text = clean_transcript(raw_text)

    print("---------- [ASR RESULT] ----------")
    print(f"[RAW ] {raw_text}")
    print(f"[CLEAN] {clean_text}")
    print("=================================\n")

    return clean_text
