from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from uuid import UUID

from flask import session

from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

from app.models import User


ROLE_PLATFORM_ADMIN = "PLATFORM_ADMIN"
ROLE_AGENCY_ADMIN = "AGENCY_ADMIN"

SUPPORTED_USER_ROLES = {
    ROLE_PLATFORM_ADMIN,
    ROLE_AGENCY_ADMIN,
}

INVITATION_EXPIRATION_HOURS = 72


def hash_invitation_token(token):
    if not token:
        return ""

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def generate_invitation_token():
    token = secrets.token_urlsafe(32)

    return (
        token,
        hash_invitation_token(token),
    )


def invitation_expiration():
    return datetime.now(
        timezone.utc
    ) + timedelta(
        hours=INVITATION_EXPIRATION_HOURS
    )


def invitation_is_expired(value):
    if value is None:
        return True

    if value.tzinfo is None:
        now = datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )
    else:
        now = datetime.now(
            timezone.utc
        )

    return value <= now


def hash_password(password):
    if not password:
        raise ValueError("Password is required.")

    return generate_password_hash(password)


def verify_password(password_hash, password):
    if not password_hash or not password:
        return False

    return check_password_hash(
        password_hash,
        password,
    )


def user_has_role(user, role):
    return (
        user is not None
        and user.status == "active"
        and user.role == role
    )


def user_is_platform_admin(user):
    return user_has_role(
        user,
        ROLE_PLATFORM_ADMIN,
    )


def user_is_agency_admin(user):
    return user_has_role(
        user,
        ROLE_AGENCY_ADMIN,
    )


def normalize_login_email(value):
    if not value:
        return ""

    return value.strip().lower()


def serialize_user(user):
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "status": user.status,
        "agency_id": (
            str(user.agency_id)
            if user.agency_id is not None
            else None
        ),
        "agency": (
            {
                "id": str(user.agency.id),
                "name": user.agency.name,
            }
            if user.agency is not None
            else None
        ),
    }


def get_session_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    try:
        user_uuid = UUID(user_id)
    except (TypeError, ValueError):
        session.clear()
        return None

    user = User.query.filter_by(
        id=user_uuid,
    ).one_or_none()

    if (
        user is None
        or user.status != "active"
    ):
        session.clear()
        return None

    return user
