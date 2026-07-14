import datetime
import logging
import os

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from backend.models import Appointment, OAuthToken

logger = logging.getLogger(__name__)

# Google OAuth Configuration
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/calendar/callback"
)

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def get_google_flow(state: str | None = None) -> Flow:
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET is not configured.")

    client_config = {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }

    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        state=state,
        autogenerate_code_verifier=False,
    )
    flow.redirect_uri = REDIRECT_URI
    return flow


def save_oauth_token(db: Session, user_id: int, credentials) -> OAuthToken:
    token_record = db.query(OAuthToken).filter(OAuthToken.user_id == user_id).first()

    expires_at = (
        datetime.datetime.utcnow()
        + datetime.timedelta(
            seconds=credentials.expiry.timestamp()
            - datetime.datetime.now(datetime.timezone.utc).timestamp()
        )
        if credentials.expiry
        else datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    )

    if not token_record:
        token_record = OAuthToken(
            user_id=user_id,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expires_at=expires_at,
        )
        db.add(token_record)
    else:
        token_record.access_token = credentials.token
        if credentials.refresh_token:
            token_record.refresh_token = credentials.refresh_token
        token_record.expires_at = expires_at

    db.commit()
    db.refresh(token_record)
    return token_record


def get_user_credentials(db: Session, user_id: int):
    token_record = db.query(OAuthToken).filter(OAuthToken.user_id == user_id).first()
    if not token_record:
        return None

    creds = Credentials(
        token=token_record.access_token,
        refresh_token=token_record.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )

    # Check if expired
    if token_record.expires_at < datetime.datetime.utcnow() and creds.refresh_token:
        try:
            from google.auth.transport.requests import Request

            creds.refresh(Request())
            # Save new token
            token_record.access_token = creds.token
            token_record.expires_at = datetime.datetime.utcnow() + datetime.timedelta(
                hours=1
            )
            db.commit()
        except Exception as e:
            logger.error(f"Failed to refresh Google Token for user {user_id}: {e}")
            return None

    return creds


def create_calendar_event(db: Session, appointment: Appointment) -> str:
    """
    Creates a Google Calendar event for both patient and doctor if tokens are available.
    Returns the google event ID if successful (or mock event ID if mock mode).
    """
    logger.info(f"Attempting to create Calendar Event for Appointment {appointment.id}")

    # Check if either user is authenticated
    creds = get_user_credentials(db, appointment.doctor_id)
    if not creds:
        creds = get_user_credentials(db, appointment.patient_id)

    # If still no credentials, run in mock mode
    if not creds:
        mock_id = (
            f"mock-event-{appointment.id}-{int(datetime.datetime.utcnow().timestamp())}"
        )
        logger.info(
            f"Google Calendar Mock Mode: Created event {mock_id} (No OAuth credentials stored)"
        )
        return mock_id

    try:
        service = build("calendar", "v3", credentials=creds)

        # Prepare event details
        start_dt = f"{appointment.date}T{appointment.start_time}:00"
        end_dt = f"{appointment.date}T{appointment.end_time}:00"

        event_body = {
            "summary": f"Doctor Appointment: {appointment.patient.full_name} & Dr. {appointment.doctor.full_name}",
            "description": (
                f"Appointment scheduled.\n"
                f"Symptoms: {appointment.symptoms or 'None declared'}\n"
                f"Urgency: {appointment.pre_visit_urgency or 'Not analysed'}"
            ),
            "start": {"dateTime": start_dt, "timeZone": "UTC"},
            "end": {"dateTime": end_dt, "timeZone": "UTC"},
            "attendees": [
                {"email": appointment.patient.email},
                {"email": appointment.doctor.email},
            ],
        }

        event = service.events().insert(calendarId="primary", body=event_body).execute()
        return event.get("id")
    except Exception as e:
        logger.error(f"Failed to create Google Calendar event: {e}")
        # Return a fallback mock ID to prevent system crashes
        return f"fallback-event-{appointment.id}"


def update_calendar_event(db: Session, appointment: Appointment) -> bool:
    """
    Updates the Google Calendar event details.
    """
    if not appointment.google_event_id:
        return False

    if appointment.google_event_id.startswith(
        "mock-"
    ) or appointment.google_event_id.startswith("fallback-"):
        logger.info(
            f"Google Calendar Mock Mode: Updated event {appointment.google_event_id}"
        )
        return True

    creds = get_user_credentials(db, appointment.doctor_id) or get_user_credentials(
        db, appointment.patient_id
    )
    if not creds:
        logger.info(
            f"Google Calendar Mock Mode: Stored credentials unavailable, logged update for {appointment.google_event_id}"
        )
        return True

    try:
        service = build("calendar", "v3", credentials=creds)

        start_dt = f"{appointment.date}T{appointment.start_time}:00"
        end_dt = f"{appointment.date}T{appointment.end_time}:00"

        event_body = {
            "summary": f"Doctor Appointment: {appointment.patient.full_name} & Dr. {appointment.doctor.full_name}",
            "description": (
                f"Appointment status: {appointment.status}\n"
                f"Symptoms: {appointment.symptoms or 'None declared'}\n"
                f"Urgency: {appointment.pre_visit_urgency or 'Not analysed'}\n\n"
                f"Post-visit Summary:\n{appointment.post_visit_summary or 'Pending'}"
            ),
            "start": {"dateTime": start_dt, "timeZone": "UTC"},
            "end": {"dateTime": end_dt, "timeZone": "UTC"},
            "attendees": [
                {"email": appointment.patient.email},
                {"email": appointment.doctor.email},
            ],
        }

        service.events().update(
            calendarId="primary", eventId=appointment.google_event_id, body=event_body
        ).execute()
        return True
    except Exception as e:
        logger.error(
            f"Failed to update Google Calendar event {appointment.google_event_id}: {e}"
        )
        return False


def delete_calendar_event(db: Session, appointment: Appointment) -> bool:
    """
    Deletes the Google Calendar event.
    """
    if not appointment.google_event_id:
        return False

    if appointment.google_event_id.startswith(
        "mock-"
    ) or appointment.google_event_id.startswith("fallback-"):
        logger.info(
            f"Google Calendar Mock Mode: Deleted event {appointment.google_event_id}"
        )
        return True

    creds = get_user_credentials(db, appointment.doctor_id) or get_user_credentials(
        db, appointment.patient_id
    )
    if not creds:
        logger.info(
            f"Google Calendar Mock Mode: Credentials unavailable, logged delete for {appointment.google_event_id}"
        )
        return True

    try:
        service = build("calendar", "v3", credentials=creds)
        service.events().delete(
            calendarId="primary", eventId=appointment.google_event_id
        ).execute()
        return True
    except Exception as e:
        logger.error(
            f"Failed to delete Google Calendar event {appointment.google_event_id}: {e}"
        )
        return False
