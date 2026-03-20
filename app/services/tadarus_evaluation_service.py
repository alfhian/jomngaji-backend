from app.services.tadarus_audio_service import evaluate_audio_only
from app.repositories.tadarus_evaluation_repo import upsert_evaluation
from app.services.tadarus_progress_service import update_progress_if_valid


def evaluate_and_save_tadarus(
    *,
    user_id: int,
    surah: int,
    ayah: int,
    total_ayah: int,
    ayat_text: str,      # 🔥 dari Quran dataset
    user_audio,
    reference_audio,
) -> dict:

    # =========================
    # 1. EVALUATE AUDIO
    # =========================
    result = evaluate_audio_only(
        user_audio=user_audio,
        reference_audio=reference_audio,
        ayat_text=ayat_text,
    )

    if not result["valid"]:
        return {
            "texts": {
                "user": "",
                "reference": ayat_text,
            },
            "scores": {
                "final": 0,
                "ayat": 0,
                "audio": 0,
            },
            "issues": [{"message": "Tidak ada bacaan valid"}],
            "suggestions": ["Bacalah dengan suara jelas dan durasi cukup"],
            "score_band": None,
            "progress": None,
        }

    # =========================
    # 2. AMBIL DATA DARI RESULT
    # =========================
    scores = result["scores"]
    issues = result.get("issues", [])
    suggestions = result.get("suggestions", [])
    user_text = result["texts"]["user"]
    ref_text = result["texts"]["reference"]

    # =========================
    # 3. SIMPAN / UPDATE EVALUATION
    # =========================
    upsert_evaluation(
        user_id=user_id,
        surah=surah,
        ayah=ayah,
        score_final=scores["final"],
        score_ayat=scores["ayat"],
        score_audio=scores["audio"],
        asr_user=user_text,      # ✅ FIX
        asr_ref=ref_text,
        issues=issues,
        suggestions=suggestions,
    )

    # =========================
    # 4. UPDATE PROGRESS
    # =========================
    progress = update_progress_if_valid(
        user_id=user_id,
        surah=surah,
        total_ayah=total_ayah,
        score=scores["final"],
    ) 

    # =========================
    # 5. RESPONSE KE FRONTEND
    # =========================
    return {
        "texts": {
            "user": user_text,
            "reference": ref_text,
        },
        "scores": scores,
        "issues": issues,
        "suggestions": suggestions,
        "score_band": scores.get("band"),
        "progress": progress,
    }
