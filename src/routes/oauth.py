from datetime import timedelta
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
import httpx
from sqlalchemy.orm import Session
import uuid
from ..config import settings
from ..auth import create_access_token
from ..database import get_db
from ..models import UserDB

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/login/google")
async def login_google():
    """Constructs the Google Login URL."""
    params = {
        "response_type": "code",
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.REDIRECT_URI,
        "scope": "openid profile email",
        "access_type": "offline"
    }
    query_string = "&".join([f"{key}={value}" for key, value in params.items()])
    return {"url": f"{settings.GOOGLE_AUTH_URL}?{query_string}"}

@router.get("/google/callback")
async def auth_google_callback(code: str, db: Session = Depends(get_db)):
    """Exchanges the Google code for a token and creates/updates user."""
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    
    async with httpx.AsyncClient() as client:
        # Exchange code for Google Token
        response = await client.post(settings.GOOGLE_TOKEN_URL, data=data)
        response_json = response.json()
        
        if "access_token" not in response_json:
            print(f"Google Error: {response_json}")
            raise HTTPException(
                status_code=400, 
                detail="Failed to retrieve access token from Google"
            )
            
        access_token = response_json["access_token"]
        
        # Get User Info from Google
        user_info_response = await client.get(
            settings.GOOGLE_USERINFO_URL, 
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_info = user_info_response.json()
    
    # Check if user exists in database
    user = db.query(UserDB).filter(UserDB.email == user_info["email"]).first()
    
    if not user:
        # Create new user
        user = UserDB(
            id=str(uuid.uuid4()),
            email=user_info["email"],
            name=user_info.get("name"),
            picture=user_info.get("picture"),
            google_id=user_info.get("id")
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update existing user info
        user.name = user_info.get("name")
        user.picture = user_info.get("picture")
        user.google_id = user_info.get("id")
        db.commit()
        db.refresh(user)
    
    # Create JWT token for our app
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    app_token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id
        },
        expires_delta=access_token_expires
    )
    
    # Redirect back to frontend with token
    return RedirectResponse(url=f"{settings.FRONTEND_URL}?token={app_token}")