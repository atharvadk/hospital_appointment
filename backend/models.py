import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "patient", "doctor", "admin"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    doctor_profile = relationship("DoctorProfile", back_populates="user", uselist=False)
    appointments_patient = relationship(
        "Appointment", back_populates="patient", foreign_keys="Appointment.patient_id"
    )


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    specialisation = Column(String, nullable=False)
    working_hours = Column(
        Text, nullable=False
    )  # JSON: {"Monday": {"start": "09:00", "end": "17:00"}, ...}
    slot_duration = Column(Integer, default=30)  # in minutes
    leave_days = Column(
        Text, default="[]"
    )  # JSON list of dates: ["2026-07-20", "2026-07-21"]
    bio = Column(Text, nullable=True)

    user = relationship("User", back_populates="doctor_profile")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(String, nullable=False)  # YYYY-MM-DD
    start_time = Column(String, nullable=False)  # HH:MM
    end_time = Column(String, nullable=False)  # HH:MM
    status = Column(String, default="booked")  # "booked", "cancelled", "completed"

    symptoms = Column(Text, nullable=True)
    pre_visit_urgency = Column(String, nullable=True)  # "Low", "Medium", "High"
    pre_visit_complaint = Column(Text, nullable=True)
    pre_visit_questions = Column(Text, nullable=True)  # JSON string or plain text list

    clinical_notes = Column(Text, nullable=True)
    prescription = Column(Text, nullable=True)
    post_visit_summary = Column(Text, nullable=True)  # LLM output

    google_event_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    doctor = relationship("User", foreign_keys=[doctor_id])
    patient = relationship(
        "User", foreign_keys=[patient_id], back_populates="appointments_patient"
    )
    reminders = relationship(
        "MedicationReminder", back_populates="appointment", cascade="all, delete-orphan"
    )


class SlotHold(Base):
    __tablename__ = "slot_holds"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(String, nullable=False)  # YYYY-MM-DD
    start_time = Column(String, nullable=False)  # HH:MM
    end_time = Column(String, nullable=False)  # HH:MM
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    locked_until = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "doctor_id", "date", "start_time", name="_doctor_slot_hold_uc"
        ),
    )


class EmailQueue(Base):
    __tablename__ = "email_queue"

    id = Column(Integer, primary_key=True, index=True)
    recipient = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String, default="pending")  # "pending", "sent", "failed"
    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)


class MedicationReminder(Base):
    __tablename__ = "medication_reminders"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(
        Integer, ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False
    )
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    medication_name = Column(String, nullable=False)
    dosage = Column(String, nullable=False)
    frequency_hours = Column(
        Integer, nullable=False
    )  # Frequency in hours (e.g. 8 for 3x daily)
    last_sent_at = Column(DateTime, nullable=True)
    next_due_at = Column(DateTime, nullable=False)
    status = Column(String, default="active")  # "active", "completed"

    appointment = relationship("Appointment", back_populates="reminders")
    patient = relationship("User", foreign_keys=[patient_id])


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    provider = Column(String, default="google")
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=False)
