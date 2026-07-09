# Architecture

## Purpose and boundary

SmartHealth is a privacy-oriented educational health-support and care-navigation platform. It is deliberately **not** an electronic health record, medical device, clinical decision system, or real payment processor. Automated rules produce explainable educational guidance and must never be represented as a diagnosis.

## Runtime topology

```text
Browser over TLS
      │
Reverse proxy / load balancer
      │
Gunicorn WSGI workers ───── Redis rate-limit state
      │
PostgreSQL transactions ─── Private object/file storage
```

The Flask development server and SQLite are limited to local development. Production configuration refuses SQLite and a short/missing secret.

## Application layers

- `healthcare/__init__.py`: app factory, extensions, security headers, errors, CLI.
- `healthcare/models.py`: normalized data model and constrained status enums.
- `healthcare/services.py`: transaction boundaries, slot locking, query services, and private file validation.
- `healthcare/security.py`: role checks, ownership helpers, input normalization, and audit events.
- `healthcare/auth.py`: Argon2 accounts, lockout, session lifecycle, profiles, and consent capture.
- `healthcare/routes.py`: public and patient-owned workflows.
- `healthcare/staff.py`: doctor-scoped and administrator-scoped operations.
- `utils/`: isolated explainable analysis rules.

## Trust boundaries

1. Browser input is untrusted, including filenames, MIME headers, query strings, and hidden fields.
2. The reverse proxy is trusted only when `TRUST_PROXY_HEADERS=true` and must be the sole upstream.
3. PostgreSQL is the source of truth. ORM sessions are request-scoped.
4. Uploaded files are untrusted even after validation. They live outside the web root and are retrieved through ownership-checked handlers.
5. Bot output is untrusted educational content and is visually/structurally distinct from clinician messages.

## Scheduling concurrency

`appointment_slots` has a unique hospital/doctor/date/time identity and a capacity check constraint. Booking locks that aggregate row with `SELECT ... FOR UPDATE` under PostgreSQL, verifies `booked_count < capacity`, increments it, and creates the appointment/payment in the same transaction. Cancellation locks the same row and decrements capacity in the same transaction. A nested savepoint handles two requests racing to create the first aggregate row.

SQLite does not provide the same row-lock semantics and is therefore development-only.

## Healthcare interoperability direction

The internal model is intentionally mapped toward HL7 FHIR concepts:

- `User` + `PatientProfile` → Patient/Practitioner identity boundary
- `Hospital` + `Department` → Organization/HealthcareService
- `Appointment` + `AppointmentSlot` → Appointment/Schedule/Slot
- `ConsentRecord` → Consent
- `AuditEvent` → AuditEvent
- `ReportAnalysis` → DiagnosticReport/DocumentReference extension boundary
- `Conversation` + `Message` → Communication

This project does not claim FHIR conformance. A production interoperability API requires implementation-guide selection, terminology bindings, resource validation, OAuth/SMART authorization, provenance, and conformance testing.

## Official design references

- [Flask production deployment](https://flask.palletsprojects.com/en/stable/deploying/)
- [SQLAlchemy session and transaction guidance](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)
- [OWASP authorization guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [OWASP secure file upload guidance](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
- [HL7 FHIR security and audit guidance](https://hl7.org/fhir/security.html)
- [HL7 FHIR Appointment](https://www.hl7.org/fhir/appointment.html)
