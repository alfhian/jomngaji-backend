from fastapi import Depends, HTTPException
from app.dependencies.auth import get_current_user
from app.services.premium_service import is_user_premium

def require_premium(current_user=Depends(get_current_user)):
    if not is_user_premium(current_user["id"]):
        raise HTTPException(
            status_code=403,
            detail="PREMIUM_REQUIRED"
        )
    return current_user