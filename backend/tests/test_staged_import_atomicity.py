from datetime import date
from uuid import UUID

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
import app.services.tcole_import as tcole_import


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


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "AUTHORIZATION_DISABLED": True,
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
        name="Atomicity Test Police Department"
    )
    db.session.add(agency)
    db.session.commit()

    return agency


def get_job(job_id):
    return db.session.get(
        ImportJob,
        job_id,
    )


def test_failed_awards_stage_rolls_back_stage_mutations(
    app,
    monkeypatch,
):
    with app.app_context():
        agency = make_agency()

        def failing_import(
            agency_id,
            content,
            commit=False,
        ):
            officer = Officer(
                agency_id=agency_id,
                tcole_pid="999999",
                first_name="Partial",
                last_name="Mutation",
            )
            db.session.add(officer)
            db.session.flush()

            raise RuntimeError(
                "Injected awards-stage failure."
            )

        monkeypatch.setattr(
            tcole_import,
            "import_awards_roster",
            failing_import,
        )

        with pytest.raises(
            RuntimeError,
            match="Injected awards-stage failure",
        ):
            tcole_import.start_tcole_awards_import(
                agency.id,
                AWARDS,
            )

        assert Officer.query.filter_by(
            agency_id=agency.id
        ).count() == 0

        assert OfficerAward.query.filter_by(
            agency_id=agency.id
        ).count() == 0

        job = ImportJob.query.filter_by(
            agency_id=agency.id
        ).one()

        assert job.status == "failed"
        assert job.error_count == 1
        assert job.failure_reason == (
            "Injected awards-stage failure."
        )
        assert job.completed_at is not None


def test_failed_courses_stage_preserves_awards_and_rolls_back_courses(
    app,
    monkeypatch,
):
    with app.app_context():
        agency = make_agency()

        awards_result = (
            tcole_import.start_tcole_awards_import(
                agency.id,
                AWARDS,
            )
        )

        job_id = UUID(
            awards_result[
                "import_job_id"
            ]
        )

        officer_count_before = (
            Officer.query.filter_by(
                agency_id=agency.id
            ).count()
        )

        award_count_before = (
            OfficerAward.query.filter_by(
                agency_id=agency.id
            ).count()
        )

        training_count_before = (
            TrainingRecord.query.filter_by(
                agency_id=agency.id
            ).count()
        )

        def failing_import(
            agency_id,
            content,
            commit=False,
        ):
            officer = (
                Officer.query
                .filter_by(
                    agency_id=agency_id,
                )
                .first()
            )

            db.session.add(
                TrainingRecord(
                    agency_id=agency_id,
                    officer_id=officer.id,
                    course_number="9999",
                    course_title=(
                        "Partial Transaction Test"
                    ),
                    course_date=date(
                        2026,
                        1,
                        1,
                    ),
                    plus_course_id=None,
                )
            )

            db.session.flush()

            raise RuntimeError(
                "Injected courses-stage failure."
            )

        monkeypatch.setattr(
            tcole_import,
            "import_training_records",
            failing_import,
        )

        with pytest.raises(
            RuntimeError,
            match="Injected courses-stage failure",
        ):
            tcole_import.run_tcole_courses_stage(
                agency.id,
                job_id,
                COURSES,
            )

        assert Officer.query.filter_by(
            agency_id=agency.id
        ).count() == officer_count_before

        assert OfficerAward.query.filter_by(
            agency_id=agency.id
        ).count() == award_count_before

        assert TrainingRecord.query.filter_by(
            agency_id=agency.id
        ).count() == training_count_before

        job = get_job(job_id)

        assert job.status == "failed"
        assert job.error_count == 1
        assert job.failure_reason == (
            "Injected courses-stage failure."
        )


def test_failed_cycle_stage_preserves_prior_stages_and_rolls_back_changes(
    app,
    monkeypatch,
):
    with app.app_context():
        agency = make_agency()

        awards_result = (
            tcole_import.start_tcole_awards_import(
                agency.id,
                AWARDS,
            )
        )

        job_id = UUID(
            awards_result[
                "import_job_id"
            ]
        )

        tcole_import.run_tcole_courses_stage(
            agency.id,
            job_id,
            COURSES,
        )

        record = (
            TrainingRecord.query
            .filter_by(
                agency_id=agency.id,
            )
            .order_by(
                TrainingRecord.course_number
            )
            .first()
        )

        record_id = record.id
        original_hours = record.credited_hours
        original_source = record.hours_source

        officer_count_before = (
            Officer.query.filter_by(
                agency_id=agency.id
            ).count()
        )

        award_count_before = (
            OfficerAward.query.filter_by(
                agency_id=agency.id
            ).count()
        )

        training_count_before = (
            TrainingRecord.query.filter_by(
                agency_id=agency.id
            ).count()
        )

        def failing_import(
            agency_id,
            content,
            commit=False,
        ):
            mutated = db.session.get(
                TrainingRecord,
                record_id,
            )

            mutated.credited_hours = 999
            mutated.hours_source = (
                "INJECTED-FAILED-STAGE"
            )

            db.session.flush()

            raise RuntimeError(
                "Injected cycle-stage failure."
            )

        monkeypatch.setattr(
            tcole_import,
            "import_cycle_hours",
            failing_import,
        )

        with pytest.raises(
            RuntimeError,
            match="Injected cycle-stage failure",
        ):
            tcole_import.run_tcole_cycle_stage(
                agency.id,
                job_id,
                CYCLE,
            )

        db.session.expire_all()

        restored_record = db.session.get(
            TrainingRecord,
            record_id,
        )

        assert restored_record.credited_hours == (
            original_hours
        )

        assert restored_record.hours_source == (
            original_source
        )

        assert Officer.query.filter_by(
            agency_id=agency.id
        ).count() == officer_count_before

        assert OfficerAward.query.filter_by(
            agency_id=agency.id
        ).count() == award_count_before

        assert TrainingRecord.query.filter_by(
            agency_id=agency.id
        ).count() == training_count_before

        job = get_job(job_id)

        assert job.status == "failed"
        assert job.error_count == 1
        assert job.failure_reason == (
            "Injected cycle-stage failure."
        )


def test_failed_licensee_stage_preserves_prior_stages_and_rolls_back_changes(
    app,
    monkeypatch,
):
    with app.app_context():
        agency = make_agency()

        awards_result = (
            tcole_import.start_tcole_awards_import(
                agency.id,
                AWARDS,
            )
        )

        job_id = UUID(
            awards_result[
                "import_job_id"
            ]
        )

        tcole_import.run_tcole_courses_stage(
            agency.id,
            job_id,
            COURSES,
        )

        tcole_import.run_tcole_cycle_stage(
            agency.id,
            job_id,
            CYCLE,
        )

        officer = (
            Officer.query
            .filter_by(
                agency_id=agency.id,
                tcole_pid="484608",
            )
            .one()
        )

        officer_id = officer.id
        original_first_name = (
            officer.first_name
        )

        officer_count_before = (
            Officer.query.filter_by(
                agency_id=agency.id
            ).count()
        )

        award_count_before = (
            OfficerAward.query.filter_by(
                agency_id=agency.id
            ).count()
        )

        training_count_before = (
            TrainingRecord.query.filter_by(
                agency_id=agency.id
            ).count()
        )

        def failing_import(
            agency_id,
            content,
            commit=False,
        ):
            mutated = db.session.get(
                Officer,
                officer_id,
            )

            mutated.first_name = (
                "CORRUPTED-BY-FAILED-STAGE"
            )

            db.session.flush()

            raise RuntimeError(
                "Injected licensee-stage failure."
            )

        monkeypatch.setattr(
            tcole_import,
            "import_licensee_search",
            failing_import,
        )

        with pytest.raises(
            RuntimeError,
            match="Injected licensee-stage failure",
        ):
            (
                tcole_import
                .run_tcole_licensee_search_stage(
                    agency.id,
                    job_id,
                    LICENSEE_SEARCH,
                )
            )

        db.session.expire_all()

        restored_officer = db.session.get(
            Officer,
            officer_id,
        )

        assert restored_officer.first_name == (
            original_first_name
        )

        assert Officer.query.filter_by(
            agency_id=agency.id
        ).count() == officer_count_before

        assert OfficerAward.query.filter_by(
            agency_id=agency.id
        ).count() == award_count_before

        assert TrainingRecord.query.filter_by(
            agency_id=agency.id
        ).count() == training_count_before

        job = get_job(job_id)

        assert job.status == "failed"
        assert job.error_count == 1
        assert job.failure_reason == (
            "Injected licensee-stage failure."
        )
