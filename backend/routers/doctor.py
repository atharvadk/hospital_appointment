import datetime
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth import get_doctor
from backend.calendar_service import update_calendar_event
from backend.database import get_db
from backend.jobs import add_email_to_queue
from backend.llm import generate_post_visit_summary, parse_prescription_for_reminders
from backend.models import Appointment, MedicationReminder, User
from backend.schemas import AppointmentResponse, PostVisitSubmit

router = APIRouter(prefix="/api/doctor", tags=["doctor"])


@router.get("/appointments", response_model=list[AppointmentResponse])
def get_doctor_appointments(
    db: Session = Depends(get_db), current_doctor: User = Depends(get_doctor)
):
    appts = (
        db.query(Appointment)
        .filter(Appointment.doctor_id == current_doctor.id)
        .order_by(Appointment.date.desc(), Appointment.start_time.desc())
        .all()
    )
    results = []
    for appt in appts:
        results.append(
            AppointmentResponse(
                id=appt.id,
                doctor_id=appt.doctor_id,
                doctor_name=current_doctor.full_name,
                patient_id=appt.patient_id,
                patient_name=appt.patient.full_name,
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


@router.post("/appointments/{id}/post-visit", response_model=AppointmentResponse)
def submit_post_visit(
    id: int,
    req: PostVisitSubmit,
    db: Session = Depends(get_db),
    current_doctor: User = Depends(get_doctor),
):
    # 1. Fetch appointment
    appt = (
        db.query(Appointment)
        .filter(Appointment.id == id, Appointment.doctor_id == current_doctor.id)
        .first()
    )

    if not appt:
        raise HTTPException(
            status_code=404, detail="Appointment not found or not assigned to you"
        )

    if appt.status != "booked":
        raise HTTPException(
            status_code=400,
            detail="Cannot add notes to a cancelled or already completed appointment",
        )

    # 2. Update status and clinical info
    appt.clinical_notes = req.clinical_notes
    appt.prescription = req.prescription
    appt.status = "completed"

    # 3. Generate patient-friendly post-visit summary using LLM
    summary_text = generate_post_visit_summary(req.clinical_notes)
    appt.post_visit_summary = summary_text

    # 4. Parse prescription for reminders and add to db
    parsed_reminders = parse_prescription_for_reminders(req.prescription)

    # Delete any existing reminders for this appointment first
    db.query(MedicationReminder).filter(
        MedicationReminder.appointment_id == appt.id
    ).delete()

    now = datetime.datetime.utcnow()
    reminders_added = []
    for item in parsed_reminders:
        reminder = MedicationReminder(
            appointment_id=appt.id,
            patient_id=appt.patient_id,
            medication_name=item["medication_name"],
            dosage=item["dosage"],
            frequency_hours=item["frequency_hours"],
            last_sent_at=None,
            next_due_at=now + datetime.timedelta(hours=item["frequency_hours"]),
            status="active",
        )
        db.add(reminder)
        reminders_added.append(reminder)

    db.commit()
    db.refresh(appt)

    # 5. Notify patient via email queue
    med_list_str = "\n".join(
        [
            f"- {r.medication_name}: {r.dosage} (every {r.frequency_hours} hours)"
            for r in reminders_added
        ]
    )
    subject = f"Your Post-visit Summary & Prescription - Dr. {current_doctor.full_name}"
    body = (
        f"Hello {appt.patient.full_name},\n\n"
        f"Your appointment with Dr. {current_doctor.full_name} on {appt.date} is complete.\n\n"
        f"--- Patient Friendly Summary ---\n"
        f"{summary_text}\n\n"
        f"--- Prescribed Medications ---\n"
        f"{med_list_str if med_list_str else 'No medications prescribed.'}\n\n"
        f"You will receive automatic email reminders when it is time to take each medication.\n\n"
        f"Take care,\nClinic Team"
    )
    add_email_to_queue(db, appt.patient.email, subject, body)

    # 6. Update Google Calendar event details
    update_calendar_event(db, appt)

    return AppointmentResponse(
        id=appt.id,
        doctor_id=appt.doctor_id,
        doctor_name=current_doctor.full_name,
        patient_id=appt.patient_id,
        patient_name=appt.patient.full_name,
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
