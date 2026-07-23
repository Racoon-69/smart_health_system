# Production operations runbook

## Release

1. Build an immutable image from a reviewed commit.
2. Run unit/integration tests, dependency review, SAST, and image scan.
3. Back up PostgreSQL and verify restore metadata.
4. Run `flask --app app db upgrade` as a one-off migration task.
5. Deploy application workers; verify `/health/live` and `/health/ready`.
6. Run patient login, directory read, staff authorization, and audit smoke tests.
7. Monitor errors, latency, database locks, storage growth, authentication failures, and queue depth.

Do not run multiple replicas that all execute migrations simultaneously. The provided entrypoint is convenient for a single-instance setup; orchestrated production should use a dedicated migration job.

## Backup and restore

- Enable PostgreSQL encrypted full backups and point-in-time WAL archiving.
- Back up private upload storage with matching retention and encryption.
- Keep database and file snapshots consistent enough to resolve storage keys.
- Test restores in an isolated environment at a defined cadence.
- Record RPO/RTO targets and restore-test evidence.

Example logical backup (credentials supplied securely):

```bash
pg_dump --format=custom --file=smarthealth.dump "$DATABASE_URL"
pg_restore --clean --if-exists --dbname="$RESTORE_DATABASE_URL" smarthealth.dump
```

## Incident response

1. Preserve audit/database/proxy logs and establish incident command.
2. Contain affected identities, keys, hosts, and upload paths.
3. Determine affected records and access timeline.
4. Follow jurisdictional breach assessment and notification procedures.
5. Restore from known-good artifacts, rotate secrets, and validate controls.
6. Complete a blameless review with tracked remediation.

## Monitoring signals

- 5xx/429 rate, response latency, readiness failures
- login failures and account lockouts
- denied authorization and private-file requests
- unexpected admin creation or role changes
- appointment transaction conflicts and database lock time
- upload rejects/parser errors and storage growth
- audit export failures, clock drift, and backup age
- emergency alert delivery failures, Twilio API errors, and partial recipient delivery

## Emergency SMS

Set `SMS_ENABLED=true`, `SMS_PROVIDER=twilio`, `SMS_FROM`, `TWILIO_ACCOUNT_SID`, and `TWILIO_AUTH_TOKEN` through the deployment secret manager. `SMS_FROM` must be a Twilio-approved E.164 sender or Messaging Service identity. Apply the emergency-alert Alembic migration during release with the normal `flask --app app db upgrade` step.

The alert endpoint creates durable delivery records before calling Twilio. A `Sent` status means Twilio accepted the request; it does not mean the handset received the message. Review partial and failed delivery records, provider logs, and rate-limit events. Do not place full symptoms, reports, diagnoses, or medication data in SMS content.

## Scaling

- Scale stateless Gunicorn containers horizontally behind a TLS proxy.
- Use Redis for shared rate-limit state.
- Use PostgreSQL for row locking and durable transactions.
- Move files to encrypted private object storage with short-lived authorized retrieval.
- Move parsing/image processing to isolated asynchronous workers when volume warrants it.
