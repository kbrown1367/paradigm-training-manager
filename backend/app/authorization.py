from types import SimpleNamespace

from flask import (
    current_app,
    g,
    jsonify,
    request,
)

from app.auth import (
    ROLE_AGENCY_ADMIN,
    ROLE_PLATFORM_ADMIN,
    get_session_user,
)


def authorize_operational_api_request():
    """
    Authenticate and tenant-scope requests handled by the
    main operational API blueprint.

    AUTHORIZATION_DISABLED exists only to allow legacy route
    unit tests to exercise their original endpoint behavior.
    Production configuration never enables it. Dedicated
    authorization tests explicitly exercise the real guard.
    """

    if current_app.config.get(
        "AUTHORIZATION_DISABLED",
        False,
    ):
        g.current_user = SimpleNamespace(
            role=ROLE_PLATFORM_ADMIN,
            agency_id=None,
        )
        return None

    user = get_session_user()

    if user is None:
        return jsonify(
            {
                "error":
                    "Authentication required."
            }
        ), 401

    g.current_user = user

    if user.role not in {
        ROLE_AGENCY_ADMIN,
        ROLE_PLATFORM_ADMIN,
    }:
        return jsonify(
            {
                "error":
                    "Resource not found."
            }
        ), 404

    view_args = request.view_args or {}
    requested_agency_id = view_args.get(
        "agency_id"
    )

    if requested_agency_id is None:
        return None

    if user.role == ROLE_PLATFORM_ADMIN:
        return None

    if (
        user.role == ROLE_AGENCY_ADMIN
        and user.agency_id is not None
        and user.agency_id == requested_agency_id
    ):
        return None

    return jsonify(
        {
            "error":
                "Resource not found."
        }
    ), 404
