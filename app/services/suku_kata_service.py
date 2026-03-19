from app.repositories.suku_kata_repo import (
    fetch_suku_kata_levels,
    fetch_suku_kata_questions,
    fetch_level_meta,
    upsert_suku_kata_progress,
    fetch_next_level_id,
    unlock_suku_kata_level,
)

PASS_SCORE = 70


# =========================
# EXISTING — TIDAK DIUBAH
# =========================

def get_suku_kata_levels(user_id: int):
    rows = fetch_suku_kata_levels(user_id)

    total_questions = sum(r["total_questions"] for r in rows)
    completed_questions = sum(r["completed_questions"] for r in rows)

    progress_percentage = (
        completed_questions / total_questions
        if total_questions > 0
        else 0
    )

    return {
        "progress_percentage": round(progress_percentage, 2),
        "levels": [
            {
                "level_id": r["level_id"],
                "title": r["title"],
                "description": r["description"],
                "order_index": r["order_index"] - 1,
                "unlocked": bool(r["unlocked"]),
                "completed_questions": int(r["completed_questions"]),
                "total_questions": int(r["total_questions"]),
                "average_score": float(r["average_score"]),
                "is_premium": int(r["is_premium"]),
            }
            for r in rows
        ],
    }


def get_suku_kata_questions(level_id: int, user_id: int):
    rows = fetch_suku_kata_questions(level_id, user_id)

    if rows is None:
        raise Exception("Level tidak ditemukan")

    return [
        {
            "id": r["id"],
            "latin": r["latin"],
            "arabic": r["arabic"],
        }
        for r in rows
    ]


# =========================
# REFACTORED — SUBMIT SCORE
# =========================

def submit_suku_kata_score(user_id: int, level_id: int, score: float):
    level = fetch_level_meta(level_id)
    if not level:
        raise Exception("Level tidak ditemukan")

    total_questions, order_index = level

    # simpan progress
    upsert_suku_kata_progress(
        user_id=user_id,
        level_id=level_id,
        completed_questions=total_questions,
        score=score,
    )

    # unlock next level jika lulus
    if score >= PASS_SCORE:
        next_level_id = fetch_next_level_id(order_index)
        if next_level_id:
            unlock_suku_kata_level(user_id, next_level_id)

    # ⚠️ return HARUS MATCH
    return {
        "success": True,
        "score": score,
    }
