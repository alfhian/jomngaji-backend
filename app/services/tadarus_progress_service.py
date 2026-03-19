from app.repositories.tadarus_progress_repo import update_progress
from app.repositories.tadarus_progress_repo import get_progress_by_surah
from app.repositories.tadarus_evaluation_repo import get_evaluated_ayahs


MIN_SCORE_TO_PROGRESS = 1  # score 0 tetap disimpan, tapi tidak naik


def get_tadarus_progress(user_id: int, surah: int) -> dict:
    progress = get_progress_by_surah(user_id, surah)
    evaluated = get_evaluated_ayahs(user_id, surah)

    if not progress:
        return {
            "surah": surah,
            "completed_ayah": 0,
            "total_ayah": 0,
            "progress": 0.0,
            "last_ayah": None,
            "evaluated_ayahs": [],
        }

    return {
        "surah": surah,
        "completed_ayah": progress["completed_ayah"],
        "total_ayah": progress["total_ayah"],
        "last_ayah": progress["last_ayah"],
        "progress": (
            progress["completed_ayah"] / progress["total_ayah"]
            if progress["total_ayah"] > 0
            else 0.0
        ),
        "evaluated_ayahs": evaluated,
    }


def update_progress_if_valid(
    *,
    user_id: int,
    surah: int,
    total_ayah: int,
    score: int,
):
    if score < MIN_SCORE_TO_PROGRESS:
        return update_progress(
            user_id=user_id,
            surah=surah,
            total_ayah=total_ayah,
        )

    return update_progress(
        user_id=user_id,
        surah=surah,
        total_ayah=total_ayah,
    )
