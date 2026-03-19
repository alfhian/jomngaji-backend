from datetime import datetime
from app.services.auth_service import get_db

def is_user_premium(user_id: int) -> bool:
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT expiry_date
        FROM subscriptions
        WHERE user_id = %s
        AND status = 'active'
        ORDER BY expiry_date DESC
        LIMIT 1
    """, (user_id,))

    sub = cursor.fetchone()

    cursor.close()
    db.close()

    if not sub:
        return False

    return sub["expiry_date"] > datetime.utcnow()