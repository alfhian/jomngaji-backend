from google.oauth2 import id_token
from google.auth.transport import requests
from fastapi import HTTPException
from app.database import get_db_connection
import os

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

def verify_google_token(token: str):
    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )
        return idinfo
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Google token")


def login_or_register_google(idinfo: dict):
    email = idinfo["email"]
    name = idinfo.get("name")
    google_id = idinfo["sub"]
    avatar = idinfo.get("picture")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()

    if user:
        # update google_id jika belum ada
        if not user.get("google_id"):
            cursor.execute("""
                UPDATE users
                SET google_id=%s, provider='google'
                WHERE id=%s
            """, (google_id, user["id"]))
            conn.commit()

        cursor.close()
        conn.close()
        return user

    # kalau belum ada → create
    cursor.execute("""
        INSERT INTO users (email, name, google_id, provider, avatar)
        VALUES (%s, %s, %s, 'google', %s)
    """, (email, name, google_id, avatar))

    conn.commit()
    user_id = cursor.lastrowid

    cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    return user

