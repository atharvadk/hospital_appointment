from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "patient"  # "patient", "doctor", "admin"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    name: str


class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None


class DoctorProfileResponse(BaseModel):
    id: int
    specialisation: str
    working_hours: str  # JSON string
    slot_duration: int
    leave_days: str  # JSON string
    bio: Optional[str] = None

    class Config:
        from_attributes = True


class DoctorResponse(BaseModel):
    id: int  # User id
    full_name: str
    email: str
    specialisation: str
    working_hours: Dict[str, Any]
    slot_duration: int
    leave_days: List[str]
    bio: Optional[str] = None


class DoctorProfileUpdate(BaseModel):
    specialisation: Optional[str] = None
    working_hours: Optional[Dict[str, Any]] = None
    slot_duration: Optional[int] = None
    bio: Optional[str] = None


class SlotHoldCreate(BaseModel):
    doctor_id: int
    date: str  # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str  # HH:MM


class SlotHoldResponse(BaseModel):
    id: int
    doctor_id: int
    date: str
    start_time: str
    end_time: str
    patient_id: int
    locked_until: datetime

    class Config:
        from_attributes = True


class AppointmentCreate(BaseModel):
    doctor_id: int
    date: str  # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    symptoms: str


class AppointmentResponse(BaseModel):
    id: int
    doctor_id: int
    doctor_name: str
    patient_id: int
    patient_name: str
    date: str
    start_time: str
    end_time: str
    status: str
    symptoms: Optional[str] = None
    pre_visit_urgency: Optional[str] = None
    pre_visit_complaint: Optional[str] = None
    pre_visit_questions: Optional[List[str]] = None
    clinical_notes: Optional[str] = None
    prescription: Optional[str] = None
    post_visit_summary: Optional[str] = None
    google_event_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PostVisitSubmit(BaseModel):
    clinical_notes: str
    prescription: str


class MedicationReminderResponse(BaseModel):
    id: int
    appointment_id: int
    medication_name: str
    dosage: str
    frequency_hours: int
    last_sent_at: Optional[datetime] = None
    next_due_at: datetime
    status: str

    class Config:
        from_attributes = True


class LeaveToggleRequest(BaseModel):
    date: str  # YYYY-MM-DD
