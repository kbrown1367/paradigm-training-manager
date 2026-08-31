import pytest

from app import create_app
from app.extensions import db
from app.importers.tcole_cycle import (
    CycleImportError,
    import_cycle_hours,
)
from app.models import (
    Agency,
    Officer,
    TrainingCredit,
    TrainingRecord,
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


def make_training_record():
    agency = Agency(name="Test Police Department")
    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="256684",
        first_name="KENNETH",
        last_name="BROWN JR.",
    )
    db.session.add(officer)
    db.session.flush()

    record = TrainingRecord(
        agency_id=agency.id,
        officer_id=officer.id,
        course_number="2107",
        course_title="Example Course",
        course_date=__import__("datetime").date(2000, 10, 20),
    )
    db.session.add(record)
    db.session.commit()

    return agency, officer, record


def test_cycle_hours_match_training_record(app):
    csv_content = """Textbox83,PeopleName,P_ID2,Textbox33,Course,COURSE_DATE,Hours
Peace Officer,"BROWN JR., KENNETH R.",256684,Sum Hrs: 100,2107,10/20/2000,6
"""

    with app.app_context():
        agency, _, record = make_training_record()

        result = import_cycle_hours(
            agency.id,
            csv_content,
        )

        db.session.refresh(record)

        assert result["rows_processed"] == 1
        assert result["training_records_matched"] == 1
        assert result["credits_created"] == 1
        assert float(record.credited_hours) == 6.0
        assert record.hours_source == "TCOLE_CYCLE_REPORT"
        assert TrainingCredit.query.count() == 1


def test_multiple_cycle_rows_are_summed(app):
    csv_content = """Textbox83,PeopleName,P_ID2,Textbox33,Course,COURSE_DATE,Hours
Peace Officer,"BROWN JR., KENNETH R.",256684,Sum Hrs: 100,2107,10/20/2000,16
Peace Officer,"BROWN JR., KENNETH R.",256684,Sum Hrs: 100,2107,10/20/2000,6
"""

    with app.app_context():
        agency, _, record = make_training_record()

        result = import_cycle_hours(
            agency.id,
            csv_content,
        )

        db.session.refresh(record)

        assert result["rows_processed"] == 2
        assert result["training_records_matched"] == 1
        assert result["credits_created"] == 2
        assert float(record.credited_hours) == 22.0
        assert TrainingCredit.query.count() == 2


def test_reimport_does_not_duplicate_credit_rows(app):
    csv_content = """Textbox83,PeopleName,P_ID2,Textbox33,Course,COURSE_DATE,Hours
Peace Officer,"BROWN JR., KENNETH R.",256684,Sum Hrs: 100,2107,10/20/2000,6
"""

    with app.app_context():
        agency, _, _ = make_training_record()

        first = import_cycle_hours(
            agency.id,
            csv_content,
        )

        second = import_cycle_hours(
            agency.id,
            csv_content,
        )

        assert first["credits_created"] == 1
        assert second["credits_created"] == 0
        assert second["credits_skipped"] == 1
        assert TrainingCredit.query.count() == 1


def test_unknown_training_record_rolls_back(app):
    csv_content = """Textbox83,PeopleName,P_ID2,Textbox33,Course,COURSE_DATE,Hours
Peace Officer,"BROWN JR., KENNETH R.",256684,Sum Hrs: 100,9999,10/20/2000,6
"""

    with app.app_context():
        agency, _, record = make_training_record()

        with pytest.raises(CycleImportError):
            import_cycle_hours(
                agency.id,
                csv_content,
            )

        db.session.refresh(record)

        assert record.credited_hours is None
        assert TrainingCredit.query.count() == 0


def test_invalid_hours_are_rejected(app):
    csv_content = """Textbox83,PeopleName,P_ID2,Textbox33,Course,COURSE_DATE,Hours
Peace Officer,"BROWN JR., KENNETH R.",256684,Sum Hrs: 100,2107,10/20/2000,NOT-HOURS
"""

    with app.app_context():
        agency, _, _ = make_training_record()

        with pytest.raises(CycleImportError):
            import_cycle_hours(
                agency.id,
                csv_content,
            )


def test_cycle_handles_multiple_course_history_matches_once(app):
    """One Cycle row must not be multiplied by duplicate history matches."""
    csv_content = """Textbox83,PeopleName,P_ID2,Textbox33,Course,COURSE_DATE,Hours
Peace Officer,"BROWN JR., KENNETH R.",256684,Sum Hrs: 100,66300,10/20/2000,18
"""

    with app.app_context():
        agency = Agency(name="Pilot Police Department")
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="256684",
            first_name="KENNETH",
            last_name="BROWN JR.",
        )
        db.session.add(officer)
        db.session.flush()

        original = TrainingRecord(
            agency_id=agency.id,
            officer_id=officer.id,
            course_number="66300",
            course_title=(
                "FEMA Int. ICS Exp. Incident (Class Rm) "
                "(FEMA IS-300)"
            ),
            course_date=__import__("datetime").date(
                2000,
                10,
                20,
            ),
            credited_hours=18,
            hours_source="TCOLE_CYCLE_REPORT",
        )

        alternate = TrainingRecord(
            agency_id=agency.id,
            officer_id=officer.id,
            course_number="66300",
            course_title=(
                "FEMA Int. ICS Exp. Incident(FEMA IS-300)"
            ),
            course_date=__import__("datetime").date(
                2000,
                10,
                20,
            ),
        )

        db.session.add_all([original, alternate])
        db.session.commit()

        result = import_cycle_hours(
            agency.id,
            csv_content,
        )

        db.session.refresh(original)
        db.session.refresh(alternate)

        assert result["rows_processed"] == 1
        assert result["training_records_matched"] == 1

        credited_total = sum(
            float(record.credited_hours or 0)
            for record in (original, alternate)
        )

        assert credited_total == 18.0
        assert float(original.credited_hours) == 18.0
        assert alternate.credited_hours is None


def test_multiple_cycle_rows_survive_ambiguous_history_match(app):
    """Cycle rows, not Course History candidates, control credited hours."""
    csv_content = """Textbox83,PeopleName,P_ID2,Textbox33,Course,COURSE_DATE,Hours
Peace Officer,"BROWN JR., KENNETH R.",256684,Sum Hrs: 100,66300,10/20/2000,16
Peace Officer,"BROWN JR., KENNETH R.",256684,Sum Hrs: 100,66300,10/20/2000,6
"""

    with app.app_context():
        agency = Agency(name="Pilot Police Department")
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="256684",
            first_name="KENNETH",
            last_name="BROWN JR.",
        )
        db.session.add(officer)
        db.session.flush()

        first_record = TrainingRecord(
            agency_id=agency.id,
            officer_id=officer.id,
            course_number="66300",
            course_title="First TCOLE Description",
            course_date=__import__("datetime").date(
                2000,
                10,
                20,
            ),
        )

        second_record = TrainingRecord(
            agency_id=agency.id,
            officer_id=officer.id,
            course_number="66300",
            course_title="Later TCOLE Description",
            course_date=__import__("datetime").date(
                2000,
                10,
                20,
            ),
        )

        db.session.add_all([first_record, second_record])
        db.session.commit()

        result = import_cycle_hours(
            agency.id,
            csv_content,
        )

        db.session.refresh(first_record)
        db.session.refresh(second_record)

        credited_total = sum(
            float(record.credited_hours or 0)
            for record in (first_record, second_record)
        )

        assert result["rows_processed"] == 2
        assert result["credits_created"] == 2
        assert credited_total == 22.0
        assert TrainingCredit.query.count() == 2
