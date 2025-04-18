from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from scripts.prod_settings import settings

# Simulated user store (in-memory or later from DB)
users_db = {
    "admin@complyai.io": {
        "email": "admin@complyai.io",
        "hashed_password": "$2b$12$8J9SWzSn4l3YeRsSV7lXKuihDSYaQF1HAdgbJsgrQ4LKMg/YQK8ui",  #password = admin123
        "role": "admin"
    }
}

# Password encryption
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=2)):
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + expires_delta
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    user_email = payload.get("sub")
    if user_email is None or user_email not in users_db:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return users_db[user_email]

def admin_required(user=Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
