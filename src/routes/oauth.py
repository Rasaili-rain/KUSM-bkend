from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.responses import RedirectResponse
import httpx
from sqlalchemy.orm import Session
import uuid
from ..settings import settings
from ..database import get_db
from ..models import User, UserDB
from urllib.parse import urlencode
from typing import Optional
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login/google")
async def login_google(request: Request):
    """Constructs the Google Login URL."""
    # Dynamically build the callback URL from the request
    redirect_uri = f"{request.base_url}auth/google/callback"
    
    # Get where the user came from (for redirecting back after auth)
    referer = request.headers.get("referer", str(request.base_url))
    
    params = {
        "response_type": "code",
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": "openid profile email",
        "access_type": "offline",
        "state": referer,  # Remember where user came from, used to go back to actual fend app from google's oauth
    }
    
    return {"url": f"{settings.GOOGLE_AUTH_URL}?{urlencode(params)}"}


@router.get("/google/callback")
async def auth_google_callback(
    code: str,
    state: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Exchanges the Google code for a token and creates/updates user."""
    redirect_uri = f"{request.base_url}auth/google/callback"
    
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    
    async with httpx.AsyncClient() as client:
        # Exchange code for Google Token
        token_response = await client.post(settings.GOOGLE_TOKEN_URL, data=data)
        response_json = token_response.json()
        
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
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update existing user info
        user.name = user_info.get("name")
        user.picture = user_info.get("picture")
        db.commit()
        db.refresh(user)
    
    # Create JWT token for our app
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    app_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    # Redirect back to where the user came from with token
    return RedirectResponse(url=f"{state}?token={app_token}")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(UserDB).filter(UserDB.email == email).first()
    if user is None:
        raise credentials_exception
    
    return User.from_orm(user)


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user