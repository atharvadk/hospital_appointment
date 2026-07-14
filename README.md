# Aegis Health Manager

Aegis Health Manager is a premium clinic appointment scheduling and patient follow-up platform. It features role-based access portals (Patient, Doctor, Admin), AI-powered symptom analysis and post-visit summaries, secure concurrency control to prevent double-booking, and Google Calendar sync.

---

## Features

- **Role-based Authentication**: Dashboards tailored for Patients, Doctors, and Administrators.
- **Symptom Screening (AI)**: Generates pre-visit chief complaints, urgency levels (Low/Medium/High), and screening questions for the doctor before the appointment.
- **Consultation summaries (AI)**: Converts doctor's clinical notes into a patient-friendly summary, extracting medication schedules.
- **Automatic Medication Reminders**: Sets background reminders matching prescription frequency and alerts patients via email.
- **Google Calendar Sync**: Integrates OAuth 2.0 to sync appointments (create, update, cancel events) directly to the calendar.
- **Double-booking Prevention**: Employs short-lived slot locks (holds) and DB unique constraints to ensure slot booking integrity.
- **Outbox Pattern Email Queue**: Decoupled email sender worker with auto-retry on failure.

---

## DB Schema Design

The application uses SQLite with SQLAlchemy. The tables are configured as follows:

```
  ┌──────────────┐          ┌───────────────────┐
  │    users     │◀─────────│  doctor_profiles  │
  │ (Patient/Dr/ │          │ (Hours, Leaves,   │
  │    Admin)    │          │  Duration, Bio)   │
  └──────────────┘          └───────────────────┘
          ▲
          │                 ┌───────────────────┐
          ├─────────────────│   appointments    │
          │                 │ (Symptoms, Notes, │
          │                 │  Summaries, status)
          │                 └───────────────────┘
          │                           ▲
          │                           │
  ┌──────────────┐          ┌───────────────────┐
  │ oauth_tokens │          │medication_remindrs│
  │ (Google Cred │          │ (Dosage, NextDue) │
  └──────────────┘          └───────────────────┘
```

1. **`users`**: Auth credentials, profile names, and roles (`patient`, `doctor`, `admin`).
2. **`doctor_profiles`**: Linked to users; stores specialisation, JSON working hours, leave days list, slot duration, and bio.
3. **`appointments`**: Records doctor, patient, date/time, status, symptoms, LLM pre-visit summaries (urgency, complaints, questions), post-visit notes, prescriptions, LLM friendly summaries, and Google Calendar event IDs.
4. **`slot_holds`**: Temporary 5-minute locks containing doctor, date, start_time, patient, and expiration.
5. **`medication_reminders`**: Tracks patient prescriptions, dosages, hourly intervals, last sent dates, and next due timestamps.
6. **`email_queue`**: Transformed notifications to be sent asynchronously, tracking retry counts and logs.
7. **`oauth_tokens`**: Stores Google Calendar refresh and access tokens per user.

---

## AI Prompt Engineering

### 1. Pre-visit Symptom Analysis
```
Analyse these symptoms and return: urgency level (Low / Medium / High), chief complaint, and three suggested questions for the doctor. Symptoms: <symptoms>
```
*Configured to output structured JSON for direct DB population.*

### 2. Post-visit Patient-Friendly Summary
```
Convert these clinical notes into a patient-friendly summary with medication schedule and follow-up steps. Notes: <notes>
```

---

## Setup & Running Guide

### Prerequisites
- Python 3.10+
- Node.js 18+

### Setup Environment Variables
1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and fill in your details (especially `GEMINI_API_KEY` for LLM capabilities).

### Running the Backend
1. Activate the Python virtual environment:
   ```bash
   source .venv/bin/activate
   ```
2. Install Python packages (already done in workspace, but for reference):
   ```bash
   pip install -r backend/requirements.txt
   # Or directly:
   pip install fastapi uvicorn sqlalchemy pydantic python-jose[cryptography] passlib[bcrypt] python-multipart google-generativeai google-auth google-auth-oauthlib google-api-python-client
   ```
3. Start the FastAPI development server:
   ```bash
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   *The backend will seed test accounts on startup and run background workers automatically.*

### Running the Frontend
1. Open a new terminal.
2. Navigate to the frontend directory and install dependencies:
   ```bash
   cd frontend
   npm install
   ```
3. Start the Vite dev server:
   ```bash
   npm run dev
   ```
4. Access the web interface at: `http://localhost:5173`.

---

## Test Accounts

For grading and testing convenience, the database is pre-seeded with the following accounts:
- **Patient**: `patient@clinic.com` / `patientpassword123`
- **Doctor**: `doctor@clinic.com` / `doctorpassword123`
- **Administrator**: `admin@clinic.com` / `adminpassword123`

---

## Google Cloud Console & Calendar Setup

To connect to Google Calendar:
1. Create a project in [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the **Google Calendar API**.
3. Set up **OAuth Consent Screen**:
   - User Type: External / Testing.
   - Add scope: `.../auth/calendar.events` (Manage events).
   - Add test user emails.
4. Generate **OAuth 2.0 Credentials**:
   - Application type: Web application.
   - Authorized redirect URI: `http://localhost:8000/api/calendar/callback`.
5. Save the generated `Client ID` and `Client Secret` to your `.env` file.
