import pytest

from app import create_app
from app.extensions import db
from app.models import (
    Agency,
    ImportJob,
    Officer,
    OfficerAward,
    TrainingRecord,
)
from app.services.tcole_import import (
    TcoleImportError,
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


def make_agency():
    agency = Agency(name="Test Police Department")
    db.session.add(agency)
    db.session.commit()
    return agency


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


def test_complete_three_file_import(app):
    with app.app_context():
        agency = make_agency()

        result = run_tcole_import(
            agency.id,
            AWARDS,
            COURSES,
            CYCLE,
        )

        assert result["status"] == "completed"
        assert result["officer_count"] == 2
        assert result["awards_created"] == 3
        assert result["training_records_created"] == 2
        assert result["cycle_rows_processed"] == 2
        assert result["training_records_with_hours"] == 2

        assert Officer.query.count() == 2
        assert OfficerAward.query.count() == 3
        assert TrainingRecord.query.count() == 2

        job = ImportJob.query.one()

        assert job.status == "completed"
        assert job.awards_filename == "rptAwards.csv"
        assert job.courses_filename == "rptCourseTaken.csv"
        assert job.cycle_filename == "rptCycleT_All.csv"
        assert job.completed_at is not None


def test_bad_course_file_rolls_back_awards_and_officers(app):
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
            )

        assert Officer.query.count() == 0
        assert OfficerAward.query.count() == 0
        assert TrainingRecord.query.count() == 0

        job = ImportJob.query.one()

        assert job.status == "failed"
        assert job.error_count == 1
        assert job.failure_reason is not None
        assert job.completed_at is not None


def test_bad_awards_file_creates_no_operational_data(app):
    bad_awards = """PID,NAME,AWARD
484608,CELIA ACOSTA,Basic Peace Officer
"""

    with app.app_context():
        agency = make_agency()

        with pytest.raises(Exception):
            run_tcole_import(
                agency.id,
                bad_awards,
                COURSES,
                CYCLE,
            )

        assert Officer.query.count() == 0
        assert OfficerAward.query.count() == 0
        assert TrainingRecord.query.count() == 0

        job = ImportJob.query.one()

        assert job.status == "failed"


def test_reimport_is_idempotent(app):
    with app.app_context():
        agency = make_agency()

        first = run_tcole_import(
            agency.id,
            AWARDS,
            COURSES,
            CYCLE,
        )

        second = run_tcole_import(
            agency.id,
            AWARDS,
            COURSES,
            CYCLE,
        )

        assert first["awards_created"] == 3
        assert first["training_records_created"] == 2

        assert second["awards_created"] == 0
        assert second["training_records_created"] == 0
        assert second["awards_skipped"] == 3
        assert second["training_records_skipped"] == 2

        assert Officer.query.count() == 2
        assert OfficerAward.query.count() == 3
        assert TrainingRecord.query.count() == 2
        assert ImportJob.query.count() == 2


def test_import_is_tenant_scoped(app):
    with app.app_context():
        agency_one = make_agency()

        agency_two = Agency(name="Second Police Department")
        db.session.add(agency_two)
        db.session.commit()

        run_tcole_import(
            agency_one.id,
            AWARDS,
            COURSES,
            CYCLE,
        )

        run_tcole_import(
            agency_two.id,
            AWARDS,
            COURSES,
            CYCLE,
        )

        assert Officer.query.count() == 4
        assert OfficerAward.query.count() == 6
        assert TrainingRecord.query.count() == 4

        assert Officer.query.filter_by(
            agency_id=agency_one.id
        ).count() == 2

        assert Officer.query.filter_by(
            agency_id=agency_two.id
        ).count() == 2


def test_unknown_agency_is_rejected(app):
    import uuid

    with app.app_context():
        with pytest.raises(TcoleImportError):
            run_tcole_import(
                uuid.uuid4(),
                AWARDS,
                COURSES,
                CYCLE,
            )

        assert ImportJob.query.count() == 0


def test_reimport_preserves_agency_managed_officer_data(app):
    from datetime import date

    from app.models import OfficerAssignment

    with app.app_context():
        agency = make_agency()

        run_tcole_import(
            agency.id,
            AWARDS,
            COURSES,
            CYCLE,
        )

        officer = Officer.query.filter_by(
            agency_id=agency.id,
            tcole_pid="484608",
        ).one()

        officer.employment_status = "active"

        assignment = OfficerAssignment(
            agency_id=agency.id,
            officer_id=officer.id,
            assignment_type="PUBLIC_INFORMATION_OFFICER",
            effective_date=date(2026, 1, 1),
        )

        db.session.add(assignment)
        db.session.commit()

        officer_id = officer.id
        assignment_id = assignment.id

        run_tcole_import(
            agency.id,
            AWARDS,
            COURSES,
            CYCLE,
        )

        refreshed = db.session.get(
            Officer,
            officer_id,
        )

        preserved_assignment = db.session.get(
            OfficerAssignment,
            assignment_id,
        )

        assert refreshed is not None
        assert refreshed.employment_status == "active"

        assert preserved_assignment is not None
        assert (
            preserved_assignment.assignment_type
            == "PUBLIC_INFORMATION_OFFICER"
        )
        assert preserved_assignment.end_date is None


def test_missing_from_later_import_does_not_archive_officer(app):
    with app.app_context():
        agency = make_agency()

        run_tcole_import(
            agency.id,
            AWARDS,
            COURSES,
            CYCLE,
        )

        officer = Officer.query.filter_by(
            agency_id=agency.id,
            tcole_pid="556622",
        ).one()

        officer_id = officer.id

        reduced_awards = """P_ID1,OFFICER_NAME1,Type1,Award,Date
484608,"ACOSTA, CELIA",Certificate,Basic Peace Officer,07/29/2022
484608,"ACOSTA, CELIA",License,Peace Officer License,07/30/2020
"""

        reduced_courses = """P_ID1,P_ID,STUDENT_NAME,PLUS_COURSE_ID,COURSE_ID,COURSE_DATE
1,484608,"ACOSTA, CELIA",,"1849 - De-escalation Tech (SB 1849)",12/12/2019
"""

        reduced_cycle = """Textbox83,PeopleName,P_ID2,Textbox33,Course,COURSE_DATE,Hours
Peace Officer,"ACOSTA, CELIA",484608,Sum Hrs: 4,1849,12/12/2019,4
"""

        run_tcole_import(
            agency.id,
            reduced_awards,
            reduced_courses,
            reduced_cycle,
        )

        preserved = db.session.get(
            Officer,
            officer_id,
        )

        assert preserved is not None
        assert preserved.employment_status == "active"
        assert preserved.archived_at is None
