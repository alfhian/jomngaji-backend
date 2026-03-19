from app.services.auth_service import get_db


def save_exam_attempt(
    user_id: int,
    total_questions: int,
    correct_answers: int,
    score_pg: int,       # skor pilihan ganda
    final_score: int,    # skor gabungan
    xp: int,
):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO iqra_exam_results
        (user_id, total_questions, correct_answers, score, final_score, xp_earned, created_at)
        VALUES (%s,%s,%s,%s,%s,%s,NOW())
        """,
        (
            user_id,
            total_questions,
            correct_answers,
            score_pg,
            final_score,
            xp,
        ),
    )

    db.commit()
    cursor.close()
    db.close()


def get_last_exam(user_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM iqra_exam_results
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user_id,),
    )

    row = cursor.fetchone()
    cursor.close()
    db.close()

    return row


def get_best_exam_score(user_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT MAX(score) AS best_score
        FROM iqra_exam_results
        WHERE user_id = %s
        """,
        (user_id,),
    )

    row = cursor.fetchone()
    cursor.close()
    db.close()

    return row