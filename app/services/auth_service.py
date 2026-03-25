import bcrypt
import mysql.connector
from fastapi import HTTPException

# 🔥 Import JWT dari auth.py (single source of truth)
from auth import create_access_token


# =========================
# DB CONNECTION
# =========================
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="jomngaji"
    )


# =========================
# REGISTER
# =========================
def register_user(email: str, password: str, name: str):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    cursor.execute(
        "INSERT INTO users (email, password, name) VALUES (%s, %s, %s)",
        (email, hashed.decode(), name)
    )

    db.commit()
    cursor.close()
    db.close()


# =========================
# LOGIN
# =========================
def login_user(email: str, password: str):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()

    cursor.close()
    db.close()

    if not user or not bcrypt.checkpw(password.encode(), user['password'].encode()):
        raise HTTPException(status_code=401, detail="Email atau password salah")

    token = create_access_token({"sub": str(user["id"])})

    return {
        "access_token": token,
        "userId": user["id"],
        "name": user["name"]
    }


# =========================
# RESET PASSWORD
# =========================
def reset_password(user_id: int, old_password: str, new_password: str):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    if not bcrypt.checkpw(old_password.encode(), user['password'].encode()):
        raise HTTPException(status_code=400, detail="Password lama salah")

    new_hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

    cursor.execute(
        "UPDATE users SET password = %s WHERE id = %s",
        (new_hashed, user_id)
    )

    db.commit()
    cursor.close()
    db.close()

    return True


# =========================
# GOOGLE
# =========================
def get_user_by_email(email: str):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    return user


def create_google_user(email: str, name: str, google_id: str):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        INSERT INTO users (email, name, google_id, provider)
        VALUES (%s, %s, %s, 'google')
    """, (email, name, google_id))

    conn.commit()
    user_id = cursor.lastrowid

    cursor.close()
    conn.close()

    return {
        "id": user_id,
        "email": email,
        "name": name,
        "google_id": google_id,
        "provider": "google",
    }
