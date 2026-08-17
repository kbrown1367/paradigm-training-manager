import pytest
from uuid import UUID

from app import create_app
from app.auth import (
    ROLE_AGENCY_ADMIN,
    ROLE_PLATFORM_ADMIN,
    hash_password,
    verify_password,
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
                "platform-admin-test-secret",
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
def data(app):
    with app.app_context():
        agency = Agency(
            name="Pilot Police Department"
        )

        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="100001",
            first_name="Pilot",
            last_name="Officer",
        )

        agency_admin = User(
            agency_id=agency.id,
            email="agency@example.gov",
            password_hash=hash_password(
                "AgencyPassword123!"
            ),
            first_name="Agency",
            last_name="Admin",
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
            last_name="Admin",
            role=ROLE_PLATFORM_ADMIN,
            status="active",
        )

        db.session.add_all(
            [
                officer,
                agency_admin,
                platform_admin,
            ]
        )

        db.session.commit()

        return {
            "agency_id":
                str(agency.id),
            "agency_admin_id":
                str(agency_admin.id),
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


def test_platform_routes_require_authentication(
    app,
    data,
):
    client = app.test_client()

    response = client.get(
        "/api/platform/agencies"
    )

    assert response.status_code == 401


def test_agency_admin_cannot_access_platform_routes(
    app,
    data,
):
    client = app.test_client()

    login(
        client,
        "agency@example.gov",
        "AgencyPassword123!",
    )

    response = client.get(
        "/api/platform/agencies"
    )

    assert response.status_code == 404


def test_platform_admin_can_list_agencies(
    app,
    data,
):
    client = app.test_client()

    login(
        client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    response = client.get(
        "/api/platform/agencies"
    )

    assert response.status_code == 200

    agencies = response.get_json()

    assert len(agencies) == 1
    assert agencies[0]["name"] == (
        "Pilot Police Department"
    )
    assert agencies[0][
        "active_employee_count"
    ] == 1
    assert agencies[0][
        "administrator_count"
    ] == 1


def test_platform_admin_can_create_agency(
    app,
    data,
):
    client = app.test_client()

    login(
        client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    response = client.post(
        "/api/platform/agencies",
        json={
            "name":
                "Second Police Department",
            "tcole_agency_number":
                "123456",
            "ori":
                "TX1234567",
        },
    )

    assert response.status_code == 201

    result = response.get_json()

    assert result["name"] == (
        "Second Police Department"
    )
    assert result[
        "administrator_count"
    ] == 0


def test_platform_admin_can_create_multiple_agency_admins(
    app,
    data,
):
    client = app.test_client()

    login(
        client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    agency_id = data["agency_id"]

    for index in range(
        2,
        5,
    ):
        response = client.post(
            f"/api/platform/agencies/{agency_id}"
            "/administrators",
            json={
                "first_name":
                    f"Admin{index}",
                "last_name":
                    "User",
                "email":
                    f"admin{index}@example.gov",
                "password":
                    "PilotPassword123!",
            },
        )

        assert response.status_code == 201

    response = client.get(
        f"/api/platform/agencies/{agency_id}"
    )

    assert response.status_code == 200

    result = response.get_json()

    assert result[
        "administrator_count"
    ] == 4

    assert len(
        result["administrators"]
    ) == 4


def test_new_agency_admin_can_activate_and_is_bound_to_agency(
    app,
    data,
):
    platform_client = app.test_client()

    login(
        platform_client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    agency_id = data["agency_id"]

    response = platform_client.post(
        f"/api/platform/agencies/{agency_id}"
        "/administrators",
        json={
            "first_name": "Second",
            "last_name": "Admin",
            "email":
                "second@example.gov",
        },
    )

    assert response.status_code == 201

    result = response.get_json()

    assert result["status"] == (
        "pending_invitation"
    )

    token = result[
        "invitation_path"
    ].split(
        "?token=",
        1,
    )[1]

    activation = platform_client.post(
        "/api/auth/activate-invitation",
        json={
            "token": token,
            "password":
                "SecondPassword123!",
        },
    )

    assert activation.status_code == 200

    agency_client = app.test_client()

    login(
        agency_client,
        "second@example.gov",
        "SecondPassword123!",
    )

    me = agency_client.get(
        "/api/auth/me"
    )

    assert me.status_code == 200

    user = me.get_json()["user"]

    assert user["agency_id"] == agency_id
    assert user["role"] == (
        ROLE_AGENCY_ADMIN
    )


def test_duplicate_admin_email_is_rejected(
    app,
    data,
):
    client = app.test_client()

    login(
        client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    response = client.post(
        "/api/platform/agencies/"
        f"{data['agency_id']}"
        "/administrators",
        json={
            "first_name": "Duplicate",
            "last_name": "User",
            "email":
                "agency@example.gov",
            "password":
                "DuplicatePassword123!",
        },
    )

    assert response.status_code == 409


def test_platform_admin_can_deactivate_agency_admin(
    app,
    data,
):
    client = app.test_client()

    login(
        client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    response = client.patch(
        "/api/platform/agencies/"
        f"{data['agency_id']}"
        "/administrators/"
        f"{data['agency_admin_id']}",
        json={
            "status": "inactive",
        },
    )

    assert response.status_code == 200
    assert (
        response.get_json()["status"]
        == "inactive"
    )

    login_response = app.test_client().post(
        "/api/auth/login",
        json={
            "email":
                "agency@example.gov",
            "password":
                "AgencyPassword123!",
        },
    )

    assert login_response.status_code == 401


def test_platform_admin_can_reset_admin_password(
    app,
    data,
):
    client = app.test_client()

    login(
        client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    response = client.post(
        "/api/platform/agencies/"
        f"{data['agency_id']}"
        "/administrators/"
        f"{data['agency_admin_id']}"
        "/reset-password",
        json={
            "password":
                "NewPassword123!",
        },
    )

    assert response.status_code == 200

    with app.app_context():
        user = User.query.filter_by(
            email="agency@example.gov"
        ).one()

        assert verify_password(
            user.password_hash,
            "NewPassword123!",
        )


def test_platform_admin_can_update_agency(
    app,
    data,
):
    client = app.test_client()

    login(
        client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    response = client.patch(
        "/api/platform/agencies/"
        f"{data['agency_id']}",
        json={
            "tcole_agency_number":
                "987654",
            "ori":
                "TX7654321",
            "status":
                "inactive",
        },
    )

    assert response.status_code == 200

    result = response.get_json()

    assert result[
        "tcole_agency_number"
    ] == "987654"

    assert result["status"] == (
        "inactive"
    )


def test_admin_creation_no_longer_accepts_password(
    app,
    data,
):
    client = app.test_client()

    login(
        client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    response = client.post(
        "/api/platform/agencies/"
        f"{data['agency_id']}"
        "/administrators",
        json={
            "first_name": "Invited",
            "last_name": "Administrator",
            "email":
                "invited@example.gov",
            "password":
                "IgnoredPassword123!",
        },
    )

    assert response.status_code == 201

    result = response.get_json()

    assert result["status"] == (
        "pending_invitation"
    )

    assert "invitation_path" in result


def test_platform_admin_can_view_agency_login_activity(
    app,
    data,
):
    from datetime import datetime, timedelta, timezone

    from app.auth import hash_password
    from app.extensions import db
    from app.models import Agency, AuditEvent, User

    with app.app_context():
        agency = Agency(
            name="Activity Test Police Department",
            status="active",
        )
        db.session.add(agency)
        db.session.flush()

        agency_admin = User(
            agency_id=agency.id,
            email="activity-admin@example.gov",
            password_hash=hash_password(
                "ActivityPassword123!"
            ),
            first_name="Activity",
            last_name="Administrator",
            role="AGENCY_ADMIN",
            status="active",
        )
        db.session.add(agency_admin)
        db.session.flush()

        now = datetime.now(timezone.utc)

        db.session.add_all(
            [
                AuditEvent(
                    agency_id=agency.id,
                    user_id=agency_admin.id,
                    event_type="AUTH_LOGIN_SUCCESS",
                    created_at=now - timedelta(days=1),
                ),
                AuditEvent(
                    agency_id=agency.id,
                    user_id=agency_admin.id,
                    event_type="AUTH_LOGIN_SUCCESS",
                    created_at=now - timedelta(days=5),
                ),
                AuditEvent(
                    agency_id=agency.id,
                    user_id=agency_admin.id,
                    event_type="AUTH_LOGIN_SUCCESS",
                    created_at=now - timedelta(days=20),
                ),
                AuditEvent(
                    agency_id=agency.id,
                    user_id=agency_admin.id,
                    event_type="AUTH_LOGIN_SUCCESS",
                    created_at=now - timedelta(days=40),
                ),
            ]
        )

        db.session.commit()

        agency_id = agency.id

    client = app.test_client()

    login(
        client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    response = client.get(
        f"/api/platform/agencies/{agency_id}/activity"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["agency_name"] == (
        "Activity Test Police Department"
    )
    assert data["logins_7_days"] == 2
    assert data["logins_30_days"] == 3
    assert data["active_admins_30_days"] == 1
    assert len(data["recent_activity"]) >= 4

    login_events = [
        event
        for event in data["recent_activity"]
        if event["event_type"]
        == "AUTH_LOGIN_SUCCESS"
    ]

    assert len(login_events) == 4

    first_login = login_events[0]

    assert first_login["user"]["email"] == (
        "activity-admin@example.gov"
    )


def test_platform_activity_endpoint_includes_non_login_events(
    app,
    data,
):
    from datetime import datetime, timezone
    from uuid import UUID

    from app.extensions import db
    from app.models import AuditEvent

    with app.app_context():
        db.session.add(
            AuditEvent(
                agency_id=UUID(
                    data["agency_id"]
                ),
                user_id=UUID(
                    data["agency_admin_id"]
                ),
                event_type=(
                    "TCOLE_IMPORT_COURSES_UPLOADED"
                ),
                object_type="IMPORT_JOB",
                object_id="test-import-job",
                result="success",
                details={
                    "filename":
                        "rptCourseTaken.csv",
                    "course_rows_processed": 42,
                },
                created_at=datetime.now(
                    timezone.utc
                ),
            )
        )

        db.session.commit()

    client = app.test_client()

    login(
        client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    response = client.get(
        "/api/platform/agencies/"
        f"{data['agency_id']}"
        "/activity"
    )

    assert response.status_code == 200

    activity = response.get_json()[
        "recent_activity"
    ]

    event = next(
        item
        for item in activity
        if item["event_type"]
        == "TCOLE_IMPORT_COURSES_UPLOADED"
    )

    assert event["result"] == "success"
    assert event["object_type"] == "IMPORT_JOB"
    assert event["object_id"] == "test-import-job"
    assert event["details"]["filename"] == (
        "rptCourseTaken.csv"
    )



def test_platform_activity_summary_lists_agencies(
    app,
    data,
):
    client = app.test_client()

    login(
        client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    response = client.get(
        "/api/platform/activity/agencies"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert isinstance(data, list)

    assert all(
        "agency_id" in item
        and "agency_name" in item
        and "last_login_at" in item
        and "logins_7_days" in item
        and "logins_30_days" in item
        and "active_admins_30_days" in item
        for item in data
    )


def test_non_platform_admin_cannot_view_activity(app):
    from app.auth import hash_password
    from app.extensions import db
    from app.models import Agency, User

    with app.app_context():
        agency = Agency(
            name="Activity Security Police Department",
            status="active",
        )
        db.session.add(agency)
        db.session.flush()

        user = User(
            agency_id=agency.id,
            email="activity-security@example.gov",
            password_hash=hash_password(
                "ActivitySecurity123!"
            ),
            first_name="Agency",
            last_name="Administrator",
            role="AGENCY_ADMIN",
            status="active",
        )
        db.session.add(user)
        db.session.commit()

    client = app.test_client()

    login = client.post(
        "/api/auth/login",
        json={
            "email": "activity-security@example.gov",
            "password": "ActivitySecurity123!",
        },
    )

    assert login.status_code == 200

    response = client.get(
        "/api/platform/activity/agencies"
    )

    assert response.status_code == 404


def test_platform_admin_can_archive_and_restore_agency(
    app,
    data,
):
    platform_client = app.test_client()

    login(
        platform_client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    archive = platform_client.post(
        "/api/platform/agencies/"
        f"{data['agency_id']}"
        "/archive"
    )

    assert archive.status_code == 200
    assert archive.get_json()["status"] == (
        "archived"
    )

    blocked_login = app.test_client().post(
        "/api/auth/login",
        json={
            "email":
                "agency@example.gov",
            "password":
                "AgencyPassword123!",
        },
    )

    assert blocked_login.status_code == 401

    restore = platform_client.post(
        "/api/platform/agencies/"
        f"{data['agency_id']}"
        "/restore"
    )

    assert restore.status_code == 200
    assert restore.get_json()["status"] == (
        "active"
    )

    restored_login = app.test_client().post(
        "/api/auth/login",
        json={
            "email":
                "agency@example.gov",
            "password":
                "AgencyPassword123!",
        },
    )

    assert restored_login.status_code == 200


def test_archiving_agency_invalidates_existing_session(
    app,
    data,
):
    agency_client = app.test_client()

    login(
        agency_client,
        "agency@example.gov",
        "AgencyPassword123!",
    )

    platform_client = app.test_client()

    login(
        platform_client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    archive = platform_client.post(
        "/api/platform/agencies/"
        f"{data['agency_id']}"
        "/archive"
    )

    assert archive.status_code == 200

    me = agency_client.get(
        "/api/auth/me"
    )

    assert me.status_code == 401


def test_platform_admin_cannot_delete_active_agency(
    app,
    data,
):
    client = app.test_client()

    login(
        client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    response = client.delete(
        "/api/platform/agencies/"
        f"{data['agency_id']}",
        json={
            "confirmation_name":
                "Pilot Police Department",
        },
    )

    assert response.status_code == 409

    with app.app_context():
        assert Agency.query.filter_by(
            id=UUID(data["agency_id"])
        ).one_or_none() is not None


def test_platform_admin_delete_requires_exact_agency_name(
    app,
    data,
):
    client = app.test_client()

    login(
        client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    archive = client.post(
        "/api/platform/agencies/"
        f"{data['agency_id']}"
        "/archive"
    )

    assert archive.status_code == 200

    response = client.delete(
        "/api/platform/agencies/"
        f"{data['agency_id']}",
        json={
            "confirmation_name":
                "Wrong Agency Name",
        },
    )

    assert response.status_code == 400

    with app.app_context():
        assert Agency.query.filter_by(
            id=UUID(data["agency_id"])
        ).one_or_none() is not None


def test_platform_admin_can_permanently_delete_archived_agency(
    app,
    data,
):
    from app.models import AuditEvent

    client = app.test_client()

    login(
        client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    archive = client.post(
        "/api/platform/agencies/"
        f"{data['agency_id']}"
        "/archive"
    )

    assert archive.status_code == 200

    response = client.delete(
        "/api/platform/agencies/"
        f"{data['agency_id']}",
        json={
            "confirmation_name":
                "Pilot Police Department",
        },
    )

    assert response.status_code == 200

    result = response.get_json()

    assert result["deleted"] is True
    assert result["agency_id"] == (
        data["agency_id"]
    )

    with app.app_context():
        assert Agency.query.filter_by(
            id=UUID(data["agency_id"])
        ).one_or_none() is None

        assert Officer.query.filter_by(
            agency_id=UUID(data["agency_id"])
        ).count() == 0

        assert User.query.filter_by(
            agency_id=UUID(data["agency_id"])
        ).count() == 0

        deletion_event = (
            AuditEvent.query.filter(
                AuditEvent.event_type
                == (
                    "PLATFORM_AGENCY_DELETED:"
                    f"{data['agency_id']}"
                )
            ).one_or_none()
        )

        assert deletion_event is not None
        assert deletion_event.agency_id is None


def test_agency_purge_plan_covers_all_agency_owned_tables(
    app,
):
    from app.platform_routes import (
        AGENCY_PURGE_MODELS,
    )

    with app.app_context():
        agency_owned_tables = {
            table.name
            for table in db.metadata.tables.values()
            if "agency_id" in table.columns
        }

        purge_tables = {
            model.__tablename__
            for model in AGENCY_PURGE_MODELS
        }

        assert purge_tables == agency_owned_tables


def test_platform_admin_can_list_retained_tcole_files(
    app,
    data,
):
    from uuid import UUID

    from app.extensions import db
    from app.models import ImportJob
    from app.services.retained_tcole_files import (
        FILE_TYPE_AWARDS,
        retain_tcole_file,
    )

    with app.app_context():
        agency_id = UUID(data["agency_id"])

        job = ImportJob(
            agency_id=agency_id,
            status="completed",
        )
        db.session.add(job)
        db.session.flush()

        retain_tcole_file(
            agency_id=agency_id,
            import_job_id=job.id,
            file_type=FILE_TYPE_AWARDS,
            filename="rptAwards.csv",
            content=b"column,value\\none,two\\n",
        )

        db.session.commit()

    client = app.test_client()

    login(
        client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    response = client.get(
        "/api/platform/agencies/"
        f"{data['agency_id']}"
        "/tcole-files"
    )

    assert response.status_code == 200

    result = response.get_json()

    assert result["agency_id"] == (
        data["agency_id"]
    )
    assert result["retention_days"] == 90
    assert len(result["files"]) == 1

    retained = result["files"][0]

    assert retained["file_type"] == "awards"
    assert retained["original_filename"] == (
        "rptAwards.csv"
    )
    assert retained["size_bytes"] > 0
    assert len(retained["sha256"]) == 64
    assert retained["uploaded_at"]
    assert retained["expires_at"]

    assert "content" not in retained


def test_platform_admin_can_download_retained_tcole_file(
    app,
    data,
):
    from uuid import UUID

    from app.extensions import db
    from app.models import (
        AuditEvent,
        ImportJob,
    )
    from app.services.retained_tcole_files import (
        FILE_TYPE_COURSES,
        retain_tcole_file,
    )

    content = (
        b"P_ID,COURSE_ID\\n"
        b"123456,3189\\n"
    )

    with app.app_context():
        agency_id = UUID(data["agency_id"])

        job = ImportJob(
            agency_id=agency_id,
            status="completed",
        )
        db.session.add(job)
        db.session.flush()

        retained = retain_tcole_file(
            agency_id=agency_id,
            import_job_id=job.id,
            file_type=FILE_TYPE_COURSES,
            filename="rptCourseTaken.csv",
            content=content,
        )

        retained_id = retained.id

        db.session.commit()

    client = app.test_client()

    login(
        client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    response = client.get(
        "/api/platform/agencies/"
        f"{data['agency_id']}"
        "/tcole-files/courses/download"
    )

    assert response.status_code == 200
    assert response.data == content

    disposition = response.headers.get(
        "Content-Disposition",
        "",
    )

    assert "attachment" in disposition
    assert "rptCourseTaken.csv" in disposition

    with app.app_context():
        event = (
            AuditEvent.query
            .filter_by(
                agency_id=UUID(
                    data["agency_id"]
                ),
                event_type=(
                    "PLATFORM_TCOLE_FILE_DOWNLOADED"
                ),
            )
            .order_by(
                AuditEvent.created_at.desc()
            )
            .first()
        )

        assert event is not None
        assert event.object_type == (
            "RETAINED_TCOLE_FILE"
        )
        assert event.object_id == str(
            retained_id
        )
        assert event.result == "success"
        assert event.details["file_type"] == (
            "courses"
        )
        assert event.details["filename"] == (
            "rptCourseTaken.csv"
        )


def test_agency_admin_cannot_access_retained_tcole_files(
    app,
    data,
):
    client = app.test_client()

    login(
        client,
        "agency@example.gov",
        "AgencyPassword123!",
    )

    list_response = client.get(
        "/api/platform/agencies/"
        f"{data['agency_id']}"
        "/tcole-files"
    )

    download_response = client.get(
        "/api/platform/agencies/"
        f"{data['agency_id']}"
        "/tcole-files/awards/download"
    )

    assert list_response.status_code == 404
    assert download_response.status_code == 404


def test_expired_retained_file_is_not_available_to_platform_admin(
    app,
    data,
):
    from datetime import timedelta
    from uuid import UUID

    from app.extensions import db
    from app.models import (
        ImportJob,
        RetainedTcoleFile,
        utcnow,
    )
    from app.services.retained_tcole_files import (
        FILE_TYPE_AWARDS,
        retain_tcole_file,
    )

    with app.app_context():
        agency_id = UUID(data["agency_id"])

        job = ImportJob(
            agency_id=agency_id,
            status="completed",
        )
        db.session.add(job)
        db.session.flush()

        retained = retain_tcole_file(
            agency_id=agency_id,
            import_job_id=job.id,
            file_type=FILE_TYPE_AWARDS,
            filename="expired.csv",
            content=b"expired",
        )

        retained.expires_at = (
            utcnow() - timedelta(seconds=1)
        )

        db.session.commit()

    client = app.test_client()

    login(
        client,
        "platform@paradigm.local",
        "PlatformPassword123!",
    )

    list_response = client.get(
        "/api/platform/agencies/"
        f"{data['agency_id']}"
        "/tcole-files"
    )

    assert list_response.status_code == 200
    assert list_response.get_json()["files"] == []

    download_response = client.get(
        "/api/platform/agencies/"
        f"{data['agency_id']}"
        "/tcole-files/awards/download"
    )

    assert download_response.status_code == 404

    with app.app_context():
        assert (
            RetainedTcoleFile.query
            .filter_by(
                agency_id=UUID(
                    data["agency_id"]
                )
            )
            .count()
            == 0
        )
