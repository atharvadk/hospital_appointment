# ruff: noqa: E402
import os

# Load environment variables from .env
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.auth import get_password_hash
from backend.database import Base, SessionLocal, engine
from backend.jobs import start_background_jobs
from backend.models import DoctorProfile, User
from backend.routers import admin, auth, calendar, doctor, patient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)


# Seed initial database records
def seed_database():
    db = SessionLocal()
    try:
        # Create default Admin
        admin_email = "admin@clinic.com"
        admin_user = db.query(User).filter(User.email == admin_email).first()
        if not admin_user:
            admin_user = User(
                email=admin_email,
                password_hash=get_password_hash("adminpassword123"),
                full_name="Clinic System Admin",
                role="admin",
            )
            db.add(admin_user)
            db.commit()
            logger.info("Admin user seeded: admin@clinic.com / adminpassword123")

        # Create default Doctor
        doc_email = "doctor@clinic.com"
        doc_user = db.query(User).filter(User.email == doc_email).first()
        if not doc_user:
            doc_user = User(
                email=doc_email,
                password_hash=get_password_hash("doctorpassword123"),
                full_name="Dr. Gregory House",
                role="doctor",
            )
            db.add(doc_user)
            db.commit()
            db.refresh(doc_user)

            # Create doctor profile
            import json

            default_hours = {
                "Monday": {"start": "09:00", "end": "17:00"},
                "Tuesday": {"start": "09:00", "end": "17:00"},
                "Wednesday": {"start": "09:00", "end": "17:00"},
                "Thursday": {"start": "09:00", "end": "17:00"},
                "Friday": {"start": "09:00", "end": "17:00"},
            }
            profile = DoctorProfile(
                user_id=doc_user.id,
                specialisation="Diagnostic Medicine",
                working_hours=json.dumps(default_hours),
                slot_duration=30,
                leave_days="[]",
                bio="Head of Diagnostic Medicine at Princeton-Plainsboro Teaching Hospital. Specialises in cardiology, nephrology, and infectious diseases.",
            )
            db.add(profile)
            db.commit()
            logger.info("Doctor user seeded: doctor@clinic.com / doctorpassword123")

        # Create default Patient
        patient_email = "patient@clinic.com"
        patient_user = db.query(User).filter(User.email == patient_email).first()
        if not patient_user:
            patient_user = User(
                email=patient_email,
                password_hash=get_password_hash("patientpassword123"),
                full_name="Arthur Dent",
                role="patient",
            )
            db.add(patient_user)
            db.commit()
            logger.info("Patient user seeded: patient@clinic.com / patientpassword123")

    except Exception as e:
        logger.error(f"Error seeding database: {e}")
    finally:
        db.close()


seed_database()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background jobs loop
    bg_task = asyncio.create_task(start_background_jobs())
    logger.info("Background jobs worker started in lifespan.")
    yield
    # Shutdown: Cancel background jobs loop
    bg_task.cancel()
    try:
        await bg_task
    except asyncio.CancelledError:
        logger.info("Background jobs worker cancelled successfully.")


app = FastAPI(
    title="Healthcare Appointment & Follow-up Manager API",
    description="API for managing clinic schedules, appointments, LLM-summaries, and medication tracking.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(doctor.router)
app.include_router(patient.router)
app.include_router(calendar.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to Healthcare Appointment & Follow-up Manager API"}
