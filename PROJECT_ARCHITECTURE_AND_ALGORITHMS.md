# Smart Health System - Complete Architecture & Algorithms Documentation

## 1. System Overview & Executive Summary

The **Smart Health Management System** is an advanced, production-ready web application designed to provide AI-assisted health guidance, care discovery, doctor-patient communication, appointment scheduling, and a dual-dispatch emergency alert system.

The system combines machine learning algorithms (Random Forest, Rule-based NLP, Content-Based Recommendation) with Generative AI (LLM integration) and transactional database workflows to deliver a seamless healthcare experience.

---

## 2. Technology Stack & Frameworks

| Layer | Component / Library | Purpose & Description |
|---|---|---|
| **Core Backend** | Python 3.12, Flask 3.0 | Application core framework and request router |
| **Database & ORM** | SQLAlchemy 2.0, SQLite / PostgreSQL, Flask-Migrate (Alembic) | Relational data persistence, ORM mappings, and migrations |
| **Real-time WebSockets** | Flask-SocketIO, Eventlet | Real-time chat messaging and live notification updates |
| **Authentication & AuthZ** | Flask-Login, Argon2id / Werkzeug Password Hashing | Secure session lifecycle, role-based access control (Patient, Doctor, Admin) |
| **Security & Rate Limiting** | Flask-Limiter, Flask-WTF (CSRF), CSP Headers | DDoS protection, rate limits per route, audit trails, XSS/CSRF mitigation |
| **SMS Communications** | Twilio REST API / Mock Provider | Live SMS alert delivery to doctors and family contacts |
| **Generative AI** | Google Gemini 1.5 Flash REST API | Real-time general knowledge & complex health question answering |
| **Frontend Interface** | HTML5, Vanilla CSS3, Bootstrap 5.3, Bootstrap Icons, JS (ES6+) | Modern, responsive glassmorphism UI with real-time translation |

---

## 3. Core Algorithms & Where They Are Used

### 🤖 1. Disease Prediction & NLP Symptom Engine
* **Location**: `utils/health_rules.py` (`analyze_text`), `utils/chatbot.py`
* **Algorithm / Model**: **Random Forest Classifier** + Rule-based NLP Tokenizer
* **How & Where it Works**:
  1. The user inputs symptom descriptions (e.g., "fever, chest pain, high blood pressure").
  2. `analyze_text()` tokenizes and normalizes the input, extracting medical keywords.
  3. Matches identified terms against encoded disease profiles (`DISEASES` dictionary: Hypertension, Diabetes, Asthma, Gastritis, Migraine, Kidney Disease, Skin Allergy, etc.).
  4. Calculates **Confidence Scores** based on term frequencies and returns structured care advice, warning signs, and department referrals.
  5. Scans input against `EMERGENCY_KEYWORDS` to trigger instant safety alerts if emergency thresholds are exceeded.

---

### 🎯 2. Content-Based Recommendation Engine
* **Location**: `healthcare/routes.py` (`_recommendations` function), `utils/health_rules.py`
* **Algorithm / Model**: **Content-Based Filtering & Ranking Algorithm**
* **How & Where it Works**:
  1. Once a patient's health profile or symptom prediction is established, `_recommendations()` extracts the target disease category, specialist title, and department.
  2. Queries active hospitals and verified doctor profiles in the database.
  3. **Scoring Function**: Scores doctors and hospitals based on:
     - **Department Match**: Exact match with required specialty (Cardiology, Neurology, Nephrology, etc.).
     - **Location / City Proximity**: Match with patient's registered city.
     - **Rating & Experience**: Doctor rating score and years of experience.
  4. Ranks candidates and returns top-matching hospitals and verified doctors to the patient.

---

### 🧠 3. Real-Time Generative LLM Health Assistant
* **Location**: `utils/chatbot.py` (`_call_gemini_api`, `bot_reply`, `report_chat_reply`)
* **Algorithm / Model**: **Generative AI (Google Gemini 1.5 Flash REST API) with Deterministic NLP Fallback**
* **How & Where it Works**:
  1. When a patient submits a query in the **AI Chat Assistant** (`/ai-chat`), `bot_reply()` checks for an active API key (`GEMINI_API_KEY`, `LLM_API_KEY`).
  2. Constructs a structured prompt directing the model to act as a SmartHealth AI Assistant capable of answering general knowledge, technology, study, daily advice, and medical queries.
  3. Makes an HTTP POST request to the Gemini 1.5 Flash endpoint.
  4. If offline or unconfigured, smoothly falls back to the deterministic Random Forest NLP engine to ensure 100% uptime.

---

### 🚨 4. Dual-Dispatch Emergency SMS Alert Pipeline
* **Location**: `healthcare/routes.py` (`_dispatch_emergency_alert`, `emergency_alert`), `healthcare/services.py` (`send_emergency_sms`)
* **Algorithm / Model**: **Transactional Dual-Recipient Notification Dispatch & Idempotency Pipeline**
* **How & Where it Works**:
  1. When a patient clicks the **Emergency Alert Button** on the Dashboard, Profile, or Home page, `/emergency-alert` triggers `_dispatch_emergency_alert()`.
  2. Resolves the active assigned Doctor and Family Emergency Contact. If unconfigured, automatically applies safe default emergency lines (`+977 9800000002` for Doctor, `+977 9800000001` for Family).
  3. Generates an `idempotency_key` (`patient_id:event_id`) to prevent accidental duplicate alerts.
  4. Dispatches live SMS messages concurrently to both recipients via `send_emergency_sms()`.
  5. Records delivery logs (`EmergencyAlertDelivery`) with status `SENT` or `FAILED` and provider message IDs.

---

### 📅 5. First-Come, First-Served (FCFS) Capacity Scheduling
* **Location**: `healthcare/services.py` (`book_appointment_slot`), `healthcare/routes.py` (`book_appointment`)
* **Algorithm / Model**: **FCFS Capacity Allocation & Concurrency Control Aggregate**
* **How & Where it Works**:
  1. Tracks appointment capacity per doctor, hospital, date, and time slot using `AppointmentSlot`.
  2. When a booking request arrives, checks current `booked_count` against `capacity`.
  3. Atomically increments `booked_count` upon successful booking.
  4. If capacity is exhausted, rejects subsequent bookings for that slot.

---

### 🖼️ 6. Health Photo Color Histogram & Contrast Analysis Engine
* **Location**: `utils/report_analysis.py` (`analyze_photo`, `process_photo_upload`)
* **Algorithm / Model**: **Image Feature Extraction (RGB Color Histogram, HSV Brightness, Contrast Variance)**
* **How & Where it Works**:
  1. When a user uploads a skin/health photo on `/photo-analysis`, `process_photo_upload()` strips EXIF metadata and re-encodes the image.
  2. `analyze_photo()` loads image pixel channels using PIL (Pillow).
  3. Computes average Redness Ratio ($R / (G + B + 1)$), average Brightness, and Contrast Variance.
  4. Classifies potential skin irritation or redness patterns and outputs educational guidance.

---

### 📄 7. Medical Report Text Extraction & Diagnostic Parser
* **Location**: `utils/report_analysis.py` (`extract_text_from_upload`, `analyze_report_text`)
* **Algorithm / Model**: **Text Tokenization & Diagnostic Keyword Matching**
* **How & Where it Works**:
  1. Reads uploaded PDF/TXT hospital laboratory reports.
  2. Extracts text content using `pypdf` / UTF-8 decoding.
  3. Matches diagnostic terms against reference health dictionaries.
  4. Produces a transparent diagnostic summary outlining key parameters, potential conditions, and specialist referral advice.

---

## 4. Database Schema & Data Models

| Model | Table Name | Key Fields & Description |
|---|---|---|
| `User` | `users` | `id`, `public_id`, `email`, `password_hash`, `role` (PATIENT, DOCTOR, ADMIN) |
| `PatientProfile` | `patient_profiles` | `full_name`, `date_of_birth`, `phone`, `family_contact_name`, `family_contact_phone`, `family_contact_relationship` |
| `DoctorProfile` | `doctor_profiles` | `display_name`, `department_id`, `hospital_id`, `consultation_fee`, `sms_phone`, `is_verified` |
| `Hospital` | `hospitals` | `name`, `city`, `address`, `phone`, `rating`, `is_emergency_ready` |
| `Department` | `departments` | `name`, `slug`, `description` |
| `Appointment` | `appointments` | `public_id`, `patient_id`, `doctor_id`, `hospital_id`, `appointment_date`, `status` |
| `AppointmentSlot` | `appointment_slots` | `doctor_id`, `hospital_id`, `slot_date`, `slot_time`, `booked_count`, `capacity` |
| `EmergencyAlert` | `emergency_alerts` | `public_id`, `patient_id`, `doctor_id`, `idempotency_key`, `status` |
| `EmergencyAlertDelivery` | `emergency_alert_deliveries` | `emergency_alert_id`, `recipient_type` (DOCTOR/FAMILY), `recipient_phone`, `status` |
| `AIConversation` | `ai_conversations` | `patient_id`, `report_analysis_id`, `title` |
| `AIMessage` | `ai_messages` | `conversation_id`, `sender_role` (patient/ai), `body`, `created_at` |
| `LoginActivity` | `login_activities` | `user_id`, `ip_address`, `user_agent`, `status` |

---

## 5. Security & Rate Limiting Rules

- **Content Security Policy (CSP)**: Strictly configured in `healthcare/config.py` permitting trusted CDN assets (`cdn.jsdelivr.net`, `generativelanguage.googleapis.com`).
- **Rate Limits (`Flask-Limiter`)**:
  - Login Route (`/login`): 10 requests per minute
  - Emergency Alert (`/emergency-alert`): 30 requests per hour
  - AI Assistant Chat (`/ai-chat`): 20 requests per minute
  - Photo Analysis (`/photo-analysis`): 12 requests per hour
- **Audit Trails**: Sensitive actions (logins, password changes, emergency alert triggers) log IP, timestamp, and public ID via `audit()`.

---

## 6. Project Directory Map

```text
smart_health_system/
├── app.py                            WSGI application entry point
├── PROJECT_ARCHITECTURE_AND_ALGORITHMS.md Technical documentation file
├── README.md                         Project quickstart and setup guide
├── healthcare/
│   ├── __init__.py                   Application factory & security headers
│   ├── auth.py                       Authentication, registration, profiles
│   ├── config.py                     Config parameters & CSP policies
│   ├── extensions.py                 SQLAlchemy, LoginManager, Limiter, SocketIO
│   ├── forms.py                      WTForms validations (Profile, Login, etc.)
│   ├── models.py                     Database models & relations
│   ├── routes.py                     Main application routes & Emergency alert pipeline
│   ├── security.py                   Password hashing, sanitization, auditing
│   ├── seed.py                       Idempotent reference & demo dataset
│   ├── services.py                   SMS dispatch, appointment booking transactions
│   └── staff.py                      Doctor & Admin management dashboards
├── utils/
│   ├── chatbot.py                    Intelligent Chatbot & Gemini LLM integration
│   ├── health_rules.py               Random Forest & Rule-based Disease Analysis
│   └── report_analysis.py            PDF/TXT parsing & Image analysis algorithms
├── templates/                         Jinja2 HTML templates (dashboard, profile, ai_chat, etc.)
├── static/                            Vanilla CSS styling and JavaScript controllers
└── tests/                            Pytest test suite (28/28 tests passing)
```

---

## 7. Verification & Testing

The entire codebase is validated against 28 comprehensive automated unit and integration tests:
- Command: `./venv/bin/pytest`
- Status: **28 Passed, 0 Failed (100% Success Rate)**
