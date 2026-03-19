from app.services.auth_service import get_db
from fastapi import HTTPException
from app.services.premium_service import is_user_premium


def get_hijaiyah_lessons(user_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            l.id AS lesson_id,
            l.title,
            l.description,
            l.total_letters,
            l.order_index,
            l.is_premium,

            CASE
                WHEN l.order_index = 1 THEN 1
                WHEN l.is_premium = 1 AND u2.is_premium = 0 THEN 0
                WHEN u.lesson_id IS NOT NULL THEN 1
                ELSE 0
            END AS unlocked,

            COALESCE(p.completed_letters, 0) AS completed_letters,
            COALESCE(p.average_score, 0) AS average_score
        FROM hijaiyah_lessons l
        LEFT JOIN users u2
            ON u2.id = %s
        LEFT JOIN hijaiyah_lesson_unlocks u
            ON u.lesson_id = l.id AND u.user_id = %s
        LEFT JOIN hijaiyah_progress p
            ON p.lesson_id = l.id AND p.user_id = %s
        ORDER BY l.order_index;
        """,
        (user_id, user_id, user_id),
    )

    rows = cursor.fetchall()
    cursor.close()
    db.close()

    print([int(r["is_premium"]) for r in rows])  # Debug: cek nilai is_premium

    return [
        {
            "lesson_id": r["lesson_id"],
            "title": r["title"],
            "description": r["description"],
            "order_index": r["order_index"] - 1,  # 🔥 penting buat Flutter
            "unlocked": bool(r["unlocked"]),
            "completed_letters": int(r["completed_letters"]),
            "total_letters": int(r["total_letters"]),
            "average_score": float(r["average_score"]), 
            "is_premium": int(r["is_premium"]),
        }
        for r in rows
    ]


def fetch_hijaiyah_letters(lesson_id: int, user_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # cek apakah lesson premium
    cursor.execute(
        "SELECT is_premium FROM hijaiyah_lessons WHERE id = %s",
        (lesson_id,),
    )
    lesson = cursor.fetchone()

    if not lesson:
        cursor.close()
        db.close()
        return None

    if lesson["is_premium"] == 1:
        if not is_user_premium(user_id):
            cursor.close()
            db.close()
            raise HTTPException(
                status_code=403,
                detail="PREMIUM_LOCKED"
            )

    # ambil letters
    cursor.execute(
        """
        SELECT id, latin, arabic
        FROM hijaiyah_letters
        WHERE lesson_id = %s
        ORDER BY id
        """,
        (lesson_id,),
    )

    rows = cursor.fetchall()
    cursor.close()
    db.close()

    return rows



def unlock_hijaiyah_lesson(user_id: int, lesson_id: int):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT IGNORE INTO hijaiyah_lesson_unlocks
        (user_id, lesson_id, unlocked_at)
        VALUES (%s, %s, NOW())
        """,
        (user_id, lesson_id),
    )

    db.commit()
    cursor.close()
    db.close()

    return {"message": "Lesson unlocked"}


def upsert_hijaiyah_progress(
    user_id: int,
    lesson_id: int,
    completed_letters: int,
    score: float,
):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO hijaiyah_progress
        (user_id, lesson_id, completed_letters, average_score)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            completed_letters = VALUES(completed_letters),
            average_score = VALUES(average_score)
        """,
        (user_id, lesson_id, completed_letters, score),
    )

    db.commit()
    cursor.close()
    db.close()

    return {"message": "Progress updated"}
