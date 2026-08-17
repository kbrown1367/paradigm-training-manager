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
            "AUTHORIZATION_DISABLED": True,
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


CYCLE = b"""Textbox83,PeopleName,P_ID2,Textbox33,Course,COURSE_DATE,Hours
Peace Officer,"ACOSTA, CELIA",484608,Sum Hrs: 4,1849,12/12/2019,4
Peace Officer,"ARANZETA, JOE A.",556622,Sum Hrs: 4,3189,01/15/2026,4
"""

LICENSEE_SEARCH = b"""P_ID,LNAME,FNAME,MNAME,SFX,GENDER,RACE,SSN,DOB,RecordDesc,RecordName,RecordDate
484608,ACOSTA,CELIA,,,F,White,1234,01/01/1990,Officer Info,,
484608,ACOSTA,CELIA,,,F,White,1234,01/01/1990,License,Peace Officer License,07/30/2020
556622,ARANZETA,JOE,A,,M,White,5678,01/01/1990,Officer Info,,
556622,ARANZETA,JOE,A,,M,White,5678,01/01/1990,License,Peace Officer License,09/03/2024
"""


def import_payload(
    awards=AWARDS,
    courses=COURSES,
    cycle=CYCLE,
    licensee_search=LICENSEE_SEARCH,
):
    return {
        "awards_file": (
            io.BytesIO(awards),
            "rptAwards.csv",
        ),
        "courses_file": (
            io.BytesIO(courses),
            "rptCourseTaken.csv",
        ),
        "cycle_file": (
            io.BytesIO(cycle),
            "rptCycleT_All.csv",
        ),
        "licensee_search_file": (
            io.BytesIO(licensee_search),
            "rptDepartmentOfficerSearch.csv",
        ),
    }


def test_tcole_import_api_accepts_four_files(app):
    with app.app_context():
        agency_id = make_agency()

    client = app.test_client()

    response = client.post(
        f"/api/agencies/{agency_id}/imports/tcole",
        data=import_payload(),
        content_type="multipart/form-data",
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["status"] == "completed"
    assert data["officer_count"] == 2
    assert data["award_rows_processed"] == 3
    assert data["course_rows_processed"] == 2
    assert data["cycle_rows_processed"] == 2
    assert data["training_records_with_hours"] == 2

    with app.app_context():
        assert Officer.query.count() == 2
        assert OfficerAward.query.count() == 3
        assert TrainingRecord.query.count() == 2
        assert ImportJob.query.count() == 1


def test_tcole_import_api_requires_all_four_files(app):
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

    assert response.status_code == 400

    data = response.get_json()

    assert (
        "awards_file, courses_file, cycle_file, and "
        "licensee_search_file are required."
        in data["error"]
    )


def test_tcole_import_api_rejects_bad_file(app):
    with app.app_context():
        agency_id = make_agency()

    client = app.test_client()

    response = client.post(
        f"/api/agencies/{agency_id}/imports/tcole",
        data=import_payload(
            awards=b"PID,NAME\n1,TEST\n",
        ),
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
        data=import_payload(),
        content_type="multipart/form-data",
    )

    assert import_response.status_code == 201

    import_data = import_response.get_json()

    summary_response = client.get(
        f"/api/agencies/{agency_id}/imports/{import_data['import_job_id']}"
    )

    assert summary_response.status_code == 200

    summary = summary_response.get_json()

    assert summary["import_job_id"] == import_data["import_job_id"]
    assert summary["status"] == "completed"
    assert summary["cycle_rows_processed"] == 2
    assert summary["training_records_with_hours"] == 2


def test_import_summary_api_is_tenant_scoped(app):
    with app.app_context():
        agency_one_id = make_agency("Agency One")
        agency_two_id = make_agency("Agency Two")

    client = app.test_client()

    import_response = client.post(
        f"/api/agencies/{agency_one_id}/imports/tcole",
        data=import_payload(),
        content_type="multipart/form-data",
    )

    assert import_response.status_code == 201

    import_data = import_response.get_json()

    response = client.get(
        f"/api/agencies/{agency_two_id}/imports/{import_data['import_job_id']}"
    )

    assert response.status_code == 404



def single_file_payload(content, filename):
    return {
        "file": (
            io.BytesIO(content),
            filename,
        )
    }


def test_staged_tcole_import_completes_in_required_order(app):
    with app.app_context():
        agency_id = make_agency()

    client = app.test_client()

    awards_response = client.post(
        f"/api/agencies/{agency_id}/imports/tcole/awards",
        data=single_file_payload(
            AWARDS,
            "rptAwards.csv",
        ),
        content_type="multipart/form-data",
    )

    assert awards_response.status_code == 201
    awards_data = awards_response.get_json()

    assert awards_data["status"] == "awards_completed"
    assert awards_data["officer_count"] == 2
    assert awards_data["award_rows_processed"] == 3

    import_job_id = awards_data["import_job_id"]

    courses_response = client.post(
        f"/api/agencies/{agency_id}/imports/tcole/"
        f"{import_job_id}/courses",
        data=single_file_payload(
            COURSES,
            "rptCourseTaken.csv",
        ),
        content_type="multipart/form-data",
    )

    assert courses_response.status_code == 200
    courses_data = courses_response.get_json()

    assert courses_data["status"] == "courses_completed"
    assert courses_data["course_rows_processed"] == 2

    cycle_response = client.post(
        f"/api/agencies/{agency_id}/imports/tcole/"
        f"{import_job_id}/cycle",
        data=single_file_payload(
            CYCLE,
            "rptCycleT_All.csv",
        ),
        content_type="multipart/form-data",
    )

    assert cycle_response.status_code == 200
    cycle_data = cycle_response.get_json()

    assert cycle_data["status"] == "cycle_completed"
    assert cycle_data["cycle_rows_processed"] == 2
    assert cycle_data["training_records_with_hours"] == 2

    license_response = client.post(
        f"/api/agencies/{agency_id}/imports/tcole/"
        f"{import_job_id}/licensee-search",
        data=single_file_payload(
            LICENSEE_SEARCH,
            "rptDepartmentOfficerSearch.csv",
        ),
        content_type="multipart/form-data",
    )

    assert license_response.status_code == 200
    final_data = license_response.get_json()

    assert final_data["status"] == "completed"
    assert final_data["officer_count"] == 2
    assert final_data["award_rows_processed"] == 3
    assert final_data["course_rows_processed"] == 2
    assert final_data["cycle_rows_processed"] == 2
    assert final_data["licensee_search_rows_processed"] == 4

    with app.app_context():
        assert Officer.query.count() == 2
        assert OfficerAward.query.count() == 3
        assert TrainingRecord.query.count() == 2
        assert ImportJob.query.count() == 1


def test_staged_tcole_import_rejects_out_of_order_step(app):
    with app.app_context():
        agency_id = make_agency()

    client = app.test_client()

    awards_response = client.post(
        f"/api/agencies/{agency_id}/imports/tcole/awards",
        data=single_file_payload(
            AWARDS,
            "rptAwards.csv",
        ),
        content_type="multipart/form-data",
    )

    assert awards_response.status_code == 201
    import_job_id = awards_response.get_json()[
        "import_job_id"
    ]

    cycle_response = client.post(
        f"/api/agencies/{agency_id}/imports/tcole/"
        f"{import_job_id}/cycle",
        data=single_file_payload(
            CYCLE,
            "rptCycleT_All.csv",
        ),
        content_type="multipart/form-data",
    )

    assert cycle_response.status_code == 400
    assert (
        "Course History must be completed"
        in cycle_response.get_json()["error"]
    )


def test_failed_staged_import_is_audited(app):
    from app.models import AuditEvent

    with app.app_context():
        agency_id = make_agency()

    client = app.test_client()

    awards_response = client.post(
        f"/api/agencies/{agency_id}"
        "/imports/tcole/awards",
        data=single_file_payload(
            AWARDS,
            "rptAwards.csv",
        ),
        content_type="multipart/form-data",
    )

    assert awards_response.status_code == 201

    import_job_id = (
        awards_response.get_json()[
            "import_job_id"
        ]
    )

    # Cycle is intentionally attempted before
    # Course History so this request must fail.
    cycle_response = client.post(
        f"/api/agencies/{agency_id}"
        f"/imports/tcole/{import_job_id}/cycle",
        data=single_file_payload(
            CYCLE,
            "rptCycleT_All.csv",
        ),
        content_type="multipart/form-data",
    )

    assert cycle_response.status_code == 400

    with app.app_context():
        event = (
            AuditEvent.query.filter_by(
                agency_id=agency_id,
                event_type=(
                    "TCOLE_IMPORT_CYCLE_FAILED"
                ),
            )
            .order_by(
                AuditEvent.created_at.desc()
            )
            .first()
        )

        assert event is not None
        assert event.object_type == "IMPORT_JOB"
        assert event.object_id == str(import_job_id)
        assert event.result == "failure"
        assert event.details["stage"] == "cycle"
        assert event.details["filename"] == (
            "rptCycleT_All.csv"
        )
        assert event.details["error"]
