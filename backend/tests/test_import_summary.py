import pytest

from app import create_app
from app.extensions import db
from app.models import Agency, ImportJob
from app.services.tcole_import import (
    TcoleImportError,
    get_import_summary,
    run_tcole_import,
)


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


AWARDS = """P_ID1,OFFICER_NAME1,Type1,Award,Date
484608,"ACOSTA, CELIA",Certificate,Basic Peace Officer,07/29/2022
484608,"ACOSTA, CELIA",License,Peace Officer License,07/30/2020
556622,"ARANZETA, JOE A.",License,Peace Officer License,09/03/2024
"""


COURSES = """P_ID1,P_ID,STUDENT_NAME,PLUS_COURSE_ID,COURSE_ID,COURSE_DATE
1,484608,"ACOSTA, CELIA",,"1849 - De-escalation Tech (SB 1849)",12/12/2019
2,556622,"ARANZETA, JOE A.",,"3189 - State and Federal Law Update",01/15/2026
"""


CYCLE = """Textbox83,PeopleName,P_ID2,Textbox33,Course,COURSE_DATE,Hours
Peace Officer,"ACOSTA, CELIA",484608,Sum Hrs: 4,1849,12/12/2019,4
Peace Officer,"ARANZETA, JOE A.",556622,Sum Hrs: 4,3189,01/15/2026,4
"""

LICENSEE_SEARCH = """P_ID,LNAME,FNAME,MNAME,SFX,GENDER,RACE,SSN,DOB,RecordDesc,RecordName,RecordDate
484608,ACOSTA,CELIA,,,F,White,1234,01/01/1990,Officer Info,,
484608,ACOSTA,CELIA,,,F,White,1234,01/01/1990,License,Peace Officer License,07/30/2020
556622,ARANZETA,JOE,A,,M,White,5678,01/01/1990,Officer Info,,
556622,ARANZETA,JOE,A,,M,White,5678,01/01/1990,License,Peace Officer License,09/03/2024
"""


def make_agency(name="Test Police Department"):
    agency = Agency(name=name)
    db.session.add(agency)
    db.session.commit()
    return agency


def test_completed_import_returns_full_summary(app):
    with app.app_context():
        agency = make_agency()

        result = run_tcole_import(
            agency.id,
            AWARDS,
            COURSES,
            CYCLE,
            LICENSEE_SEARCH,
        )

        assert result["status"] == "completed"
        assert result["officer_count"] == 2
        assert result["award_rows_processed"] == 3
        assert result["course_rows_processed"] == 2
        assert result["cycle_rows_processed"] == 2
        assert result["training_records_with_hours"] == 2
        assert result["awards_created"] == 3
        assert result["training_records_created"] == 2
        assert result["awards_skipped"] == 0
        assert result["training_records_skipped"] == 0
        assert result["warning_count"] == 0
        assert result["error_count"] == 0
        assert result["failure_reason"] is None
        assert result["started_at"] is not None
        assert result["completed_at"] is not None


def test_import_summary_can_be_retrieved(app):
    with app.app_context():
        agency = make_agency()

        result = run_tcole_import(
            agency.id,
            AWARDS,
            COURSES,
            CYCLE,
            LICENSEE_SEARCH,
        )

        summary = get_import_summary(
            result["import_job_id"],
            agency.id,
        )

        assert summary["import_job_id"] == result["import_job_id"]
        assert summary["officer_count"] == 2
        assert summary["award_rows_processed"] == 3
        assert summary["course_rows_processed"] == 2
        assert summary["cycle_rows_processed"] == 2
        assert summary["training_records_with_hours"] == 2


def test_reimport_summary_reports_skipped_records(app):
    with app.app_context():
        agency = make_agency()

        run_tcole_import(
            agency.id,
            AWARDS,
            COURSES,
            CYCLE,
            LICENSEE_SEARCH,
        )

        second = run_tcole_import(
            agency.id,
            AWARDS,
            COURSES,
            CYCLE,
            LICENSEE_SEARCH,
        )

        assert second["awards_created"] == 0
        assert second["training_records_created"] == 0
        assert second["awards_skipped"] == 3
        assert second["training_records_skipped"] == 2


def test_import_summary_is_tenant_scoped(app):
    with app.app_context():
        agency_one = make_agency("Agency One")
        agency_two = make_agency("Agency Two")

        result = run_tcole_import(
            agency_one.id,
            AWARDS,
            COURSES,
            CYCLE,
            LICENSEE_SEARCH,
        )

        with pytest.raises(TcoleImportError):
            get_import_summary(
                result["import_job_id"],
                agency_two.id,
            )


def test_failed_import_summary_persists_failure(app):
    bad_courses = """P_ID1,P_ID,STUDENT_NAME,PLUS_COURSE_ID,COURSE_ID,COURSE_DATE
1,999999,"UNKNOWN, PERSON",,"3189 - State and Federal Law Update",01/15/2026
"""

    with app.app_context():
        agency = make_agency()

        with pytest.raises(Exception):
            run_tcole_import(
                agency.id,
                AWARDS,
                bad_courses,
                CYCLE,
                LICENSEE_SEARCH,
            )

        job = ImportJob.query.one()

        summary = get_import_summary(
            job.id,
            agency.id,
        )

        assert summary["status"] == "failed"
        assert summary["error_count"] == 1
        assert summary["failure_reason"] is not None
        assert summary["completed_at"] is not None
