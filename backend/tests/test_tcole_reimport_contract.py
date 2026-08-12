from datetime import date, datetime, timezone

import pytest

from app import create_app
from app.extensions import db
from app.models import (
    Agency,
    Officer,
    OfficerAssignment,
    OfficerAward,
    OfficerCredentialVerification,
    TrainingRecord,
)
from app.services.tcole_import import (
    run_tcole_import,
)


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI":
                "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def make_agency():
    agency = Agency(
        name="Reimport Contract Police Department"
    )

    db.session.add(agency)
    db.session.commit()

    return agency


AWARDS_INITIAL = """P_ID1,OFFICER_NAME1,Type1,Award,Date
484608,"ACOSTA, CELIA",Certificate,Basic Peace Officer,07/29/2022
484608,"ACOSTA, CELIA",License,Peace Officer License,07/30/2020
556622,"ARANZETA, JOE A.",License,Peace Officer License,09/03/2024
"""


COURSES_INITIAL = """P_ID1,P_ID,STUDENT_NAME,PLUS_COURSE_ID,COURSE_ID,COURSE_DATE
1,484608,"ACOSTA, CELIA",,"1849 - De-escalation Tech (SB 1849)",12/12/2019
2,556622,"ARANZETA, JOE A.",,"3189 - State and Federal Law Update",01/15/2026
"""


CYCLE_INITIAL = """Textbox83,PeopleName,P_ID2,Textbox33,Course,COURSE_DATE,Hours
Peace Officer,"ACOSTA, CELIA",484608,Sum Hrs: 4,1849,12/12/2019,4
Peace Officer,"ARANZETA, JOE A.",556622,Sum Hrs: 4,3189,01/15/2026,4
"""


LICENSEE_INITIAL = """P_ID,LNAME,FNAME,MNAME,SFX,GENDER,RACE,SSN,DOB,RecordDesc,RecordName,RecordDate
484608,ACOSTA,CELIA,,,F,White,1234,01/01/1990,Officer Info,,
484608,ACOSTA,CELIA,,,F,White,1234,01/01/1990,License,Peace Officer License,07/30/2020
556622,ARANZETA,JOE,A,,M,White,5678,01/01/1990,Officer Info,,
556622,ARANZETA,JOE,A,,M,White,5678,01/01/1990,License,Peace Officer License,09/03/2024
"""


def initial_import(agency):
    return run_tcole_import(
        agency.id,
        AWARDS_INITIAL,
        COURSES_INITIAL,
        CYCLE_INITIAL,
        LICENSEE_INITIAL,
    )


def test_later_import_adds_new_employee_without_replacing_existing(
    app,
):
    with app.app_context():
        agency = make_agency()
        initial_import(agency)

        original = Officer.query.filter_by(
            agency_id=agency.id,
            tcole_pid="484608",
        ).one()

        original_id = original.id

        awards_updated = AWARDS_INITIAL + (
            '777777,"WILLIAMS, TAYLOR",License,'
            'Peace Officer License,08/01/2026\n'
        )

        licensee_updated = LICENSEE_INITIAL + (
            "777777,WILLIAMS,TAYLOR,,,F,White,9999,"
            "01/01/1995,Officer Info,,\n"
            "777777,WILLIAMS,TAYLOR,,,F,White,9999,"
            "01/01/1995,License,Peace Officer License,"
            "08/01/2026\n"
        )

        run_tcole_import(
            agency.id,
            awards_updated,
            COURSES_INITIAL,
            CYCLE_INITIAL,
            licensee_updated,
        )

        assert Officer.query.filter_by(
            agency_id=agency.id
        ).count() == 3

        preserved = Officer.query.filter_by(
            agency_id=agency.id,
            tcole_pid="484608",
        ).one()

        added = Officer.query.filter_by(
            agency_id=agency.id,
            tcole_pid="777777",
        ).one()

        assert preserved.id == original_id
        assert added.first_name == "TAYLOR"
        assert added.last_name == "WILLIAMS"


def test_later_import_adds_new_certificate_to_existing_employee(
    app,
):
    with app.app_context():
        agency = make_agency()
        initial_import(agency)

        officer = Officer.query.filter_by(
            agency_id=agency.id,
            tcole_pid="484608",
        ).one()

        officer_id = officer.id

        awards_updated = AWARDS_INITIAL + (
            '484608,"ACOSTA, CELIA",Certificate,'
            'Intermediate Peace Officer,08/01/2026\n'
        )

        result = run_tcole_import(
            agency.id,
            awards_updated,
            COURSES_INITIAL,
            CYCLE_INITIAL,
            LICENSEE_INITIAL,
        )

        refreshed = db.session.get(
            Officer,
            officer_id,
        )

        certificate = OfficerAward.query.filter_by(
            agency_id=agency.id,
            officer_id=officer_id,
            award_type="Certificate",
            award_name="Intermediate Peace Officer",
        ).one()

        assert refreshed.id == officer_id
        assert certificate.award_date == date(
            2026,
            8,
            1,
        )
        assert result["awards_created"] == 1


def test_later_import_adds_only_new_training(
    app,
):
    with app.app_context():
        agency = make_agency()
        initial_import(agency)

        officer = Officer.query.filter_by(
            agency_id=agency.id,
            tcole_pid="484608",
        ).one()

        original_records = TrainingRecord.query.filter_by(
            agency_id=agency.id,
            officer_id=officer.id,
        ).count()

        courses_updated = COURSES_INITIAL + (
            '3,484608,"ACOSTA, CELIA",,'
            '"3843 - New Training Course",08/01/2026\n'
        )

        cycle_updated = CYCLE_INITIAL + (
            'Peace Officer,"ACOSTA, CELIA",484608,'
            'Sum Hrs: 8,3843,08/01/2026,4\n'
        )

        result = run_tcole_import(
            agency.id,
            AWARDS_INITIAL,
            courses_updated,
            cycle_updated,
            LICENSEE_INITIAL,
        )

        refreshed_records = TrainingRecord.query.filter_by(
            agency_id=agency.id,
            officer_id=officer.id,
        ).all()

        new_record = TrainingRecord.query.filter_by(
            agency_id=agency.id,
            officer_id=officer.id,
            course_number="3843",
        ).one()

        assert len(refreshed_records) == (
            original_records + 1
        )
        assert result[
            "training_records_created"
        ] == 1
        assert new_record.course_date == date(
            2026,
            8,
            1,
        )


def test_reimport_preserves_all_agency_managed_officer_facts(
    app,
):
    with app.app_context():
        agency = make_agency()
        initial_import(agency)

        officer = Officer.query.filter_by(
            agency_id=agency.id,
            tcole_pid="484608",
        ).one()

        officer.email_override = (
            "special.address@example.gov"
        )
        officer.verified_education_level = (
            "BACHELOR"
        )
        officer.verified_military_months = 72

        assignment = OfficerAssignment(
            agency_id=agency.id,
            officer_id=officer.id,
            assignment_type="SUPERVISOR",
            effective_date=date(
                2026,
                1,
                1,
            ),
        )

        verification = OfficerCredentialVerification(
            agency_id=agency.id,
            officer_id=officer.id,
            credential_type="TDEM_PIO_CERTIFICATION",
            status="VERIFIED",
            effective_date=date(
                2026,
                2,
                1,
            ),
            verified_by="Training Coordinator",
            reference="LOCAL-VERIFY-001",
        )

        db.session.add_all(
            [
                assignment,
                verification,
            ]
        )
        db.session.commit()

        officer_id = officer.id
        assignment_id = assignment.id
        verification_id = verification.id

        run_tcole_import(
            agency.id,
            AWARDS_INITIAL,
            COURSES_INITIAL,
            CYCLE_INITIAL,
            LICENSEE_INITIAL,
        )

        refreshed = db.session.get(
            Officer,
            officer_id,
        )

        preserved_assignment = db.session.get(
            OfficerAssignment,
            assignment_id,
        )

        preserved_verification = db.session.get(
            OfficerCredentialVerification,
            verification_id,
        )

        assert refreshed.email_override == (
            "special.address@example.gov"
        )
        assert (
            refreshed.verified_education_level
            == "BACHELOR"
        )
        assert (
            refreshed.verified_military_months
            == 72
        )

        assert preserved_assignment is not None
        assert (
            preserved_assignment.assignment_type
            == "SUPERVISOR"
        )
        assert preserved_assignment.end_date is None

        assert preserved_verification is not None
        assert (
            preserved_verification.credential_type
            == "TDEM_PIO_CERTIFICATION"
        )
        assert (
            preserved_verification.status
            == "VERIFIED"
        )
        assert (
            preserved_verification.reference
            == "LOCAL-VERIFY-001"
        )


def test_archived_employee_stays_archived_when_present_in_reimport(
    app,
):
    with app.app_context():
        agency = make_agency()
        initial_import(agency)

        officer = Officer.query.filter_by(
            agency_id=agency.id,
            tcole_pid="556622",
        ).one()

        officer_id = officer.id

        officer.employment_status = "archived"
        officer.archived_at = datetime(
            2026,
            8,
            1,
            12,
            0,
            tzinfo=timezone.utc,
        )
        officer.archived_reason = (
            "Separated from agency."
        )

        db.session.commit()

        run_tcole_import(
            agency.id,
            AWARDS_INITIAL,
            COURSES_INITIAL,
            CYCLE_INITIAL,
            LICENSEE_INITIAL,
        )

        refreshed = db.session.get(
            Officer,
            officer_id,
        )

        assert refreshed is not None
        assert refreshed.employment_status == (
            "archived"
        )
        assert refreshed.archived_at is not None
        assert refreshed.archived_reason == (
            "Separated from agency."
        )


def test_reimport_does_not_delete_existing_training_or_awards(
    app,
):
    with app.app_context():
        agency = make_agency()
        initial_import(agency)

        officer = Officer.query.filter_by(
            agency_id=agency.id,
            tcole_pid="484608",
        ).one()

        officer_id = officer.id

        original_award_ids = {
            award.id
            for award in OfficerAward.query.filter_by(
                agency_id=agency.id,
                officer_id=officer_id,
            ).all()
        }

        original_training_ids = {
            record.id
            for record in TrainingRecord.query.filter_by(
                agency_id=agency.id,
                officer_id=officer_id,
            ).all()
        }

        run_tcole_import(
            agency.id,
            AWARDS_INITIAL,
            COURSES_INITIAL,
            CYCLE_INITIAL,
            LICENSEE_INITIAL,
        )

        current_award_ids = {
            award.id
            for award in OfficerAward.query.filter_by(
                agency_id=agency.id,
                officer_id=officer_id,
            ).all()
        }

        current_training_ids = {
            record.id
            for record in TrainingRecord.query.filter_by(
                agency_id=agency.id,
                officer_id=officer_id,
            ).all()
        }

        assert original_award_ids.issubset(
            current_award_ids
        )
        assert original_training_ids.issubset(
            current_training_ids
        )
