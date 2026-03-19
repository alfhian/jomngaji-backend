from app.repositories.iqra_exam_repo import (
    save_exam_attempt,
    get_last_exam,
    get_best_exam_score,
)


PASSING_SCORE = 60


def submit_iqra_exam(user_id: int, total_questions: int, correct_answers: int, recording_scores: list):
    score_pg = int((correct_answers / total_questions) * 100)

    # rata-rata recording
    recording_percent = sum(recording_scores) / len(recording_scores) if recording_scores else 0

    # bobot 60% PG + 40% recording
    final_score = int((score_pg * 0.6) + (recording_percent * 0.4))

    xp = correct_answers * 5 

    save_exam_attempt(
        user_id=user_id,
        total_questions=total_questions,
        correct_answers=correct_answers,
        score_pg=score_pg,
        final_score=final_score,
        xp=xp,
    )

    return {
        "correct": correct_answers,
        "total": total_questions,
        "score_pg": score_pg,
        "recording_score": recording_percent,
        "final_score": final_score,
        "xp_earned": xp,
        "passed": final_score >= 60,
    }



def get_exam_progress(user_id: int):
    last = get_last_exam(user_id)
    best = get_best_exam_score(user_id)

    if not last:
        return {
            "progress": 0,
            "score": 0,
            "best_score": 0,
        }

    return {
        "progress": 1 if last["score"] >= PASSING_SCORE else 0,
        "score": last["score"],
        "best_score": best["best_score"] if best else 0,
    }