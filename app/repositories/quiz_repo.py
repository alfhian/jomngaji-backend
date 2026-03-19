from app.services.auth_service import get_db


# =========================================
# GET QUIZ BY CODE
# =========================================
def get_quiz_by_code(quiz_code: str):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM quizzes WHERE quiz_code = %s",
        (quiz_code,),
    )
    quiz = cursor.fetchone()

    cursor.close()
    db.close()

    return quiz


# =========================================
# GET QUESTIONS
# =========================================
def get_questions_by_quiz_id(quiz_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT id, question_text
        FROM quiz_questions
        WHERE quiz_id = %s
        ORDER BY id ASC
        """,
        (quiz_id,),
    )

    rows = cursor.fetchall()
    cursor.close()
    db.close()

    return rows


# =========================================
# GET OPTIONS
# =========================================
def get_options_by_question_id(question_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT option_text
        FROM quiz_options
        WHERE question_id = %s
        """,
        (question_id,),
    )

    rows = cursor.fetchall()
    cursor.close()
    db.close()

    return rows


# =========================================
# GET QUESTION (UNTUK CHECK JAWABAN)
# =========================================
def get_question_by_id(question_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM quiz_questions WHERE id = %s",
        (question_id,),
    )

    row = cursor.fetchone()
    cursor.close()
    db.close()

    return row


# =========================================
# SAVE ATTEMPT
# =========================================
def save_quiz_attempt(
    user_id: int,
    quiz_id: int,
    correct: int,
    total: int,
    score: float,
    xp: int,
):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO quiz_attempts
            (user_id, quiz_id, correct, total, score, xp, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """,
        (user_id, quiz_id, correct, total, score, xp),
    )

    db.commit()
    cursor.close()
    db.close()


def get_quiz_progress_by_quiz_id(user_id: int, quiz_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT correct, total, score, xp, created_at
        FROM quiz_attempts
        WHERE user_id = %s AND quiz_id = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user_id, quiz_id),
    )

    row = cursor.fetchone()
    cursor.close()
    db.close()
    return row


def get_best_quiz_score(user_id: int, quiz_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT MAX(score) AS best_score
        FROM quiz_attempts
        WHERE user_id = %s AND quiz_id = %s
        """,
        (user_id, quiz_id),
    )
    row = cursor.fetchone()
    cursor.close()
    db.close()
    return row
