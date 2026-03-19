from app.services.auth_service import get_db
import json

# =========================================================
# SAVE EVALUATION
# =========================================================
def save_tahfidz_evaluation(
    user_id: int,
    lesson_id: int,
    transcript: str,
    score_final: int,
    feedback: str | None,
    issues: list | None,
):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO tahfidz_evaluations
            (user_id, lesson_id, transcript, score_final, feedback, issues, evaluated_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
        """,
        (user_id, lesson_id, transcript, score_final, feedback, json.dumps(issues, ensure_ascii=False)),
    )

    db.commit()
    cursor.close()
    db.close()


# =========================================================
# GET LAST EVALUATION
# =========================================================
def get_last_tahfidz_evaluation(user_id: int, lesson_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT * FROM tahfidz_evaluations
        WHERE user_id = %s AND lesson_id = %s
        ORDER BY evaluated_at DESC
        LIMIT 1
        """,
        (user_id, lesson_id),
    )

    row = cursor.fetchone()
    cursor.close()
    db.close()
    return row


# =========================================================
# GET PROGRESS
# =========================================================
def get_tahfidz_progress(user_id: int, quiz_code: str, pass_threshold: int = 50):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # ambil attempt terakhir (untuk detail)
    cursor.execute(
        """
        SELECT te.score_final
        FROM tahfidz_evaluations te
        JOIN quizzes q ON q.id = te.lesson_id
        WHERE te.user_id = %s AND q.quiz_code = %s
        ORDER BY te.evaluated_at DESC
        LIMIT 1
        """,
        (user_id, quiz_code),
    )
    last_row = cursor.fetchone()
    cursor.close()
    db.close()

    # ambil skor tertinggi
    best_row = get_best_tahfidz_score(user_id, quiz_code)

    if not last_row and not best_row:
        return {"progress": 0.0, "passed": False, "last_score": 0, "best_score": 0}

    best_score = best_row["best_score"] if best_row and best_row["best_score"] is not None else 0
    passed = best_score >= pass_threshold
    progress = 0.5 if passed else 0.0

    return {
        "progress": progress,          # ✅ progress dihitung dari skor tertinggi
        "passed": passed,
        "last_score": last_row["score_final"] if last_row else 0,
        "best_score": best_score,      # ✅ skor tertinggi
    }


# =========================================================
# GET BEST SCORE
# =========================================================
def get_best_tahfidz_score(user_id: int, quiz_code: str):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT MAX(te.score_final) AS best_score
        FROM tahfidz_evaluations te
        JOIN quizzes q ON q.id = te.lesson_id
        WHERE te.user_id = %s AND q.quiz_code = %s
        """,
        (user_id, quiz_code),
    )
    row = cursor.fetchone()
    cursor.close()
    db.close()
    return row


def get_average_tahfidz_score(user_id: int) -> float:
    """
    Hitung rata-rata skor tahfidz untuk user tertentu langsung dari DB.
    Selalu mengembalikan float agar aman dipakai di perhitungan.
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT AVG(score_final) AS avg_score
        FROM tahfidz_evaluations
        WHERE user_id = %s
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    db.close()

    return float(row["avg_score"]) if row and row["avg_score"] is not None else 0.0


