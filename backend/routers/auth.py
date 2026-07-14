from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from backend.database import get_db
from backend.models import DoctorProfile, User
from backend.schemas import Token, UserRegister, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Hash password
    hashed_password = get_password_hash(user_data.password)

    # Create user
    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # If the user is a doctor, create a default profile for them
    if new_user.role == "doctor":
        default_working_hours = '{"Monday": {"start": "09:00", "end": "17:00"}, "Tuesday": {"start": "09:00", "end": "17:00"}, "Wednesday": {"start": "09:00", "end": "17:00"}, "Thursday": {"start": "09:00", "end": "17:00"}, "Friday": {"start": "09:00", "end": "17:00"}}'
        profile = DoctorProfile(
            user_id=new_user.id,
            specialisation="General Medicine",
            working_hours=default_working_hours,
            slot_duration=30,
            bio="Default biography.",
        )
        db.add(profile)
        db.commit()

    return new_user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "name": user.full_name,
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
