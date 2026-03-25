from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from app.services.auth_service import get_db
from auth import create_access_token, get_current_user

# =========================
# 🔥 GOOGLE AUTH IMPORT
# =========================
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import os

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# =========================
# Utils
# =========================
from app.utils.audio_utils import save_upload, ensure_wav

# =========================
# AI Services (General)
# =========================
from app.services.asr_service import transcribe_audio
from app.services.tajwid_service import analyze_tajwid, evaluate_tajwid
from app.services.hijaiyah_service import evaluate_hijaiyah
from app.services.tilawah_service import evaluate_tilawah
from app.services.tahfidz_service import evaluate_tahfidz

# =========================
# Repositories
# =========================
from app.repositories.tadarus_progress_repo import (
    get_global_progress,
    get_progress_by_surah,
    get_last_activity,
)

from app.repositories.hijaiyah_progress_repo import (
    get_hijaiyah_progress,
    get_last_hijaiyah_activity,
    update_hijaiyah_after_evaluation,
    get_hijaiyah_global_progress,
    get_hijaiyah_lessons,
    ensure_hijaiyah_progress,
    save_hijaiyah_evaluation,
)

from app.repositories.hijaiyah_lesson_repo import (
    unlock_hijaiyah_lesson,
    upsert_hijaiyah_progress
)


from app.repositories.tajwid_repo import (
    save_tajwid_evaluation,
    get_last_tajwid_evaluation,
    get_average_tajwid_score,
    get_tajwid_progress,
)

from app.repositories.tilawah_repo import (
    save_tilawah_evaluation,
    get_last_tilawah_evaluation,
    get_average_tilawah_score,
)

from app.repositories.tahfidz_repo import (
    save_tahfidz_evaluation,
    get_last_tahfidz_evaluation,
    get_average_tahfidz_score,
)

# =========================
# Services
# =========================
from app.services.iqra_exam_service import (
    submit_iqra_exam,
    get_exam_progress,
)

from app.services.suku_kata_service import (
    get_suku_kata_levels,
    get_suku_kata_questions,
    submit_suku_kata_score,
)

from app.services.quiz_service import (
    fetch_quiz_questions,
    submit_quiz,
    get_quiz_progress,
)

from app.services.tadarus_asr_service import transcribe_tadarus
from app.services.tadarus_service import evaluate_tadarus
from app.services.tadarus_evaluation_service import evaluate_and_save_tadarus

from app.services.auth_service import (
    register_user,
    login_user,
    reset_password,
    get_user_by_email,        # 🔥 tambahkan
    create_google_user,       # 🔥 tambahkan
)

from app.services import quran_service

# =========================
# Models
# =========================
from app.models.evaluation_result import EvaluationResult
from app.models.user import UserCreate, UserLogin


# =========================
# APP INIT
# =========================
app = FastAPI(
    title="JomNgaji AI Backend",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# AUTH (LOCAL)
# =========================
@app.post("/register")
def register(data: UserCreate):
    register_user(data.email, data.password, data.name)
    return {"message": "Registrasi berhasil"}


@app.post("/login")
def login(data: UserLogin):
    return login_user(data.email, data.password)

@app.get("/premium/status")
def check_premium_status(user_id: int = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # cek dari table users
    cursor.execute("""
        SELECT is_premium, premium_expired_at
        FROM users
        WHERE id = %s
    """, (user_id,))
    user = cursor.fetchone()

    is_premium = False
    expired = None

    if user:
        expired = user["premium_expired_at"]

        if user["is_premium"] == 1 and expired:
            if expired > datetime.utcnow():
                is_premium = True

    # cek juga dari table subscriptions (optional)
    cursor.execute("""
        SELECT expiry_date
        FROM subscriptions
        WHERE user_id = %s
        AND status = 'active'
        ORDER BY expiry_date DESC
        LIMIT 1
    """, (user_id,))
    sub = cursor.fetchone()

    if sub:
        if sub["expiry_date"] > datetime.utcnow():
            is_premium = True
            expired = sub["expiry_date"]

    cursor.close()
    conn.close()

    return {
        "is_premium": is_premium,
        "expired_at": expired
    }

@app.post("/premium/verify")
def verify_premium(user_id: int = Depends(get_current_user)):
    # nanti di sini tambahkan Google receipt validation

    premium_until = datetime.utcnow() + timedelta(days=30)

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET premium_expired_at = %s
        WHERE id = %s
    """, (premium_until, user_id))

    conn.commit()
    cursor.close()
    conn.close()

    return {"message": "Premium activated"}

@app.post("/upgrade")
def dev_upgrade(user_id: int = Depends(get_current_user)):
    db = get_db()
    cursor = db.cursor()

    expiry = datetime.utcnow() + timedelta(days=30)

    cursor.execute(
        """
        UPDATE users
        SET is_premium = 1,
            premium_expired_at = %s
        WHERE id = %s
        """,
        (expiry, user_id),
    )

    db.commit()
    cursor.close()
    db.close()

    return {"message": "Premium activated", "expiry": expiry}


# ==========================================================
# 🔥 GOOGLE SIGN IN (NEW)
# ==========================================================
@app.post("/auth/google")
def google_login(token: str = Form(...)):
    print("TOKEN RECEIVED:", token)
    print("GOOGLE_CLIENT_ID:", GOOGLE_CLIENT_ID)
    try:
        if not GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID belum diset")

        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )

        google_id = idinfo["sub"]
        email = idinfo["email"]
        name = idinfo.get("name", "")

        # cek apakah user sudah ada
        user = get_user_by_email(email)

        if not user:
            user = create_google_user(
                email=email,
                name=name,
                google_id=google_id,
            )

        token = create_access_token({"sub": str(user["id"])})

        return {
            "access_token": token,
            "userId": user["id"],
            "name": user["name"],
            "provider": "google",
        }

    except Exception as e:
        print("GOOGLE VERIFY ERROR:", str(e))
        raise HTTPException(status_code=401, detail=str(e))


# @app.get("/hijaiyah/lessons")
# def list_lessons(user_id: int):
#     return get_hijaiyah_lessons(user_id)

@app.get("/hijaiyah/lessons/status")
def hijaiyah_lessons_status(user_id: int = Depends(get_current_user)):
    lessons = get_hijaiyah_lessons(user_id)

    print("HIJAIYAH STATUS:", lessons)

    return {
        "lessons": lessons
    }


@app.get("/hijaiyah/progress")
def hijaiyah_progress(user_id: int = Depends(get_current_user)):
    return get_hijaiyah_progress(user_id)


@app.get("/hijaiyah/global-progress")
def hijaiyah_global(user_id: int = Depends(get_current_user)):
    return get_hijaiyah_global_progress(user_id)


@app.get("/hijaiyah/last-activity")
def hijaiyah_last_activity(user_id: int = Depends(get_current_user)):
    return get_last_hijaiyah_activity(user_id)


@app.post("/hijaiyah/lessons/{lesson_id}/unlock")
def unlock_hijaiyah_lesson_endpoint(lesson_id: int, user_id: int = Depends(get_current_user)):
    return unlock_hijaiyah_lesson(user_id, lesson_id)


@app.post("/hijaiyah/lessons/{lesson_id}/submit")
def submit_hijaiyah_score_endpoint(
    lesson_id: int,
    payload: dict,
    user_id: int = Depends(get_current_user),
):
    return upsert_hijaiyah_progress(
        user_id=user_id,
        lesson_id=lesson_id,
        completed_letters=int(payload["completed_letters"]),
        score=float(payload["score"]),
    )



@app.get("/suku-kata/levels")
def get_levels(user_id: int = Depends(get_current_user)):
    return get_suku_kata_levels(user_id)


@app.get("/suku-kata/levels/{level_id}/questions")
def get_level_questions(level_id: int, user_id: int = Depends(get_current_user)):
    return get_suku_kata_questions(level_id, user_id)

@app.post("/suku-kata/levels/{level_id}/submit")
def submit_suku_kata_score_endpoint(
    level_id: int,
    payload: dict,
    user_id: int = Depends(get_current_user),
):
    return submit_suku_kata_score(
        user_id=user_id,
        level_id=level_id,
        score=float(payload["score"]),
    )


@app.get("/quizzes/{quiz_code}/questions")
def get_quiz_questions(quiz_code: str):
    result = fetch_quiz_questions(quiz_code)

    if not result:
        raise HTTPException(status_code=404, detail="Quiz tidak ditemukan")

    return result


@app.post("/quizzes/{quiz_code}/submit")
def submit_quiz_endpoint(
    quiz_code: str,
    payload: dict,
    user_id: int = Depends(get_current_user),
):
    result = submit_quiz(
        user_id=user_id,
        quiz_code=quiz_code,
        answers=payload["answers"],
    )

    if not result:
        raise HTTPException(status_code=404, detail="Quiz tidak ditemukan")

    return result


@app.get("/quizzes/{quiz_code}/progress")
def quiz_progress(quiz_code: str, user_id: int = Depends(get_current_user)):
    result = get_quiz_progress(user_id, quiz_code)
    if not result:
        raise HTTPException(status_code=404, detail="Quiz tidak ditemukan atau belum ada attempt")
    return result

@app.get("/iqra-exam/progress")
def iqra_exam_progress(user_id: int = Depends(get_current_user)):
    return get_exam_progress(user_id)


@app.post("/iqra-exam/submit")
def submit_iqra_exam_endpoint(
    payload: dict,
    user_id: int = Depends(get_current_user),
):
    return submit_iqra_exam(
        user_id=user_id,
        total_questions=payload["total_questions"],
        correct_answers=payload["correct_answers"],
        recording_scores=payload.get("recording_scores", []),
    )



@app.get("/tajwid/{quiz_code}/combined-progress")
def tajwid_combined_progress(quiz_code: str, user_id: int = Depends(get_current_user)):
    # Quiz progress
    quiz_result = get_quiz_progress(user_id, quiz_code) or {"progress": 0.0}
    quiz_passed = quiz_result.get("passed", False)
    quiz_progress = 0.5 if quiz_passed else 0.0

    # Recording progress
    tajwid_result = get_tajwid_progress(user_id, quiz_code)
    recording_progress = tajwid_result["progress"]

    combined = quiz_progress + recording_progress

    return {
        "quiz_progress": quiz_progress,
        "recording_progress": recording_progress,
        "combined_progress": combined,
        "quiz_detail": quiz_result,
        "recording_detail": tajwid_result,
    }




# =========================
# QURAN
# =========================
@app.get("/quran/surahs")
def list_surahs():
    return quran_service.get_all_surahs()


@app.get("/quran/surah/{surah_number}")
def get_surah(surah_number: int):
    surah = quran_service.get_surah(surah_number)
    if not surah:
        raise HTTPException(status_code=404, detail="Surah not found")
    return surah


@app.get("/quran/ayah/{surah_number}/{ayah_number}")
def get_ayah(surah_number: int, ayah_number: int):
    ayah = quran_service.get_ayah(surah_number, ayah_number)
    if not ayah:
        raise HTTPException(status_code=404, detail="Ayah not found")
    return ayah


# =========================
# GLOBAL TADARUS PROGRESS
# =========================
@app.get("/tadarus/global-progress")
def global_progress(user_id: int = Depends(get_current_user)):
    return get_global_progress(user_id)


# =========================
# AI EVALUATION (GENERAL) ✅ FIXED
# =========================
@app.post("/evaluate")
async def evaluate(
    user_id: int = Depends(get_current_user),
    audio: UploadFile = File(...),

    # hijaiyah
    target: str | None = Form(None),
    lesson_id: int | None = Form(None),

    # quran context
    surah: str | None = Form(None),
    ayah: int | None = Form(None),
):
    # =============================
    # VALIDATION
    # =============================
    if target and lesson_id is None:
        raise HTTPException(
            status_code=422,
            detail="lesson_id wajib untuk evaluasi hijaiyah",
        )

    # =============================
    # AUDIO → TEXT (ASR)
    # =============================
    path = ensure_wav(save_upload(audio))
    transcript = transcribe_audio(path)

    # =============================
    # TAJWID (GLOBAL)
    # =============================
    tajwid_scores, tajwid_issues, tajwid_suggestions = analyze_tajwid(transcript)

    # =============================
    # HIJAIYAH (OPTIONAL)
    # =============================
    hij_scores = {}
    hij_issues = []
    hij_suggestions = []

    hijaiyah_score = 0

    if target:
        hij_eval = evaluate_hijaiyah(
            transcription=transcript,
            target_letter=target,
        )

        hij_scores = hij_eval["scores"]
        hij_issues = hij_eval["issues"]
        hij_suggestions = hij_eval["suggestions"]

        hijaiyah_score = hij_scores.get("hijaiyah", 0)

        # =============================
        # PROGRESS
        # =============================
        ensure_hijaiyah_progress(user_id, lesson_id)

        # =============================
        # 🔥 SAVE HIJAIYAH EVALUATION
        # =============================
        save_hijaiyah_evaluation(
            user_id=user_id,
            lesson_id=lesson_id,
            hijaiyah=target,
            transcript=transcript,          
            score_final=hijaiyah_score,

            score_audio=None,
            score_ayat=None,

            feedback=" ".join(hij_suggestions) if hij_suggestions else None,  
            issues=hij_issues,
        )

        update_hijaiyah_after_evaluation(
            user_id=user_id,
            lesson_id=lesson_id,
            hijaiyah=target,              
            score=hijaiyah_score,        
        )




    # =============================
    # TILAWAH & TAHFIDZ (OPTIONAL / FUTURE)
    # =============================
    til_eval = evaluate_tilawah(transcript)
    til_scores = til_eval["scores"]
    til_issues = til_eval["issues"]
    til_suggestions = til_eval["suggestions"]

    tah_eval = evaluate_tahfidz(transcript)
    tah_scores = tah_eval["scores"]
    tah_issues = tah_eval["issues"]
    tah_suggestions = tah_eval["suggestions"]

    # =============================
    # FINAL SCORE STRATEGY
    # (sementara: hijaiyah dominates)
    # =============================
    final_score = (
        hijaiyah_score if target
        else tajwid_scores.get("tajwid", 0)
    )

    print("HIJAIYAH:", hijaiyah_score)
    print("TAJWID:", tajwid_scores.get("tajwid", 0))
    print("FINAL:", final_score) 

    # =============================
    # RESPONSE
    # =============================
    return {
        "text": transcript,
        "surah": surah,
        "ayah": ayah,
        "scores": {
            **tajwid_scores,
            **hij_scores,
            **til_scores,
            **tah_scores,
            "final": final_score,  # final selalu terakhir
        },
        "issues": [
            *tajwid_issues,
            *hij_issues,
            *til_issues,
            *tah_issues,
        ],
        "suggestions": [
            *tajwid_suggestions,
            *hij_suggestions,
            *til_suggestions,
            *tah_suggestions,
        ],
    }



@app.post("/evaluate/tajwid")
async def evaluate_tajwid_endpoint(
    user_id: int = Depends(get_current_user),
    lesson_id: int = Form(...),
    target_text: str = Form(...),
    audio: UploadFile = File(...),
):
    try:
        path = ensure_wav(save_upload(audio))
        transcript = transcribe_audio(path)

        result = evaluate_tajwid(transcript, target_text)

        save_tajwid_evaluation(
            user_id=user_id,
            lesson_id=lesson_id,
            transcript=transcript,
            score_final=result["scores"]["tajwid"],
            feedback=" ".join(result["suggestions"]) if result["suggestions"] else None,
            issues=result["issues"],
        )

        return {
            "text": transcript,
            "scores": result["scores"],
            "issues": result["issues"],
            "suggestions": result["suggestions"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/evaluate/tajwid/last")
def get_last_tajwid(user_id: int = Depends(get_current_user), lesson_id: int = Query(...)):
    return get_last_tajwid_evaluation(user_id, lesson_id)


@app.post("/evaluate/tilawah")
async def evaluate_tilawah_endpoint(
    user_id: int = Depends(get_current_user),
    lesson_id: int = Form(...),
    target_text: str = Form(...),
    audio: UploadFile = File(...),
):
    try:
        # Simpan audio upload → wav
        path = ensure_wav(save_upload(audio))
        transcript = transcribe_audio(path)

        # Evaluasi Tilawah
        result = evaluate_tilawah(transcript, target_text)

        # Simpan hasil evaluasi ke DB
        save_tilawah_evaluation(
            user_id=user_id,
            lesson_id=lesson_id,
            transcript=transcript,
            score_final=result["scores"]["tilawah"],
            feedback=" ".join(result["suggestions"]) if result["suggestions"] else None,
            issues=result["issues"],
        )

        return {
            "text": transcript,
            "scores": result["scores"],
            "issues": result["issues"],
            "suggestions": result["suggestions"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/evaluate/tilawah/last")
def get_last_tilawah(user_id: int = Depends(get_current_user), lesson_id: int = Query(...)):
    return get_last_tilawah_evaluation(user_id, lesson_id)


@app.post("/evaluate/tahfidz")
async def evaluate_tahfidz_endpoint(
    user_id: int = Depends(get_current_user),
    lesson_id: int = Form(...),
    target_text: str = Form(...),
    audio: UploadFile = File(...),
):
    try:
        # Simpan audio upload → wav
        path = ensure_wav(save_upload(audio))
        transcript = transcribe_audio(path)

        # Evaluasi Tahfidz
        result = evaluate_tahfidz(transcript, target_text)

        # Simpan hasil evaluasi ke DB
        save_tahfidz_evaluation(
            user_id=user_id,
            lesson_id=lesson_id,
            transcript=transcript,
            score_final=result["scores"]["tahfidz"],
            feedback=" ".join(result["suggestions"]) if result["suggestions"] else None,
            issues=result["issues"],
        )

        return {
            "text": transcript,
            "scores": result["scores"],
            "issues": result["issues"],
            "suggestions": result["suggestions"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/evaluate/tahfidz/last")
def get_last_tahfidz(user_id: int = Depends(get_current_user), lesson_id: int = Query(...)):
    return get_last_tahfidz_evaluation(user_id, lesson_id)



# =========================
# TADARUS (ASR)
# =========================
@app.post("/evaluate/tadarus")
async def evaluate_tadarus_endpoint(
    audio: UploadFile = File(...),
    surah: str | None = Form(None),
    ayah: int | None = Form(None),
    target: str | None = Form(None),
):
    try:
        path = ensure_wav(save_upload(audio))
        text = transcribe_tadarus(path)

        scores, issues, suggestions = evaluate_tadarus(target, text)

        return {
            "text": text,
            "surah": surah,
            "ayah": ayah,
            "scores": scores,
            "issues": issues,
            "suggestions": suggestions,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# TADARUS AUDIO → AUDIO (FINAL)
# =========================
@app.post("/evaluate/tadarus/audio")
async def evaluate_tadarus_audio_endpoint(
    user_id: int = Depends(get_current_user),
    surah: int = Form(...),
    ayah: int = Form(...),
    total_ayah: int = Form(...),
    user_audio: UploadFile = File(...),
    reference_audio: UploadFile = File(...),
):
    try:
        ayah_data = quran_service.get_ayah(surah, ayah)
        if not ayah_data:
            raise HTTPException(status_code=404, detail="Ayat tidak ditemukan")

        ayat_text = ayah_data["text"]

        return evaluate_and_save_tadarus(
            user_id=user_id,
            surah=surah,
            ayah=ayah,
            total_ayah=total_ayah,
            ayat_text=ayat_text,
            user_audio=user_audio,
            reference_audio=reference_audio,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# TADARUS PROGRESS
# =========================
@app.get("/tadarus/progress")
def get_tadarus_progress_query(user_id: int = Depends(get_current_user), surah: int = Query(...)):
    progress = get_progress_by_surah(user_id, surah)

    if not progress:
        return {
            "user_id": user_id,
            "surah": surah,
            "completed_ayah": 0,
            "total_ayah": 0,
            "percentage": 0,
            "average_score": 0,
        }

    return progress


@app.get("/tadarus/last-activity")
def last_activity(user_id: int = Depends(get_current_user)):
    return get_last_activity(user_id)




@app.get("/progress/summary")
def progress_summary(user_id: int = Depends(get_current_user)):
    hijaiyah = get_hijaiyah_progress(user_id) or {}
    tajwid = get_last_tajwid_evaluation(user_id, lesson_id=1) or {}
    tilawah = get_last_tilawah_evaluation(user_id, lesson_id=1) or {}
    tahfidz = get_last_tahfidz_evaluation(user_id, lesson_id=1) or {}

    return {
        "iqra_score": hijaiyah.get("score", 0),
        "tajwid_score": tajwid.get("score_final", 0),
        "tilawah_score": tilawah.get("score_final", 0),
        "tahfidz_score": tahfidz.get("score_final", 0),
    }


@app.get("/progress/average")
def progress_average(user_id: int = Depends(get_current_user)):
    iqra_avg = float(get_hijaiyah_global_progress(user_id).get("average_score", 0) or 0)
    tajwid_avg = get_average_tajwid_score(user_id)
    tilawah_avg = get_average_tilawah_score(user_id)
    tahfidz_avg = get_average_tahfidz_score(user_id)

    overall = (iqra_avg + tajwid_avg + tilawah_avg + tahfidz_avg) / 4

    return {
        "iqra_avg": iqra_avg,
        "tajwid_avg": tajwid_avg,
        "tilawah_avg": tilawah_avg,
        "tahfidz_avg": tahfidz_avg,
        "overall_avg": overall,
    }


# =========================
# AUTH - RESET PASSWORD
# =========================
@app.post("/reset-password")
def reset_password_endpoint(
    user_id: int = Depends(get_current_user),
    old_password: str = Form(...),
    new_password: str = Form(...),
):
    result = reset_password(user_id, old_password, new_password)
    if result:
        return {"message": "Password berhasil direset"}






# =========================
# HEALTH
# =========================
@app.get("/health")
def health():
    return {"status": "ok"}
