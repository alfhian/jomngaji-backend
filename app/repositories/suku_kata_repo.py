from app.services.auth_service import get_db
from fastapi import HTTPException
from app.services.premium_service import is_user_premium

# =========================
# EXISTING (TIDAK DIUBAH)
# =========================

def fetch_suku_kata_levels(user_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            l.id AS level_id,
            l.title,
            l.description,
            l.total_questions,
            l.order_index,
            l.is_premium,

            CASE
                WHEN l.order_index = 1 THEN 1
                WHEN l.is_premium = 1 AND u2.is_premium = 0 THEN 0
                WHEN u.level_id IS NOT NULL THEN 1
                ELSE 0
            END AS unlocked,

            COALESCE(p.completed_questions, 0) AS completed_questions,
            COALESCE(p.average_score, 0) AS average_score

        FROM suku_kata_levels l

        LEFT JOIN users u2
            ON u2.id = %s

        LEFT JOIN suku_kata_level_unlocks u
            ON u.level_id = l.id AND u.user_id = %s

        LEFT JOIN suku_kata_progress p
            ON p.level_id = l.id AND p.user_id = %s

        ORDER BY l.order_index;
        """,
        (user_id, user_id, user_id),
    )

    rows = cursor.fetchall()
    cursor.close()
    db.close()

    return rows


def fetch_suku_kata_questions(level_id: int, user_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # cek apakah level premium
    cursor.execute(
        "SELECT is_premium FROM suku_kata_levels WHERE id = %s",
        (level_id,),
    )
    level = cursor.fetchone()

    if not level:
        cursor.close()
        db.close()
        return None

    if level["is_premium"] == 1:
        if not is_user_premium(user_id):
            raise HTTPException(
                status_code=403,
                detail="PREMIUM_LOCKED"
            )
        user = cursor.fetchone()

        if not user or user["is_premium"] == 0:
            cursor.close()
            db.close()
            raise HTTPException(
                status_code=403,
                detail="PREMIUM_LOCKED"
            )

    # ambil questions
    cursor.execute(
        """
        SELECT id, latin, arabic
        FROM suku_kata_questions
        WHERE level_id = %s
        ORDER BY id
        """,
        (level_id,),
    )

    rows = cursor.fetchall()
    cursor.close()
    db.close()

    return rows


# =========================
# NEW — UNTUK SUBMIT SCORE
# =========================

def fetch_level_meta(level_id: int):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT total_questions, order_index FROM suku_kata_levels WHERE id = %s",
        (level_id,),
    )
    row = cursor.fetchone()

    cursor.close()
    db.close()
    return row


def upsert_suku_kata_progress(
    user_id: int,
    level_id: int,
    completed_questions: int,
    score: float,
):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO suku_kata_progress
        (user_id, level_id, completed_questions, average_score)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            completed_questions = VALUES(completed_questions),
            average_score = VALUES(average_score)
        """,
        (user_id, level_id, completed_questions, score),
    )

    db.commit()
    cursor.close()
    db.close()


def fetch_next_level_id(order_index: int):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT id FROM suku_kata_levels WHERE order_index = %s",
        (order_index + 1,),
    )
    row = cursor.fetchone()

    cursor.close()
    db.close()
    return row[0] if row else None


def unlock_suku_kata_level(user_id: int, level_id: int):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT IGNORE INTO suku_kata_level_unlocks
        (user_id, level_id, unlocked_at)
        VALUES (%s, %s, NOW())
        """,
        (user_id, level_id),
    )

    db.commit()
    cursor.close()
    db.close()
