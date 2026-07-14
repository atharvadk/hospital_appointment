import asyncio
import datetime
import logging
import os
import smtplib
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import EmailQueue, MedicationReminder, SlotHold, User

logger = logging.getLogger(__name__)

# SMTP Configuration (optional, falls back to logging mock delivery)
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "notifications@clinicmanager.com")


def send_smtp_email(recipient: str, subject: str, body: str) -> bool:
    """
    Tries to send an email via SMTP. If credentials are not configured,
    it logs the email to local logs (simulating successful delivery).
    """
    if not SMTP_HOST or not SMTP_USER:
        # Mock mode
        logger.info(
            f"\n--- MOCK EMAIL SENT ---\nTo: {recipient}\nSubject: {subject}\nBody: {body}\n------------------------"
        )
        return True

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = recipient

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"SMTP Error: {e}")
        return False


def add_email_to_queue(
    db: Session, recipient: str, subject: str, body: str
) -> EmailQueue:
    email = EmailQueue(
        recipient=recipient, subject=subject, body=body, status="pending"
    )
    db.add(email)
    db.commit()
    db.refresh(email)
    return email


async def process_email_queue():
    """
    Background job to send pending and retry failed emails.
    """
    db = SessionLocal()
    try:
        # Get emails that are pending or failed and have fewer than 3 retries
        emails = (
            db.query(EmailQueue)
            .filter(
                EmailQueue.status.in_(["pending", "failed"]), EmailQueue.retry_count < 3
            )
            .all()
        )

        for email in emails:
            logger.info(f"Processing queued email ID {email.id} to {email.recipient}")
            success = send_smtp_email(email.recipient, email.subject, email.body)

            if success:
                email.status = "sent"
                email.processed_at = datetime.datetime.utcnow()
            else:
                email.retry_count += 1
                email.status = "failed"
                email.last_error = f"Failed to send email. Attempt {email.retry_count}."

            db.commit()
    except Exception as e:
        logger.error(f"Error processing email queue: {e}")
    finally:
        db.close()


async def release_expired_slot_holds():
    """
    Removes slot holds that have expired.
    """
    db = SessionLocal()
    try:
        now = datetime.datetime.utcnow()
        expired = db.query(SlotHold).filter(SlotHold.locked_until < now).all()
        if expired:
            logger.info(f"Releasing {len(expired)} expired slot holds")
            for hold in expired:
                db.delete(hold)
            db.commit()
    except Exception as e:
        logger.error(f"Error releasing expired slot holds: {e}")
    finally:
        db.close()


async def process_medication_reminders():
    """
    Triggers medication reminders and schedules the next ones.
    """
    db = SessionLocal()
    try:
        now = datetime.datetime.utcnow()
        reminders = (
            db.query(MedicationReminder)
            .filter(
                MedicationReminder.status == "active",
                MedicationReminder.next_due_at <= now,
            )
            .all()
        )

        for rem in reminders:
            patient = db.query(User).filter(User.id == rem.patient_id).first()
            if patient:
                subject = f"Medication Reminder: {rem.medication_name}"
                body = (
                    f"Hello {patient.full_name},\n\n"
                    f"This is a friendly reminder to take your medication:\n"
                    f"- Medication: {rem.medication_name}\n"
                    f"- Dosage: {rem.dosage}\n\n"
                    f"Please keep healthy!\n\n"
                    f"Warm regards,\nClinic Team"
                )
                logger.info(
                    f"Medication reminder triggered for Patient {patient.full_name} ({patient.email})"
                )

                # Enqueue the reminder email
                add_email_to_queue(db, patient.email, subject, body)

                # Update reminder intervals
                rem.last_sent_at = now
                rem.next_due_at = now + datetime.timedelta(hours=rem.frequency_hours)

            db.commit()
    except Exception as e:
        logger.error(f"Error processing medication reminders: {e}")
    finally:
        db.close()


async def start_background_jobs():
    """
    Infinite loop running background jobs every 10 seconds.
    """
    logger.info("Background jobs worker started.")
    while True:
        try:
            await process_email_queue()
            await release_expired_slot_holds()
            await process_medication_reminders()
        except Exception as e:
            logger.error(f"Background jobs worker loop error: {e}")
        await asyncio.sleep(10)
