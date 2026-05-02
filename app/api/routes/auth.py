from fastapi import APIRouter, Depends, HTTPException, status, Depends
import httpx
from models.model import TokenExchangeRequest, User
from db.session import get_session
import os
from dotenv import load_dotenv
from services.security import create_access_token, create_refresh_token, get_current_user
from sqlmodel import Session, select

router = APIRouter()
load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
REDIRECT_URI = os.getenv("REDIRECT_URI")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

@router.post("/github/exchange")
async def exchange_github_token(request: TokenExchangeRequest, session: Session = Depends(get_session)):
    token_url = "https://github.com/login/oauth/access_token"

    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": request.code,
        "code_verifier": request.code_verifier,
        "grant_type": "authorization_code", 
        "redirect_uri": REDIRECT_URI
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, json=payload, headers=headers)

        #print(response.text)
        data = response.json()
        if response.status_code != 200:
            error_msg = data.get("error_description", "Unknown error from GitHub")
            raise HTTPException(status_code=400, detail=f"Github says: {data}")

        if "error" in data:
            error_msg = data.get("error_description", "Unknown error from GitHub")
            raise HTTPException(status_code=400, detail=f"Github says: {error_msg}")
    
        github_access_token = data.get("access_token")

        # FETCH USER DETAILS FROM GITHUB API
        github_user_url = "https://api.github.com/user"
        user_header = {
            "Authorization": f"Bearer {github_access_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        # check if the user exists in data base else create them
        async with httpx.AsyncClient() as client:
            user_response = await client.get(github_user_url, headers=user_header)
            if user_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch github Profile")
            
            github_user = user_response.json()
            github_username = github_user.get("login")
            github_email = github_user.get("email")

            if not github_email:
                github_email = f"{github_username}@username.noreply.github.com"

            statement = select(User).where(github_username == github_username)
            user = session.exec(statement).first()
            if not user:
                user = User(github_username=github_username, email=github_email)
                session.add(user)
                session.commit()
                session.refresh(user)
            
            user_identifier = user.id
            access_token = create_access_token(user_id=user_identifier)
            refresh_token = create_refresh_token(user_id=user_identifier)


        return {
            "message": "Login successful",
            "github_token": github_access_token,
            "refresh_token": refresh_token,
            "access_token": access_token,
            "token_type": "bearer"
        }