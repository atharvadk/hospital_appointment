import datetime
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth import get_patient
from backend.calendar_service import create_calendar_event
from backend.database import get_db
from backend.jobs import add_email_to_queue
from backend.llm import generate_pre_visit_summary
from backend.models import (
    Appointment,
    DoctorProfile,
    MedicationReminder,
    SlotHold,
    User,
)
from backend.schemas import (
    AppointmentCreate,
    AppointmentResponse,
    DoctorResponse,
    SlotHoldCreate,
    SlotHoldResponse,
)

router = APIRouter(prefix="/api/patient", tags=["patient"])


@router.get("/doctors", response_model=list[DoctorResponse])
def search_doctors(
    specialisation: str | None = None,
    db: Session = Depends(get_db),
    current_patient: User = Depends(get_patient),
):
    query = db.query(DoctorProfile)
    if specialisation:
        query = query.filter(DoctorProfile.specialisation.ilike(f"%{specialisation}%"))
    profiles = query.all()

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


@router.get("/doctors/{id}/slots")
def get_slots(
    id: int,
    date: str,
    db: Session = Depends(get_db),
    current_patient: User = Depends(get_patient),
):
    """
    Generates slot availability for a specific doctor and date.
    Format of date is YYYY-MM-DD
    """
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    leave_days = json.loads(profile.leave_days)
    if date in leave_days:
        return []

    try:
        dt = datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
        )

    day_name = dt.strftime("%A")
    working_hours = json.loads(profile.working_hours)
    if day_name not in working_hours:
        return []

    day_config = working_hours[day_name]
    start_str = day_config.get("start")
    end_str = day_config.get("end")
    if not start_str or not end_str:
        return []

    # Generate times based on slot duration
    start_time = datetime.datetime.strptime(start_str, "%H:%M").time()
    end_time = datetime.datetime.strptime(end_str, "%H:%M").time()

    slots = []
    curr_dt = datetime.datetime.combine(dt.date(), start_time)
    end_dt = datetime.datetime.combine(dt.date(), end_time)

    slot_dur = profile.slot_duration
    while curr_dt + datetime.timedelta(minutes=slot_dur) <= end_dt:
        slot_start = curr_dt.strftime("%H:%M")
        curr_dt += datetime.timedelta(minutes=slot_dur)
        slot_end = curr_dt.strftime("%H:%M")
        slots.append({"start": slot_start, "end": slot_end})

    # Fetch booked appointments for the doctor
    booked = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == id,
            Appointment.date == date,
            Appointment.status == "booked",
        )
        .all()
    )
    booked_starts = {b.start_time for b in booked}

    # Fetch active locks (slot holds)
    now = datetime.datetime.utcnow()
    holds = (
        db.query(SlotHold)
        .filter(
            SlotHold.doctor_id == id, SlotHold.date == date, SlotHold.locked_until > now
        )
        .all()
    )
    held_slots = {h.start_time: h for h in holds}

    results = []
    for slot in slots:
        status_val = "available"
        held_by = None
        locked_until = None

        if slot["start"] in booked_starts:
            status_val = "booked"
        elif slot["start"] in held_slots:
            status_val = "held"
            held_by = held_slots[slot["start"]].patient_id
            locked_until = held_slots[slot["start"]].locked_until

        results.append(
            {
                "start_time": slot["start"],
                "end_time": slot["end"],
                "status": status_val,
                "held_by": held_by,
                "locked_until": locked_until,
            }
        )

    return results


@router.post("/slots/hold", response_model=SlotHoldResponse)
def hold_slot(
    req: SlotHoldCreate,
    db: Session = Depends(get_db),
    current_patient: User = Depends(get_patient),
):
    """
    Lock a slot for 5 minutes to prevent double booking.
    """
    now = datetime.datetime.utcnow()

    # 1. Check if already booked
    booked_exists = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == req.doctor_id,
            Appointment.date == req.date,
            Appointment.start_time == req.start_time,
            Appointment.status == "booked",
        )
        .first()
    )

    if booked_exists:
        raise HTTPException(status_code=409, detail="This slot is already booked")

    # 2. Check if locked by another user
    active_hold = (
        db.query(SlotHold)
        .filter(
            SlotHold.doctor_id == req.doctor_id,
            SlotHold.date == req.date,
            SlotHold.start_time == req.start_time,
            SlotHold.locked_until > now,
        )
        .first()
    )

    if active_hold:
        if active_hold.patient_id == current_patient.id:
            # Refresh lock
            active_hold.locked_until = now + datetime.timedelta(minutes=5)
            db.commit()
            db.refresh(active_hold)
            return active_hold
        else:
            raise HTTPException(
                status_code=409, detail="This slot is currently held by another user"
            )

    # Clean up any expired lock of current user on this slot or any other slot to avoid duplicates
    db.query(SlotHold).filter(SlotHold.locked_until <= now).delete()

    # 3. Create new lock
    lock = SlotHold(
        doctor_id=req.doctor_id,
        date=req.date,
        start_time=req.start_time,
        end_time=req.end_time,
        patient_id=current_patient.id,
        locked_until=now + datetime.timedelta(minutes=5),
    )

    try:
        db.add(lock)
        db.commit()
        db.refresh(lock)
        return lock
    except IntegrityError:
        db.rollback()
        # Handle concurrent insertion race condition
        raise HTTPException(
            status_code=409, detail="This slot was locked by another user concurrently"
        )


@router.post("/appointments", response_model=AppointmentResponse)
def book_appointment(
    req: AppointmentCreate,
    db: Session = Depends(get_db),
    current_patient: User = Depends(get_patient),
):
    """
    Confirm appointment and book the slot.
    """
    now = datetime.datetime.utcnow()

    # 1. Double check booking
    booked_exists = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == req.doctor_id,
            Appointment.date == req.date,
            Appointment.start_time == req.start_time,
            Appointment.status == "booked",
        )
        .first()
    )

    if booked_exists:
        raise HTTPException(status_code=409, detail="This slot is already booked")

    # 2. Check if held by another patient
    active_hold = (
        db.query(SlotHold)
        .filter(
            SlotHold.doctor_id == req.doctor_id,
            SlotHold.date == req.date,
            SlotHold.start_time == req.start_time,
            SlotHold.locked_until > now,
        )
        .first()
    )

    if active_hold and active_hold.patient_id != current_patient.id:
        raise HTTPException(
            status_code=409, detail="This slot is locked by another user"
        )

    # 3. LLM Pre-visit summary generation
    pre_visit = generate_pre_visit_summary(req.symptoms)

    # 4. Create appointment
    appt = Appointment(
        doctor_id=req.doctor_id,
        patient_id=current_patient.id,
        date=req.date,
        start_time=req.start_time,
        end_time=req.end_time,
        status="booked",
        symptoms=req.symptoms,
        pre_visit_urgency=pre_visit.get("urgency", "Medium"),
        pre_visit_complaint=pre_visit.get("chief_complaint", req.symptoms),
        pre_visit_questions=json.dumps(pre_visit.get("questions", [])),
    )

    db.add(appt)

    # Remove slot holds for this slot
    if active_hold:
        db.delete(active_hold)

    db.commit()
    db.refresh(appt)

    # 5. Fetch doctor details for notifications
    doctor = db.query(User).filter(User.id == req.doctor_id).first()

    # 6. Create Google Calendar Event
    event_id = create_calendar_event(db, appt)
    if event_id:
        appt.google_event_id = event_id
        db.commit()

    # 7. Notify patient & doctor via email queue
    subj_patient = f"Appointment Confirmed: Dr. {doctor.full_name}"
    body_patient = (
        f"Hello {current_patient.full_name},\n\n"
        f"Your appointment has been booked successfully!\n"
        f"- Doctor: Dr. {doctor.full_name}\n"
        f"- Date: {appt.date}\n"
        f"- Time: {appt.start_time} - {appt.end_time}\n\n"
        f"A Google Calendar event has been created for your schedule.\n\n"
        f"Best regards,\nClinic Team"
    )
    add_email_to_queue(db, current_patient.email, subj_patient, body_patient)

    subj_doctor = f"New Booking: {current_patient.full_name}"
    body_doctor = (
        f"Hello Dr. {doctor.full_name},\n\n"
        f"A patient has booked an appointment with you:\n"
        f"- Patient: {current_patient.full_name}\n"
        f"- Date: {appt.date}\n"
        f"- Time: {appt.start_time} - {appt.end_time}\n"
        f"- Urgency Level: {appt.pre_visit_urgency}\n"
        f"- Chief Complaint: {appt.pre_visit_complaint}\n\n"
        f"Please view the portal for more details.\n\n"
        f"Best regards,\nClinic System"
    )
    add_email_to_queue(db, doctor.email, subj_doctor, body_doctor)

    return AppointmentResponse(
        id=appt.id,
        doctor_id=appt.doctor_id,
        doctor_name=doctor.full_name,
        patient_id=appt.patient_id,
        patient_name=current_patient.full_name,
        date=appt.date,
        start_time=appt.start_time,
        end_time=appt.end_time,
        status=appt.status,
        symptoms=appt.symptoms,
        pre_visit_urgency=appt.pre_visit_urgency,
        pre_visit_complaint=appt.pre_visit_complaint,
        pre_visit_questions=json.loads(appt.pre_visit_questions),
        google_event_id=appt.google_event_id,
        created_at=appt.created_at,
    )


@router.get("/appointments", response_model=list[AppointmentResponse])
def get_patient_appointments(
    db: Session = Depends(get_db), current_patient: User = Depends(get_patient)
):
    appts = (
        db.query(Appointment)
        .filter(Appointment.patient_id == current_patient.id)
        .order_by(Appointment.date.desc(), Appointment.start_time.desc())
        .all()
    )
    results = []
    for appt in appts:
        results.append(
            AppointmentResponse(
                id=appt.id,
                doctor_id=appt.doctor_id,
                doctor_name=appt.doctor.full_name,
                patient_id=appt.patient_id,
                patient_name=current_patient.full_name,
                date=appt.date,
                start_time=appt.start_time,
                end_time=appt.end_time,
                status=appt.status,
                symptoms=appt.symptoms,
                pre_visit_urgency=appt.pre_visit_urgency,
                pre_visit_complaint=appt.pre_visit_complaint,
                pre_visit_questions=json.loads(appt.pre_visit_questions or "[]"),
                clinical_notes=appt.clinical_notes,
                prescription=appt.prescription,
                post_visit_summary=appt.post_visit_summary,
                google_event_id=appt.google_event_id,
                created_at=appt.created_at,
            )
        )
    return results


@router.get("/reminders")
def get_reminders(
    db: Session = Depends(get_db), current_patient: User = Depends(get_patient)
):
    rems = (
        db.query(MedicationReminder)
        .filter(
            MedicationReminder.patient_id == current_patient.id,
            MedicationReminder.status == "active",
        )
        .all()
    )
    return rems
