# auth.py

from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import get_connection

# ========================
# CONFIGURATION
# ========================

SECRET_KEY = "your_super_secret_key_123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Use HTTPBearer instead of OAuth2PasswordBearer
security = HTTPBearer()


# ========================
# CREATE ACCESS TOKEN
# ========================

def create_access_token(data: dict):
    """
    Generates a JWT token with expiry time.
    """
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_jwt


# ========================
# VERIFY ACCESS TOKEN
# ========================

def verify_access_token(token: str):
    """
    Verifies JWT token and returns payload.
    Returns None if invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return payload

    except JWTError:
        return None


# ========================
# GET CURRENT USER (PROTECTED)
# ========================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Extracts user from JWT token and returns user info.
    """

    token = credentials.credentials

    payload = verify_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user_id = payload.get("user_id")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Fetch user from database
    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        "SELECT user_id, name, email FROM Users WHERE user_id = ?",
        (user_id,)
    )

    user = cursor.fetchone()

    conn.close()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return {
        "user_id": user[0],
        "name": user[1],
        "email": user[2]
    }
