import io

import pytest

from app import create_app
from app.extensions import db
from app.models import Agency, ImportJob, Officer, OfficerAward, TrainingRecord


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def make_agency(name="Test Police Department"):
    agency = Agency(name=name)
    db.session.add(agency)
    db.session.commit()
    return agency.id


AWARDS = b"""P_ID1,OFFICER_NAME1,Type1,Award,Date
484608,"ACOSTA, CELIA",Certificate,Basic Peace Officer,07/29/2022
484608,"ACOSTA, CELIA",License,Peace Officer License,07/30/2020
556622,"ARANZETA, JOE A.",License,Peace Officer License,09/03/2024
"""


COURSES = b"""P_ID1,P_ID,STUDENT_NAME,PLUS_COURSE_ID,COURSE_ID,COURSE_DATE
1,484608,"ACOSTA, CELIA",,"1849 - De-escalation Tech (SB 1849)",12/12/2019
2,556622,"ARANZETA, JOE A.",,"3189 - State and Federal Law Update",01/15/2026
"""


def test_tcole_import_api_accepts_two_files(app):
    with app.app_context():
        agency_id = make_agency()

    client = app.test_client()

    response = client.post(
        f"/api/agencies/{agency_id}/imports/tcole",
        data={
            "awards_file": (
                io.BytesIO(AWARDS),
                "rptAwards.csv",
            ),
            "courses_file": (
                io.BytesIO(COURSES),
                "rptCourseTaken.csv",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["status"] == "completed"
    assert data["officer_count"] == 2
    assert data["award_rows_processed"] == 3
    assert data["course_rows_processed"] == 2

    with app.app_context():
        assert Officer.query.count() == 2
        assert OfficerAward.query.count() == 3
        assert TrainingRecord.query.count() == 2
        assert ImportJob.query.count() == 1


def test_tcole_import_api_requires_both_files(app):
    with app.app_context():
        agency_id = make_agency()

    client = app.test_client()

    response = client.post(
        f"/api/agencies/{agency_id}/imports/tcole",
        data={
            "awards_file": (
                io.BytesIO(AWARDS),
                "rptAwards.csv",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400

    data = response.get_json()

    assert "Both awards_file and courses_file are required." in data["error"]


def test_tcole_import_api_rejects_bad_file(app):
    with app.app_context():
        agency_id = make_agency()

    client = app.test_client()

    response = client.post(
        f"/api/agencies/{agency_id}/imports/tcole",
        data={
            "awards_file": (
                io.BytesIO(b"PID,NAME\n1,TEST\n"),
                "rptAwards.csv",
            ),
            "courses_file": (
                io.BytesIO(COURSES),
                "rptCourseTaken.csv",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400

    with app.app_context():
        assert Officer.query.count() == 0
        assert OfficerAward.query.count() == 0
        assert TrainingRecord.query.count() == 0
        assert ImportJob.query.count() == 1
        assert ImportJob.query.one().status == "failed"


def test_import_summary_api_returns_saved_result(app):
    with app.app_context():
        agency_id = make_agency()

    client = app.test_client()

    import_response = client.post(
        f"/api/agencies/{agency_id}/imports/tcole",
        data={
            "awards_file": (
                io.BytesIO(AWARDS),
                "rptAwards.csv",
            ),
            "courses_file": (
                io.BytesIO(COURSES),
                "rptCourseTaken.csv",
            ),
        },
        content_type="multipart/form-data",
    )

    import_data = import_response.get_json()

    summary_response = client.get(
        f"/api/agencies/{agency_id}/imports/{import_data['import_job_id']}"
    )

    assert summary_response.status_code == 200

    summary = summary_response.get_json()

    assert summary["import_job_id"] == import_data["import_job_id"]
    assert summary["status"] == "completed"


def test_import_summary_api_is_tenant_scoped(app):
    with app.app_context():
        agency_one_id = make_agency("Agency One")
        agency_two_id = make_agency("Agency Two")

    client = app.test_client()

    import_response = client.post(
        f"/api/agencies/{agency_one_id}/imports/tcole",
        data={
            "awards_file": (
                io.BytesIO(AWARDS),
                "rptAwards.csv",
            ),
            "courses_file": (
                io.BytesIO(COURSES),
                "rptCourseTaken.csv",
            ),
        },
        content_type="multipart/form-data",
    )

    import_data = import_response.get_json()

    response = client.get(
        f"/api/agencies/{agency_two_id}/imports/{import_data['import_job_id']}"
    )

    assert response.status_code == 404
