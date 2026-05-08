import jwt
import os
from datetime import datetime, timedelta, timezone
from fastapi import Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Request, HTTPException, status, Depends
from db.session import get_session
from models.model import User

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
    expire = datetime.now(timezone.utc) + timedelta(days=1)
    payload = {"sub": user_id, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    session: Session = Depends(get_sesion)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(status_code=401, detail="invalid token")

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token Expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = session.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="Usern not found")
    
    return User

async def get_user_browser(request: Request):

    token = request.cookies.get("access_token")
    csrf_cookie = request.cookies.get("csrf_token")
    csrf_header = request.headers.get("X-CSRF-Token")


    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Unauthorized: No web session found."
        )

    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Forbidden: CSRF validation failed."
        )

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload.get("sub")

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token Expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")