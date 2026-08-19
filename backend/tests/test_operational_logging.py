# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.

import logging

from app import create_app


def build_test_app():
    return create_app(
        {
            "TESTING": False,
            "SQLALCHEMY_DATABASE_URI":
                "sqlite:///:memory:",
            "SECRET_KEY":
                "operational-logging-test-secret",
            "LOG_LEVEL": "INFO",
        }
    )


def combined_log_text(caplog):
    return "\n".join(
        record.getMessage()
        for record in caplog.records
    )


def test_unknown_api_route_returns_json_404():
    app = build_test_app()

    response = app.test_client().get(
        "/api/this-route-does-not-exist"
    )

    assert response.status_code == 404
    assert response.is_json
    assert response.get_json() == {
        "error": "Resource not found."
    }


def test_frontend_client_route_still_uses_frontend():
    app = build_test_app()

    response = app.test_client().get(
        "/some-client-side-route"
    )

    assert response.status_code == 200


def test_unexpected_api_exception_returns_safe_json(
    caplog,
):
    app = build_test_app()

    @app.get("/api/test-unexpected-error")
    def test_unexpected_error():
        raise RuntimeError(
            "SENSITIVE-EXCEPTION-MESSAGE"
        )

    with caplog.at_level(
        logging.ERROR,
        logger=app.logger.name,
    ):
        response = app.test_client().get(
            "/api/test-unexpected-error"
        )

    assert response.status_code == 500
    assert response.is_json
    assert response.get_json() == {
        "error":
            "An unexpected server error occurred."
    }

    combined = combined_log_text(caplog)

    assert "Unhandled PTM exception" in combined
    assert "RuntimeError" in combined
    assert "test_unexpected_error" in combined

    assert (
        "SENSITIVE-EXCEPTION-MESSAGE"
        not in combined
    )


def test_operational_log_excludes_query_string(
    caplog,
):
    app = build_test_app()

    @app.get("/api/test-query-redaction")
    def test_query_redaction():
        raise RuntimeError("boom")

    with caplog.at_level(
        logging.ERROR,
        logger=app.logger.name,
    ):
        response = app.test_client().get(
            (
                "/api/test-query-redaction"
                "?token=SECRET-TOKEN"
                "&password=SECRET-PASSWORD"
            )
        )

    assert response.status_code == 500

    combined = combined_log_text(caplog)

    assert "/api/test-query-redaction" in combined
    assert "SECRET-TOKEN" not in combined
    assert "SECRET-PASSWORD" not in combined
    assert "?token=" not in combined


def test_operational_log_excludes_request_body(
    caplog,
):
    app = build_test_app()

    @app.post("/api/test-body-redaction")
    def test_body_redaction():
        raise RuntimeError("boom")

    with caplog.at_level(
        logging.ERROR,
        logger=app.logger.name,
    ):
        response = app.test_client().post(
            "/api/test-body-redaction",
            json={
                "password":
                    "DO-NOT-LOG-THIS-PASSWORD",
                "token":
                    "DO-NOT-LOG-THIS-TOKEN",
                "employee_name":
                    "DO-NOT-LOG-THIS-NAME",
            },
        )

    assert response.status_code == 500

    combined = combined_log_text(caplog)

    assert (
        "DO-NOT-LOG-THIS-PASSWORD"
        not in combined
    )
    assert (
        "DO-NOT-LOG-THIS-TOKEN"
        not in combined
    )
    assert (
        "DO-NOT-LOG-THIS-NAME"
        not in combined
    )


def test_log_level_is_info():
    app = build_test_app()

    assert app.config["LOG_LEVEL"] == "INFO"
    assert app.logger.getEffectiveLevel() == (
        logging.INFO
    )
