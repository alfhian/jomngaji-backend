import json
from app.services.auth_service import get_db


# ======================================================
# GET AYAT YANG SUDAH DINILAI
# ======================================================
def get_evaluated_ayahs(user_id: int, surah: int) -> list[int]:
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT ayah
        FROM tadarus_evaluations
        WHERE user_id = %s AND surah = %s
        ORDER BY ayah
        """,
        (user_id, surah),
    )

    rows = cursor.fetchall()

    cursor.close()
    db.close()

    return [row["ayah"] for row in rows]


# ======================================================
# UPSERT EVALUATION (ANTI TURUN SCORE)
# ======================================================
def upsert_evaluation(
    *,
    user_id: int,
    surah: int,
    ayah: int,
    score_final: int,
    score_ayat: int,
    score_audio: int,
    asr_user: str,
    asr_ref: str,
    issues: list,
    suggestions: list,
) -> bool:
    """
    Rules:
    - INSERT jika belum ada
    - UPDATE hanya jika score baru >= score lama
    - Jika score baru < score lama → SKIP
    """

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # =========================
    # CEK DATA EXISTING
    # =========================
    cursor.execute(
        """
        SELECT id, score_final
        FROM tadarus_evaluations
        WHERE user_id = %s AND surah = %s AND ayah = %s
        """,
        (user_id, surah, ayah),
    )

    record = cursor.fetchone()

    # =========================
    # UPDATE (ANTI DOWNGRADE)
    # =========================
    if record:
        old_score = record["score_final"] or 0

        # ❌ Jangan update kalau score turun
        if score_final < old_score:
            cursor.close()
            db.close()
            return False

        cursor.execute(
            """
            UPDATE tadarus_evaluations
            SET
                score_final = %s,
                score_ayat = %s,
                score_audio = %s,
                asr_user = %s,
                asr_ref = %s,
                issues = %s,
                suggestions = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                score_final,
                score_ayat,
                score_audio,
                asr_user,
                asr_ref,
                json.dumps(issues, ensure_ascii=False),
                json.dumps(suggestions, ensure_ascii=False),
                record["id"],
            ),
        )

    # =========================
    # INSERT
    # =========================
    else:
        cursor.execute(
            """
            INSERT INTO tadarus_evaluations
            (
                user_id,
                surah,
                ayah,
                score_final,
                score_ayat,
                score_audio,
                asr_user,
                asr_ref,
                issues,
                suggestions,
                evaluated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """,
            (
                user_id,
                surah,
                ayah,
                score_final,
                score_ayat,
                score_audio,
                asr_user,
                asr_ref,
                json.dumps(issues, ensure_ascii=False),
                json.dumps(suggestions, ensure_ascii=False),
            ),
        )

    db.commit()
    cursor.close()
    db.close()

    return True
