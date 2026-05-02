import jwt
import os
from datetime import datetime, timedelta, timezone
from fastapi import Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

JWT_SECRET = os.getenv("JWT_SECRET", "secret_key")
ALGORITHM = "HS256"

security = HTTPBearer()
def create_access_token(user_id: str ) -> str:
    """Expires in 15 mins"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    payload = {"sub": user_id, "exp": expire, "type": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    """Expires in a day"""
    expire = datetime.now(timezone.utc) ++ timedelta(days=1)
    payload = {"sub": user_id, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentilas = Security(security)):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])

        return payload.get("sub")

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token Expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    