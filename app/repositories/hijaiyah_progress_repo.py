import json
from datetime import datetime
from app.services.auth_service import get_db

PASSING_SCORE = 50


# =========================================================
# GLOBAL PROGRESS (HOME CARD)
# =========================================================
def get_hijaiyah_progress(user_id: int):
    return get_hijaiyah_global_progress(user_id)


def get_hijaiyah_global_progress(user_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            COALESCE(SUM(completed_letters), 0) AS completed,
            COALESCE(SUM(total_letters), 0) AS total,
            ROUND(AVG(average_score), 2) AS avg_score
        FROM hijaiyah_progress
        WHERE user_id = %s
        """,
        (user_id,),
    )

    row = cursor.fetchone()
    cursor.close()
    db.close()

    completed = int(row["completed"])
    total = int(row["total"])
    avg = float(row["avg_score"] or 0)

    return {
        "completed_letters": completed,
        "total_letters": total,
        "average_score": avg,
        "percentage": round((completed / total) * 100, 2) if total else 0,
    }

def save_hijaiyah_evaluation(
    user_id: int,
    lesson_id: int,
    hijaiyah: str,
    transcript: str,
    score_final: int,
    score_audio: int | None,
    score_ayat: int | None,
    feedback: str | None,
    issues: dict | None,
):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO hijaiyah_evaluations
            (
                user_id,
                lesson_id,
                hijaiyah,
                transcript,
                score_final,
                score_audio,
                score_ayat,
                feedback,
                issues
            )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            user_id,
            lesson_id,
            hijaiyah,
            transcript,
            score_final,
            score_audio,
            score_ayat,
            feedback,
            json.dumps(issues) if issues else None,
        ),
    )

    print("[EVAL SAVED] row_id:", cursor.lastrowid)

    db.commit()
    cursor.close()
    db.close()


# =========================================================
# INIT PROGRESS (WAJIB ADA)
# =========================================================
def ensure_hijaiyah_progress(user_id: int, lesson_id: int):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO hijaiyah_progress
            (user_id, lesson_id, completed_letters, total_letters, average_score)
        SELECT
            %s, l.id, 0, l.total_letters, 0
        FROM hijaiyah_lessons l
        WHERE l.id = %s
        ON DUPLICATE KEY UPDATE user_id = user_id
        """,
        (user_id, lesson_id),
    )

    db.commit()
    cursor.close()
    db.close()


# =========================================================
# UPDATE PROGRESS (INCREMENTAL)
# =========================================================
PASSING_SCORE = 50

def update_hijaiyah_after_evaluation(
    user_id: int,
    lesson_id: int,
    hijaiyah: str,
    score: int,
):
    if score < PASSING_SCORE:
        return

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # 1️⃣ pastikan progress lesson ada
    cursor.execute(
        """
        INSERT INTO hijaiyah_progress (user_id, lesson_id, completed_letters, total_letters, average_score)
        SELECT %s, l.id, 0, l.total_letters, 0
        FROM hijaiyah_lessons l
        WHERE l.id = %s
        ON DUPLICATE KEY UPDATE user_id = user_id
        """,
        (user_id, lesson_id),
    )

    # 2️⃣ cek apakah huruf sudah pernah lulus
    cursor.execute(
        """
        SELECT passed
        FROM hijaiyah_letter_progress
        WHERE user_id=%s AND lesson_id=%s AND hijaiyah=%s
        """,
        (user_id, lesson_id, hijaiyah),
    )
    row = cursor.fetchone()

    if row and row["passed"] == 1:
        db.commit()
        db.close()
        return

    # 3️⃣ simpan huruf lulus
    cursor.execute(
        """
        INSERT INTO hijaiyah_letter_progress
            (user_id, lesson_id, hijaiyah, passed, score)
        VALUES (%s, %s, %s, 1, %s)
        ON DUPLICATE KEY UPDATE passed=1, score=VALUES(score)
        """,
        (user_id, lesson_id, hijaiyah, score),
    )

    # 4️⃣ hitung ulang completed_letters (SUMBER KEBENARAN)
    cursor.execute(
        """
        SELECT COUNT(*) AS completed
        FROM hijaiyah_letter_progress
        WHERE user_id=%s AND lesson_id=%s AND passed=1
        """,
        (user_id, lesson_id),
    )
    completed = cursor.fetchone()["completed"]

    # 5️⃣ update hijaiyah_progress (completed_letters)
    cursor.execute(
        """
        UPDATE hijaiyah_progress
        SET completed_letters = LEAST(%s, total_letters)
        WHERE user_id=%s AND lesson_id=%s
        """,
        (completed, user_id, lesson_id),
    )

    # ⭐ 5.5️⃣ HITUNG ULANG AVERAGE SCORE
    cursor.execute(
        """
        SELECT ROUND(AVG(score), 2) AS avg_score
        FROM hijaiyah_letter_progress
        WHERE user_id=%s AND lesson_id=%s AND passed=1
        """,
        (user_id, lesson_id),
    )
    avg_score = cursor.fetchone()["avg_score"] or 0

    cursor.execute(
        """
        UPDATE hijaiyah_progress
        SET average_score=%s
        WHERE user_id=%s AND lesson_id=%s
        """,
        (avg_score, user_id, lesson_id),
    )

    # 6️⃣ cek unlock lesson berikutnya (pakai order_index)
    cursor.execute(
        """
        SELECT p.completed_letters, p.total_letters, l.order_index
        FROM hijaiyah_progress p
        JOIN hijaiyah_lessons l ON l.id = p.lesson_id
        WHERE p.user_id=%s AND p.lesson_id=%s
        """,
        (user_id, lesson_id),
    )
    row = cursor.fetchone()

    if row and row["completed_letters"] >= row["total_letters"]:
        cursor.execute(
            """
            INSERT IGNORE INTO hijaiyah_lesson_unlocks (user_id, lesson_id)
            SELECT %s, id
            FROM hijaiyah_lessons
            WHERE order_index > %s
            ORDER BY order_index ASC
            LIMIT 1
            """,
            (user_id, row["order_index"]),
        )


    db.commit()
    db.close()




# =========================================================
# LAST ACTIVITY
# =========================================================
def get_last_hijaiyah_activity(user_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT hijaiyah
        FROM hijaiyah_evaluations
        WHERE user_id = %s
        ORDER BY evaluated_at DESC
        LIMIT 1
        """,
        (user_id,),
    )

    row = cursor.fetchone()
    cursor.close()
    db.close()

    return {
        "last_recited": row["hijaiyah"] if row else None
    }

from app.repositories.hijaiyah_lesson_repo import get_hijaiyah_lessons
