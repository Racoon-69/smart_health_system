# Security and privacy design

## Implemented controls

- Named patient, doctor, and administrator accounts; no shared admin key.
- Argon2id password hashes and 15-character minimum for new passwords.
- Temporary account lock after repeated failures and rate limits on authentication/analysis endpoints.
- `HttpOnly`, `SameSite=Lax`, short-lived sessions; `Secure` cookies and HSTS in production.
- CSRF protection on state-changing browser workflows.
- Role authorization plus object ownership checks on every private record.
- Opaque UUIDs in external record URLs; authorization does not rely on unpredictability.
- Restrictive CSP, clickjacking, content sniffing, referrer, opener, and permissions headers.
- Upload extension, size, signature/parser, page/dimension checks; generated names; private storage.
- Uploaded images are decoded and rewritten to strip metadata/embedded content.
- PostgreSQL row locks and database constraints protect appointment capacity.
- Append-only application audit events for sensitive reads and writes.
- No card number, OTP, PIN, or wallet credential collection.
- No PHI copied into audit detail fields.
- Docker runtime is non-root, read-only, capability-dropped, and no-new-privileges.

## Production gates that require organizational decisions

The repository cannot by itself certify a healthcare deployment. Before real patient information is accepted, owners must complete:

1. Jurisdiction-specific privacy, health, medical-device, telemedicine, and retention assessment.
2. Threat model, privacy impact assessment, data-flow inventory, and incident response exercises.
3. Managed identity or OIDC/SMART integration with MFA, email/identity verification, and session revocation.
4. Malware scanning/content disarm in an isolated upload pipeline and encrypted object storage.
5. TLS certificates, encryption-key management, database/storage encryption, secret manager, and key rotation.
6. Tamper-evident centralized audit export, monitoring, alerting, and tested time synchronization.
7. Backup, point-in-time recovery, disaster-recovery drills, retention, legal hold, and secure deletion.
8. Vendor agreements, least-privilege operations access, workforce training, and periodic access review.
9. Independent penetration test, dependency/SAST/container scanning, and remediation sign-off.
10. Clinical safety review of every rule, copy change, escalation threshold, and supported workflow.
11. Accessibility and localization review, including emergency numbers and clinical terminology.
12. Real payment-provider hosted checkout/webhook verification if payments leave simulation mode.

## Data classification

| Class | Examples | Required handling |
|---|---|---|
| Public | hospital directory, department descriptions | normal integrity controls |
| Internal | operational configuration, non-sensitive metrics | authenticated staff access |
| Confidential | account email, appointment metadata | encryption, least privilege, audit |
| Restricted health data | reports, photos, symptoms, messages | explicit purpose, strongest access and retention controls |

## Reporting vulnerabilities

Do not open a public issue containing patient data or exploit details. Configure a monitored private security contact and disclosure policy before launch.

## Primary references

- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
- [HHS HIPAA Security Rule overview](https://www.hhs.gov/hipaa/for-professionals/security/index.html) (applicable only where US HIPAA scope exists)
- [HL7 FHIR Security](https://hl7.org/fhir/security.html)
