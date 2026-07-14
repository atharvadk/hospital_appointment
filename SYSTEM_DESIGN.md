# System Design Write-up: Aegis Health Manager

This document explains the core architectural and concurrency patterns implemented in the Aegis Health Manager to ensure schedule integrity, handle slot holds, process doctor leaves, and guarantee notification delivery.

---

## 1. Concurrency & Double-Booking Prevention

Double-booking represents a classic race condition where two patients attempt to book the same time slot simultaneously. To prevent this, Aegis Health Manager utilizes a multi-layered verification strategy:

1. **Transactional Validation**: When a booking request is processed, the backend queries the database for any existing active appointments for the specified `doctor_id`, `date`, and `start_time` within a transaction.
2. **Unique Constraints**: At the database schema level, a unique index is applied across the `doctor_id`, `date`, and `start_time` fields in the `slot_holds` table:
   ```python
   UniqueConstraint("doctor_id", "date", "start_time", name="_doctor_slot_hold_uc")
   ```
   If two concurrent requests attempt to insert or secure a lock on the exact same slot, the database engine raises an `IntegrityError` on the second transaction, which is caught by the backend and returned as a HTTP 409 Conflict.

---

## 2. Slot Hold Mechanism

Before confirming an appointment, patients must write down symptoms, which takes time. To prevent other users from snatching the slot during checkout, a **Slot Hold Mechanism** is used:

```mermaid
sequenceFlow
Patient->>Backend: Hold Slot (Doctor ID, Date, Time)
Backend->>DB: Check active appointments / active locks
Note right of DB: If free, insert lock (Expires in 5 min)
Backend-->>Patient: Lock Confirmed & Start 5-min Countdown
Patient->>Backend: Submit symptoms & Confirm Booking
Backend->>DB: Save Appointment & Release Lock
```

- **Temporary Holds**: The `slot_holds` table stores the `patient_id` and a `locked_until` timestamp set to `now + 5 minutes`.
- **Validation**: While a lock is active, the slot's status is returned as `"held"`. Only the patient who owns the lock can proceed with booking. Other patients are blocked.
- **Garbage Collection**: A lightweight asynchronous loop running in the background periodically sweeps and deletes expired locks:
  ```python
  expired = db.query(SlotHold).filter(SlotHold.locked_until < now).all()
  db.delete(expired)
  ```

---

## 3. Doctor Leave Conflict Handling

When a doctor is marked on leave by an administrator, the schedule must resolve active bookings:

1. **Leave Registration**: The date is appended to the doctor's profile `leave_days` list.
2. **Conflict Detection**: The system queries the `appointments` table for any booked sessions on that specific date:
   ```python
   db.query(Appointment).filter(Appointment.doctor_id == doc_id, Appointment.date == leave_date, Appointment.status == "booked").all()
   ```
3. **Cascading Cancellation**: Affected appointments are set to `cancelled`.
4. **Google Calendar Cleanup**: The backend initiates Google Calendar API calls using stored OAuth tokens to delete the corresponding events via their stored `google_event_id`.
5. **Immediate Notification**: Cancellation emails explaining the leave are compiled and pushed to the `email_queue`.

---

## 4. Notification Failure Handling

Network requests to external email APIs (SMTP, SendGrid, etc.) can fail due to rate limits or temporary internet dropouts. To ensure reliability, Aegis Health Manager implements the **Transactional Outbox Pattern**:

- **Decoupled Queueing**: Email notifications are never sent synchronously during request handling. Instead, they are written to the `email_queue` table as part of the database transaction.
- **Asynchronous Processing**: An async worker runs every 10 seconds, fetching records where `status = "pending"` or `status = "failed"` and `retry_count < 3`.
- **Automatic Retry**: If a delivery fails, the worker logs the error message in the `last_error` field, increments `retry_count`, and marks it as `failed` for the next sweep.
- **Graceful Fallbacks**: If the SMTP server is completely unreachable, the application logs the compiled emails to the console, ensuring that local developer environments and evaluations are never blocked by email delivery issues.
