# Smart Health Management Platform

A production-oriented Flask health-support platform with private patient accounts, role-scoped doctor/admin operations, educational report/symptom/photo analysis, care discovery, transaction-safe scheduling, payment simulation, secure messaging, consent records, and audit trails.

This is a substantial engineering baseline, not a claim of clinical or regulatory certification. Before accepting real patient data, complete every gate in [Security and privacy design](docs/SECURITY.md).

## What changed from the prototype

- Application factory and environment-specific configuration
- PostgreSQL-ready Flask-SQLAlchemy domain model and Alembic migrations
- Named patient, doctor, and admin accounts with Argon2id password hashing
- Role-based and record-level authorization; opaque public identifiers
- CSRF protection, account lockout, rate limiting, hardened cookies and response headers
- Private uploads outside the web root with signature/parser checks and generated names
- Image rewriting to strip metadata and embedded content
- Transactional slot aggregate with PostgreSQL row locking and capacity constraint
- Patient-owned reports, photos, appointments, payments, and conversations
- Normalized bot/doctor message separation
- Consent capture and auditable sensitive actions
- Non-root/read-only container, PostgreSQL, Redis, Gunicorn, health probes, and migration entrypoint
- Automated authorization, upload, booking, refund, bot-safety, and health tests
- Linear SVM emergency-language classification with explicit patient-confirmed Twilio alerts

## Local development

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
flask --app app db upgrade
flask --app app seed-demo
flask --app app run --debug
```

Open <http://127.0.0.1:5000>.

Migrations are the authoritative schema path. `AUTO_CREATE_DB=true` exists only as an optional disposable-development shortcut; do not use it for maintained environments.

### Emergency SMS alerts

Emergency language is classified by a linear SVM over the submitted text. An emergency result does not send automatically: the authenticated patient must confirm an alert and select an active doctor. The alert sends a minimal message to the configured doctor and family contact.

To enable live SMS, set these values in the environment and use a Twilio E.164 sender number or approved Messaging Service:

```bash
SMS_ENABLED=true
SMS_PROVIDER=twilio
SMS_FROM=+15551234567
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
```

The provider call is synchronous and the database records each recipient result. Configure the family contact in the patient profile and the doctor SMS number through the staff/admin data path before testing. Twilio acceptance is not confirmation that a person received or responded to the message. Always contact local emergency services first.

### Development accounts

| Role | Email | Password |
|---|---|---|
| Patient | `patient@example.com` | `DemoPatient!2026` |
| Doctor | `asha@smarthealth.com` | `DemoPatient!2026` |
| Administrator | `admin@smarthealth.com` | `ChangeMe!Admin2026` |

These accounts are never automatically seeded in production mode. Change credentials if the environment is shared.

## Tests and quality

```bash
make test
make lint
```

The tests cover public rendering, authentication lockout, role denial, private-record IDOR denial, upload signature checks, booking duplication, cancellation/refund/capacity, emergency bot wording, and readiness probes.

## Production deployment

1. Copy `.env.example` to `.env` and set strong unique values. `SECRET_KEY` must be at least 32 characters.
2. Set `POSTGRES_PASSWORD` in `.env`; use a secret manager in managed environments.
3. Keep `FLASK_ENV=production`. Production startup refuses SQLite.
4. Start the stack:

```bash
docker compose up --build -d
```

The entrypoint applies migrations and seeds only department/condition reference data. It does not create demo patients, doctors, hospitals, or administrators.

5. Create the first administrator interactively inside the application container:

```bash
docker compose exec app flask --app app create-admin
```

6. Put a TLS reverse proxy/load balancer in front of `127.0.0.1:8000`; an example is in `deploy/nginx.conf.example`.

The production app uses Gunicorn. Flask’s built-in server is development-only.

## Documentation

- [Architecture and trust boundaries](docs/ARCHITECTURE.md)
- [Security controls and production gates](docs/SECURITY.md)
- [Operations, backup, monitoring, and incidents](docs/OPERATIONS.md)
- [Initial database migration](migrations/versions/36725bd94ff0_initial_production_schema.py)

## Project map

```text
app.py                      WSGI entry point
healthcare/
  __init__.py               app factory, headers, CLI
  config.py                 environment configuration
  extensions.py             SQLAlchemy, login, migration, CSRF, rate limits
  models.py                 normalized domain and audit model
  auth.py                   accounts, sessions, profiles, consent
  routes.py                 public and patient-owned workflows
  staff.py                  doctor/admin workflows
  services.py               scheduling and private upload transactions
  security.py               authorization and audit helpers
  seed.py                   reference/development data
utils/                       explainable educational analysis engines
templates/ + static/        responsive interface
migrations/                 versioned database schema
tests/                      security and workflow regression tests
deploy/ + Dockerfile        Gunicorn/container/reverse-proxy assets
```

## Medical disclaimer

Automated outputs are educational suggestions only. They are not diagnoses, prescriptions, clinical triage, or substitutes for licensed care. Never delay emergency care or change medication based on this platform. Serious symptoms require local emergency services or the nearest emergency department.
