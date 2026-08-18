from uuid import UUID

import pytest

from app import create_app
from app.auth import (
    ROLE_AGENCY_ADMIN,
    ROLE_PLATFORM_ADMIN,
    hash_password,
)
from app.extensions import db
from app.models import (
    Agency,
    Officer,
    User,
)


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY":
                "tenant-authorization-test-secret",
            "AUTHORIZATION_DISABLED": False,
            "SQLALCHEMY_DATABASE_URI":
                "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def tenant_data(app):
    with app.app_context():
        agency_a = Agency(
            name="Agency Alpha",
            email_domain="alpha.gov",
            email_pattern="FIRST_INITIAL_LAST",
        )

        agency_b = Agency(
            name="Agency Bravo",
            email_domain="bravo.gov",
            email_pattern="FIRST_INITIAL_LAST",
        )

        db.session.add_all(
            [
                agency_a,
                agency_b,
            ]
        )
        db.session.flush()

        officer_a = Officer(
            agency_id=agency_a.id,
            tcole_pid="A100",
            first_name="Alice",
            last_name="Alpha",
        )

        officer_b = Officer(
            agency_id=agency_b.id,
            tcole_pid="B200",
            first_name="Bob",
            last_name="Bravo",
        )

        admin_a = User(
            agency_id=agency_a.id,
            email="admin@alpha.gov",
            password_hash=hash_password(
                "AlphaPassword123!"
            ),
            first_name="Admin",
            last_name="Alpha",
            role=ROLE_AGENCY_ADMIN,
            status="active",
        )

        admin_b = User(
            agency_id=agency_b.id,
            email="admin@bravo.gov",
            password_hash=hash_password(
                "BravoPassword123!"
            ),
            first_name="Admin",
            last_name="Bravo",
            role=ROLE_AGENCY_ADMIN,
            status="active",
        )

        platform_admin = User(
            agency_id=None,
            email="platform@paradigm.local",
            password_hash=hash_password(
                "PlatformPassword123!"
            ),
            first_name="Platform",
            last_name="Administrator",
            role=ROLE_PLATFORM_ADMIN,
            status="active",
        )

        db.session.add_all(
            [
                officer_a,
                officer_b,
                admin_a,
                admin_b,
                platform_admin,
            ]
        )

        db.session.commit()

        return {
            "agency_a_id":
                str(agency_a.id),
            "agency_b_id":
                str(agency_b.id),
            "officer_a_id":
                str(officer_a.id),
            "officer_b_id":
                str(officer_b.id),
        }


def login(
    client,
    email,
    password,
):
    response = client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200

    return response


def test_unauthenticated_agency_officers_is_401(
    app,
    tenant_data,
):
    client = app.test_client()

    response = client.get(
        "/api/agencies/"
        f"{tenant_data['agency_a_id']}"
        "/officers"
    )

    assert response.status_code == 401
    assert response.get_json() == {
        "error": "Authentication required."
    }


def test_admin_a_can_access_agency_a(
    app,
    tenant_data,
):
    client = app.test_client()

    login(
        client,
        "admin@alpha.gov",
        "AlphaPassword123!",
    )

    response = client.get(
        "/api/agencies/"
        f"{tenant_data['agency_a_id']}"
        "/officers"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert len(data) == 1
    assert data[0]["tcole_pid"] == "A100"


def test_admin_a_cannot_access_agency_b(
    app,
    tenant_data,
):
    client = app.test_client()

    login(
        client,
        "admin@alpha.gov",
        "AlphaPassword123!",
    )

    response = client.get(
        "/api/agencies/"
        f"{tenant_data['agency_b_id']}"
        "/officers"
    )

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "Resource not found."
    }


def test_admin_b_can_access_agency_b(
    app,
    tenant_data,
):
    client = app.test_client()

    login(
        client,
        "admin@bravo.gov",
        "BravoPassword123!",
    )

    response = client.get(
        "/api/agencies/"
        f"{tenant_data['agency_b_id']}"
        "/officers"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert len(data) == 1
    assert data[0]["tcole_pid"] == "B200"


def test_admin_b_cannot_access_agency_a(
    app,
    tenant_data,
):
    client = app.test_client()

    login(
        client,
        "admin@bravo.gov",
        "BravoPassword123!",
    )

    response = client.get(
        "/api/agencies/"
        f"{tenant_data['agency_a_id']}"
        "/officers"
    )

    assert response.status_code == 404


def test_admin_a_cannot_access_officer_b_via_agency_b(
    app,
    tenant_data,
):
    client = app.test_client()

    login(
        client,
        "admin@alpha.gov",
        "AlphaPassword123!",
    )

    response = client.get(
        "/api/agencies/"
        f"{tenant_data['agency_b_id']}"
        "/officers/"
        f"{tenant_data['officer_b_id']}"
        "/workspace"
    )

    assert response.status_code == 404


def test_admin_a_cannot_access_officer_b_via_agency_a(
    app,
    tenant_data,
):
    client = app.test_client()

    login(
        client,
        "admin@alpha.gov",
        "AlphaPassword123!",
    )

    response = client.get(
        "/api/agencies/"
        f"{tenant_data['agency_a_id']}"
        "/officers/"
        f"{tenant_data['officer_b_id']}"
        "/workspace"
    )

    assert response.status_code == 404


def test_admin_a_cannot_access_agency_b_dashboard(
    app,
    tenant_data,
):
    client = app.test_client()

    login(
        client,
        "admin@alpha.gov",
        "AlphaPassword123!",
    )

    response = client.get(
        "/api/agencies/"
        f"{tenant_data['agency_b_id']}"
        "/compliance/dashboard"
    )

    assert response.status_code == 404


def test_admin_a_cannot_patch_agency_b_email_settings(
    app,
    tenant_data,
):
    client = app.test_client()

    login(
        client,
        "admin@alpha.gov",
        "AlphaPassword123!",
    )

    response = client.patch(
        "/api/agencies/"
        f"{tenant_data['agency_b_id']}"
        "/email-configuration",
        json={
            "email_domain": "changed.gov",
            "email_pattern":
                "FIRST_INITIAL_LAST",
        },
    )

    assert response.status_code == 404


def test_admin_a_cannot_import_into_agency_b(
    app,
    tenant_data,
):
    client = app.test_client()

    login(
        client,
        "admin@alpha.gov",
        "AlphaPassword123!",
    )

    response = client.post(
        "/api/agencies/"
        f"{tenant_data['agency_b_id']}"
        "/imports/tcole"
    )

    assert response.status_code == 404


def test_admin_a_agency_list_contains_only_a(
    app,
    tenant_data,
):
    client = app.test_client()

    login(
        client,
        "admin@alpha.gov",
        "AlphaPassword123!",
    )

    response = client.get(
        "/api/agencies"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert len(data) == 1
    assert (
        data[0]["id"]
        == tenant_data["agency_a_id"]
    )
    assert data[0]["name"] == "Agency Alpha"

    serialized = str(data)

    assert "Agency Bravo" not in serialized
    assert tenant_data["agency_b_id"] not in serialized


def test_admin_b_agency_list_contains_only_b(
    app,
    tenant_data,
):
    client = app.test_client()

    login(
        client,
        "admin@bravo.gov",
        "BravoPassword123!",
    )

    response = client.get(
        "/api/agencies"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert len(data) == 1
    assert (
        data[0]["id"]
        == tenant_data["agency_b_id"]
    )


def test_unauthenticated_agency_list_is_401(
    app,
    tenant_data,
):
    client = app.test_client()

    response = client.get(
        "/api/agencies"
    )

    assert response.status_code == 401


def test_authenticated_admin_can_access_metadata(
    app,
    tenant_data,
):
    client = app.test_client()

    login(
        client,
        "admin@alpha.gov",
        "AlphaPassword123!",
    )

    assignment_response = client.get(
        "/api/assignment-types"
    )

    credential_response = client.get(
        "/api/credential-types"
    )

    assert assignment_response.status_code == 200
    assert credential_response.status_code == 200


def test_unauthenticated_metadata_is_401(
    app,
    tenant_data,
):
    client = app.test_client()

    assert client.get(
        "/api/assignment-types"
    ).status_code == 401

    assert client.get(
        "/api/credential-types"
    ).status_code == 401


def test_platform_admin_can_list_both_agencies(
    app,
    tenant_data,
):
    client = app.test_client()

    login(
        client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    response = client.get(
        "/api/agencies"
    )

    assert response.status_code == 200

    data = response.get_json()

    ids = {
        item["id"]
        for item in data
    }

    assert tenant_data["agency_a_id"] in ids
    assert tenant_data["agency_b_id"] in ids


def test_platform_admin_can_access_either_agency(
    app,
    tenant_data,
):
    client = app.test_client()

    login(
        client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    response_a = client.get(
        "/api/agencies/"
        f"{tenant_data['agency_a_id']}"
        "/officers"
    )

    response_b = client.get(
        "/api/agencies/"
        f"{tenant_data['agency_b_id']}"
        "/officers"
    )

    assert response_a.status_code == 200
    assert response_b.status_code == 200


def test_inactive_session_user_is_rejected(
    app,
    tenant_data,
):
    client = app.test_client()

    login(
        client,
        "admin@alpha.gov",
        "AlphaPassword123!",
    )

    with app.app_context():
        user = User.query.filter_by(
            email="admin@alpha.gov",
        ).one()

        user.status = "inactive"
        db.session.commit()

    response = client.get(
        "/api/agencies/"
        f"{tenant_data['agency_a_id']}"
        "/officers"
    )

    assert response.status_code == 401

    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_every_operational_agency_route_is_tenant_guarded(
    app,
    tenant_data,
):
    """
    Security regression test.

    Every agency-scoped route registered on the operational
    API blueprint must reject an Agency Alpha administrator
    when Agency Bravo's ID is supplied.

    This protects future operational endpoints from being
    added without tenant isolation.
    """

    client = app.test_client()

    login(
        client,
        "admin@alpha.gov",
        "AlphaPassword123!",
    )

    agency_b_id = tenant_data["agency_b_id"]

    agency_rules = []

    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith("api.") and (
            "<uuid:agency_id>" in rule.rule
        ):
            agency_rules.append(rule)

    assert agency_rules, (
        "Expected at least one agency-scoped "
        "operational API route."
    )

    failures = []

    for rule in agency_rules:
        path = rule.rule.replace(
            "<uuid:agency_id>",
            agency_b_id,
        )

        # Other dynamic values do not matter because the
        # tenant guard must reject the request before the
        # endpoint itself executes.
        path = path.replace(
            "<uuid:officer_id>",
            tenant_data["officer_b_id"],
        )
        path = path.replace(
            "<uuid:import_job_id>",
            "00000000-0000-0000-0000-000000000001",
        )
        path = path.replace(
            "<assignment_type>",
            "SUPERVISOR",
        )
        path = path.replace(
            "<credential_type>",
            "TEST",
        )
        path = path.replace(
            "<license_type>",
            "PEACE_OFFICER",
        )

        methods = sorted(
            method
            for method in rule.methods
            if method not in {
                "HEAD",
                "OPTIONS",
            }
        )

        for method in methods:
            response = client.open(
                path,
                method=method,
                json={}
                if method in {
                    "POST",
                    "PATCH",
                    "PUT",
                }
                else None,
            )

            if response.status_code != 404:
                failures.append(
                    (
                        method,
                        path,
                        response.status_code,
                    )
                )

    assert not failures, (
        "Cross-tenant operational routes were not "
        f"blocked: {failures}"
    )
