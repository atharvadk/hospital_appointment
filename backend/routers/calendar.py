import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from jose import jwt
from sqlalchemy.orm import Session

from backend.auth import ALGORITHM, SECRET_KEY, get_current_user
from backend.calendar_service import get_google_flow, save_oauth_token
from backend.database import get_db
from backend.models import User

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


@router.get("/auth")
def authenticate_google(token: str, db: Session = Depends(get_db)):
    """
    Initiates Google Calendar OAuth.
    We pass JWT token as query param since this is a direct browser redirection.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Encode state with user_id to identify them on callback
        state = token
        flow = get_google_flow(state=state)
        authorization_url, _ = flow.authorization_url(
            access_type="offline", include_granted_scopes="true", prompt="consent"
        )
        return {"authorization_url": authorization_url}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initiate Google OAuth: {str(e)}"
        )


@router.get("/callback")
def google_oauth_callback(code: str, state: str, db: Session = Depends(get_db)):
    """
    Handles Google redirection, exchanges code for token, and saves it.
    """
    # Decode token from state to identify user
    try:
        payload = jwt.decode(state, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token in state")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token in state")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        flow = get_google_flow(state=state)
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Save token
        save_oauth_token(db, user.id, credentials)

        # Redirect back to frontend dashboard
        return RedirectResponse(url=f"{FRONTEND_URL}/?calendar_connected=true")
    except Exception as e:
        # Redirect with error
        return RedirectResponse(url=f"{FRONTEND_URL}/?calendar_error={str(e)}")


@router.get("/status")
def get_calendar_status(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    from backend.models import OAuthToken

    token = db.query(OAuthToken).filter(OAuthToken.user_id == current_user.id).first()
    return {"connected": token is not None}


@router.post("/disconnect")
def disconnect_calendar(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    from backend.models import OAuthToken

    db.query(OAuthToken).filter(OAuthToken.user_id == current_user.id).delete()
    db.commit()
    return {"message": "Google Calendar disconnected successfully"}
