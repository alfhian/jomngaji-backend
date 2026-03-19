from app.services.auth_service import get_db
from app.services import quran_service

def get_progress_by_surah(user_id: int, surah: int):
    print("====== GET TADARUS PROGRESS ======")
    print(f"user_id = {user_id}, surah = {surah}")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    print("[QUERY] SELECT FROM tadarus_progress")

    cursor.execute(
        """
        SELECT
            user_id,
            surah,
            completed_ayah,
            total_ayah,
            average_score,
            ROUND((completed_ayah / total_ayah) * 100, 2) AS percentage
        FROM tadarus_progress
        WHERE user_id = %s AND surah = %s
        """,
        (user_id, surah),
    )

    row = cursor.fetchone()

    print("[RESULT RAW DB]")
    print(row)

    cursor.close()
    db.close()

    print("====== END GET PROGRESS ======")

    if row:
      return {
				"user_id": row["user_id"],
				"surah": row["surah"],
				"completed_ayah": int(row["completed_ayah"]),
				"total_ayah": int(row["total_ayah"]),
				"average_score": float(row["average_score"]),
				"percentage": float(row["percentage"]),  # 🔥 INI PENTING
			}



from app.services.auth_service import get_db
from app.services import quran_service

def get_last_activity(user_id: int) -> dict:
    """
    Ambil aktivitas terakhir user:
    - last_read = ayat terakhir yang dinilai (score_final not null)
    - last_recited = ayat terakhir yang dilafalkan (recited_at not null)
    """

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:
        # =========================
        # Terakhir dinilai
        # =========================
        cursor.execute(
            """
            SELECT surah, ayah
            FROM tadarus_evaluations
            WHERE user_id = %s AND score_final IS NOT NULL
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (user_id,),
        )
        last_read_row = cursor.fetchone()

        # =========================
        # Terakhir dilafalkan
        # =========================
        cursor.execute(
            """
            SELECT surah, ayah
            FROM tadarus_evaluations
            WHERE user_id = %s AND evaluated_at IS NOT NULL
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (user_id,),
        )
        last_recited_row = cursor.fetchone()

        # =========================
        # Ambil nama surah dari quran_service
        # =========================
        def get_surah_name(surah_number):
            if surah_number is None:
                return None
            surah = quran_service.get_surah(surah_number)
            return surah["latin"] if surah else f"Surah {surah_number}"

        last_read = {
            "surah_name": get_surah_name(last_read_row["surah"] if last_read_row else None),
            "ayah": last_read_row["ayah"] if last_read_row else None
        }

        last_recited = {
            "surah_name": get_surah_name(last_recited_row["surah"] if last_recited_row else None),
            "ayah": last_recited_row["ayah"] if last_recited_row else None
        }

        return {"last_read": last_read, "last_recited": last_recited}

    except Exception as e:
        print("Error in get_last_activity:", e)
        raise e

    finally:
        cursor.close()
        db.close()


def update_progress(
    *,
    user_id: int,
    surah: int,
    total_ayah: int,
):
    """
    completed_ayah dihitung dari:
    COUNT(DISTINCT ayah) pada tadarus_evaluations
    """

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # =========================
    # HITUNG AYAT UNIK YANG LULUS
    # =========================
    cursor.execute(
        """
        SELECT COUNT(DISTINCT ayah) AS completed
        FROM tadarus_evaluations
        WHERE
            user_id = %s
            AND surah = %s
            AND score_final IS NOT NULL
        """,
        (user_id, surah),
    )

    completed = cursor.fetchone()["completed"] or 0

    # =========================
    # UPSERT PROGRESS
    # =========================
    cursor.execute(
        """
        SELECT id
        FROM tadarus_progress
        WHERE user_id = %s AND surah = %s
        """,
        (user_id, surah),
    )

    row = cursor.fetchone()

    if not row:
        cursor.execute(
            """
            INSERT INTO tadarus_progress
            (
                user_id,
                surah,
                completed_ayah,
                total_ayah
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                user_id,
                surah,
                completed,
                total_ayah,
            ),
        )
    else:
        cursor.execute(
            """
            UPDATE tadarus_progress
            SET
                completed_ayah = %s,
                total_ayah = %s
            WHERE id = %s
            """,
            (
                completed,
                total_ayah,
                row["id"],
            ),
        )

    db.commit()
    cursor.close()
    db.close()

    return {
        "completed_ayah": int(completed),
        "total_ayah": int(total_ayah),
        "percentage": round((completed / total_ayah) * 100, 2)
        if total_ayah > 0
        else 0,
    }


def get_global_progress(user_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # =========================
    # TOTAL AYAT QURAN (FIXED)
    # =========================
    all_surahs = quran_service.get_all_surahs()
    total_ayah_quran = sum(s["ayah_count"] for s in all_surahs)

    # =========================
    # TOTAL AYAT SELESAI USER
    # =========================
    cursor.execute(
        """
        SELECT COALESCE(SUM(completed_ayah), 0) AS completed
        FROM tadarus_progress
        WHERE user_id = %s
        """,
        (user_id,),
    )

    completed = cursor.fetchone()["completed"] or 0

    cursor.close()
    db.close()

    percentage = (
        round((completed / total_ayah_quran) * 100, 4)
        if total_ayah_quran > 0
        else 0
    )

    return {
        "user_id": user_id,
        "completed_ayah": int(completed),
        "total_ayah": int(total_ayah_quran),  # 🔥 INI KUNCI
        "percentage": percentage,
    }
