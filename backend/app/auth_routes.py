from datetime import datetime, timezone

from flask import (
    Blueprint,
    jsonify,
    request,
    session,
)

from app.auth import (
    get_session_user,
    hash_password,
    normalize_login_email,
    serialize_user,
    verify_password,
)
from app.extensions import db
from app.models import User


auth_api = Blueprint(
    "auth_api",
    __name__,
)




@auth_api.post("/login")
def login():
    payload = request.get_json(
        silent=True
    ) or {}

    email = normalize_login_email(
        payload.get("email")
    )
    password = payload.get("password") or ""

    if not email or not password:
        return jsonify(
            {
                "error":
                    "Email and password are required."
            }
        ), 400

    user = User.query.filter(
        db.func.lower(User.email) == email
    ).one_or_none()

    if (
        user is None
        or user.status != "active"
        or not verify_password(
            user.password_hash,
            password,
        )
    ):
        return jsonify(
            {
                "error":
                    "Invalid email or password."
            }
        ), 401

    session.clear()
    session["user_id"] = str(user.id)
    session.permanent = True

    user.last_login_at = datetime.now(
        timezone.utc
    )

    db.session.commit()

    return jsonify(
        {
            "authenticated": True,
            "user": serialize_user(user),
        }
    ), 200


@auth_api.post("/change-password")
def change_password():
    user = get_session_user()

    if user is None:
        return jsonify(
            {
                "error":
                    "Authentication required."
            }
        ), 401

    payload = request.get_json(
        silent=True
    ) or {}

    current_password = (
        payload.get("current_password")
        or ""
    )

    new_password = (
        payload.get("new_password")
        or ""
    )

    if not current_password:
        return jsonify(
            {
                "error":
                    "Current password is required."
            }
        ), 400

    if len(new_password) < 12:
        return jsonify(
            {
                "error":
                    "New password must be at least "
                    "12 characters."
            }
        ), 400

    if not verify_password(
        user.password_hash,
        current_password,
    ):
        return jsonify(
            {
                "error":
                    "Current password is incorrect."
            }
        ), 400

    if verify_password(
        user.password_hash,
        new_password,
    ):
        return jsonify(
            {
                "error":
                    "New password must be different "
                    "from the current password."
            }
        ), 400

    user.password_hash = hash_password(
        new_password
    )

    db.session.commit()

    return jsonify(
        {
            "message":
                "Password changed successfully."
        }
    ), 200


@auth_api.post("/logout")
def logout():
    session.clear()

    return jsonify(
        {
            "authenticated": False,
        }
    ), 200


@auth_api.get("/me")
def me():
    user = get_session_user()

    if user is None:
        return jsonify(
            {
                "authenticated": False,
                "user": None,
            }
        ), 401

    return jsonify(
        {
            "authenticated": True,
            "user": serialize_user(user),
        }
    ), 200
