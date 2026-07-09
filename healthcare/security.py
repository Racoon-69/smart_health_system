"""Authorization, audit, and validation helpers."""

from __future__ import annotations

import re
from functools import wraps

from flask import abort, request
from flask_login import current_user, login_required

from .extensions import db
from .models import AuditEvent, UserRole

PHONE_RE = re.compile(r"^[0-9+() .-]{7,30}$")


def role_required(*roles: UserRole):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def owns_patient_record(patient_id: int) -> bool:
    return current_user.is_authenticated and (current_user.id == patient_id or current_user.role == UserRole.ADMIN)


def can_access_doctor_record(doctor_id: int) -> bool:
    if not current_user.is_authenticated:
        return False
    if current_user.role == UserRole.ADMIN:
        return True
    return bool(
        current_user.role == UserRole.DOCTOR
        and current_user.doctor_profile
        and current_user.doctor_profile.id == doctor_id
    )


def audit(action: str, entity_type: str, entity_id=None, *, outcome="success", details=None) -> AuditEvent:
    event = AuditEvent(
        actor_id=current_user.id if current_user.is_authenticated else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        outcome=outcome,
        ip_address=(request.access_route[0] if request.access_route else request.remote_addr),
        user_agent=request.user_agent.string[:300],
        details=details or {},
    )
    db.session.add(event)
    return event


def clean_text(value: str | None, max_length: int, *, required: bool = False) -> str:
    cleaned = " ".join((value or "").strip().split())
    if required and not cleaned:
        raise ValueError("A required field is missing.")
    if len(cleaned) > max_length:
        raise ValueError(f"Input exceeds the {max_length} character limit.")
    return cleaned
