from app.repositories.quiz_repo import (
    get_quiz_by_code,
    get_questions_by_quiz_id,
    get_options_by_question_id,
    get_question_by_id,
    save_quiz_attempt,
    get_quiz_progress_by_quiz_id,
    get_best_quiz_score,
)

PASSING_SCORE = 50


# =========================================
# FETCH QUESTIONS
# =========================================
def fetch_quiz_questions(quiz_code: str):
    quiz = get_quiz_by_code(quiz_code)
    if not quiz:
        return None

    questions = get_questions_by_quiz_id(quiz["id"])

    result = []

    for q in questions:
        options = get_options_by_question_id(q["id"])

        result.append({
            "question_id": q["id"],
            "question_text": q["question_text"],
            "options": [o["option_text"] for o in options],
        })

    return result


# =========================================
# SUBMIT QUIZ
# =========================================
def submit_quiz(user_id: int, quiz_code: str, answers: list):
    quiz = get_quiz_by_code(quiz_code)
    if not quiz:
        return None

    correct = 0

    for item in answers:
        question = get_question_by_id(item["question_id"])
        if question and question["correct_answer"] == item["selected_option"]:
            correct += 1

    total = len(answers)
    score_percent = (correct / total) * 100 if total else 0
    xp = correct * 5

    # 🔥 SAVE ATTEMPT (FIXED)
    save_quiz_attempt(
        user_id=user_id,
        quiz_id=quiz["id"],
        correct=correct,
        total=total,
        score=round(score_percent, 2),
        xp=xp,
    )

    return {
        "correct": correct,
        "total": total,
        "score": round(score_percent, 2),
        "xp": xp,
        "passed": score_percent >= PASSING_SCORE,
    }

def get_quiz_progress(user_id: int, quiz_code: str, pass_threshold: int = PASSING_SCORE):
    quiz = get_quiz_by_code(quiz_code)
    if not quiz:
        return None

    # ambil attempt terakhir (untuk detail)
    last_attempt = get_quiz_progress_by_quiz_id(user_id, quiz["id"])
    # ambil skor tertinggi
    best_attempt = get_best_quiz_score(user_id, quiz["id"])

    if not last_attempt and not best_attempt:
        return {
            "quiz_code": quiz_code,
            "user_id": user_id,
            "progress": 0.0,
            "passed": False,
            "correct": 0,
            "total": 0,
            "score": 0,
            "xp": 0,
            "best_score": 0,
        }

    best_score = best_attempt["best_score"] if best_attempt and best_attempt["best_score"] is not None else 0
    passed = best_score >= pass_threshold
    progress = 0.5 if passed else 0.0

    return {
        "quiz_code": quiz_code,
        "user_id": user_id,
        "progress": progress,   # ✅ progress dihitung dari skor tertinggi
        "passed": passed,
        "correct": last_attempt["correct"] if last_attempt else 0,
        "total": last_attempt["total"] if last_attempt else 0,
        "score": last_attempt["score"] if last_attempt else 0,  # skor terakhir
        "xp": last_attempt["xp"] if last_attempt else 0,
        "best_score": best_score,  # ✅ skor tertinggi
    }


