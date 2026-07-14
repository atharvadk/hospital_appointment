import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import get_admin, get_password_hash
from backend.calendar_service import delete_calendar_event
from backend.database import get_db
from backend.jobs import add_email_to_queue
from backend.models import Appointment, DoctorProfile, User
from backend.schemas import (
    DoctorProfileUpdate,
    DoctorResponse,
    LeaveToggleRequest,
    UserRegister,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/doctors", response_model=list[DoctorResponse])
def get_doctors(
    db: Session = Depends(get_db), current_admin: User = Depends(get_admin)
):
    profiles = db.query(DoctorProfile).all()
    results = []
    for p in profiles:
        results.append(
            DoctorResponse(
                id=p.user.id,
                full_name=p.user.full_name,
                email=p.user.email,
                specialisation=p.specialisation,
                working_hours=json.loads(p.working_hours),
                slot_duration=p.slot_duration,
                leave_days=json.loads(p.leave_days),
                bio=p.bio,
            )
        )
    return results


@router.post("/doctors", response_model=DoctorResponse)
def create_doctor(
    doc_data: UserRegister,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin),
):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == doc_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create doctor user
    hashed_password = get_password_hash(doc_data.password)
    user = User(
        email=doc_data.email,
        password_hash=hashed_password,
        full_name=doc_data.full_name,
        role="doctor",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create profile
    default_hours = {
        "Monday": {"start": "09:00", "end": "17:00"},
        "Tuesday": {"start": "09:00", "end": "17:00"},
        "Wednesday": {"start": "09:00", "end": "17:00"},
        "Thursday": {"start": "09:00", "end": "17:00"},
        "Friday": {"start": "09:00", "end": "17:00"},
    }

    profile = DoctorProfile(
        user_id=user.id,
        specialisation="General Practice",
        working_hours=json.dumps(default_hours),
        slot_duration=30,
        leave_days="[]",
        bio="New doctor profile.",
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return DoctorResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        specialisation=profile.specialisation,
        working_hours=default_hours,
        slot_duration=profile.slot_duration,
        leave_days=[],
        bio=profile.bio,
    )


@router.put("/doctors/{id}", response_model=DoctorResponse)
def update_doctor_profile(
    id: int,
    update_data: DoctorProfileUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin),
):
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found"
        )

    if update_data.specialisation is not None:
        profile.specialisation = update_data.specialisation
    if update_data.working_hours is not None:
        profile.working_hours = json.dumps(update_data.working_hours)
    if update_data.slot_duration is not None:
        profile.slot_duration = update_data.slot_duration
    if update_data.bio is not None:
        profile.bio = update_data.bio

    db.commit()
    db.refresh(profile)

    return DoctorResponse(
        id=profile.user.id,
        full_name=profile.user.full_name,
        email=profile.user.email,
        specialisation=profile.specialisation,
        working_hours=json.loads(profile.working_hours),
        slot_duration=profile.slot_duration,
        leave_days=json.loads(profile.leave_days),
        bio=profile.bio,
    )


@router.post("/doctors/{id}/leave")
def add_doctor_leave(
    id: int,
    req: LeaveToggleRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin),
):
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found"
        )

    leave_days = json.loads(profile.leave_days)
    if req.date in leave_days:
        return {"message": "Leave date already exists", "leave_days": leave_days}

    # Add leave day
    leave_days.append(req.date)
    profile.leave_days = json.dumps(leave_days)
    db.commit()

    # Process affected appointments
    affected_appointments = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == id,
            Appointment.date == req.date,
            Appointment.status == "booked",
        )
        .all()
    )

    cancelled_count = len(affected_appointments)
    for appt in affected_appointments:
        appt.status = "cancelled"

        # Notify patient
        subject = "Your appointment has been cancelled"
        body = (
            f"Hello {appt.patient.full_name},\n\n"
            f"We regret to inform you that your appointment with Dr. {appt.doctor.full_name} "
            f"on {appt.date} at {appt.start_time} has been cancelled because the doctor is on leave.\n\n"
            f"Please visit our portal to book another slot.\n\n"
            f"Apologies for the inconvenience,\nClinic Team"
        )
        add_email_to_queue(db, appt.patient.email, subject, body)

        # Delete from Google Calendar
        delete_calendar_event(db, appt)

    db.commit()

    return {
        "message": "Leave date added successfully",
        "leave_days": leave_days,
        "cancelled_appointments_count": cancelled_count,
    }


@router.delete("/doctors/{id}/leave/{date}")
def remove_doctor_leave(
    id: int,
    date: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin),
):
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found"
        )

    leave_days = json.loads(profile.leave_days)
    if date not in leave_days:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Leave date not found"
        )

    leave_days.remove(date)
    profile.leave_days = json.dumps(leave_days)
    db.commit()

    return {"message": "Leave date removed successfully", "leave_days": leave_days}
