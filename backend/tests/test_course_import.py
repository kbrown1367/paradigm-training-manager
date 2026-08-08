import pytest

from app import create_app
from app.extensions import db
from app.importers.tcole_courses import (
    CourseImportError,
    import_training_records,
    parse_course,
)
from app.models import Agency, Officer, TrainingRecord


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


def make_agency_and_officer():
    agency = Agency(name="Test Police Department")

    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="484608",
        first_name="CELIA",
        last_name="ACOSTA",
    )

    db.session.add(officer)
    db.session.commit()

    return agency, officer


def test_parse_course():
    number, title = parse_course(
        "1849 - De-escalation Tech (SB 1849)",
        2,
    )

    assert number == "1849"
    assert title == "De-escalation Tech (SB 1849)"


def test_course_file_creates_training_records(app):
    csv_content = """P_ID1,P_ID,STUDENT_NAME,PLUS_COURSE_ID,COURSE_ID,COURSE_DATE
1,484608,"ACOSTA, CELIA",,"1033 - Chapter 33 Rule Overview Exam",08/07/2019
2,484608,"ACOSTA, CELIA",,"1849 - De-escalation Tech (SB 1849)",12/12/2019
"""

    with app.app_context():
        agency, officer = make_agency_and_officer()

        result = import_training_records(
            agency.id,
            csv_content,
        )

        assert result["rows_processed"] == 2
        assert result["unique_officers"] == 1
        assert result["training_records_created"] == 2
        assert result["training_records_skipped"] == 0

        assert TrainingRecord.query.count() == 2

        record = TrainingRecord.query.filter_by(
            course_number="1849"
        ).one()

        assert record.officer_id == officer.id
        assert record.course_title == "De-escalation Tech (SB 1849)"


def test_plus_course_id_is_preserved(app):
    csv_content = """P_ID1,P_ID,STUDENT_NAME,PLUS_COURSE_ID,COURSE_ID,COURSE_DATE
1,484608,"ACOSTA, CELIA",2106,"2106 - Crime Scene Investigation (Intermediate)",03/05/2015
"""

    with app.app_context():
        agency, _ = make_agency_and_officer()

        import_training_records(
            agency.id,
            csv_content,
        )

        record = TrainingRecord.query.one()

        assert record.plus_course_id == "2106"


def test_duplicate_rows_are_skipped(app):
    csv_content = """P_ID1,P_ID,STUDENT_NAME,PLUS_COURSE_ID,COURSE_ID,COURSE_DATE
1,484608,"ACOSTA, CELIA",,"1849 - De-escalation Tech (SB 1849)",12/12/2019
2,484608,"ACOSTA, CELIA",,"1849 - De-escalation Tech (SB 1849)",12/12/2019
"""

    with app.app_context():
        agency, _ = make_agency_and_officer()

        result = import_training_records(
            agency.id,
            csv_content,
        )

        assert result["training_records_created"] == 1
        assert result["training_records_skipped"] == 1
        assert TrainingRecord.query.count() == 1


def test_reimport_does_not_duplicate_training(app):
    csv_content = """P_ID1,P_ID,STUDENT_NAME,PLUS_COURSE_ID,COURSE_ID,COURSE_DATE
1,484608,"ACOSTA, CELIA",,"1849 - De-escalation Tech (SB 1849)",12/12/2019
"""

    with app.app_context():
        agency, _ = make_agency_and_officer()

        first = import_training_records(
            agency.id,
            csv_content,
        )

        second = import_training_records(
            agency.id,
            csv_content,
        )

        assert first["training_records_created"] == 1
        assert second["training_records_created"] == 0
        assert second["training_records_skipped"] == 1
        assert TrainingRecord.query.count() == 1


def test_unknown_officer_rolls_back_import(app):
    csv_content = """P_ID1,P_ID,STUDENT_NAME,PLUS_COURSE_ID,COURSE_ID,COURSE_DATE
1,484608,"ACOSTA, CELIA",,"1849 - De-escalation Tech (SB 1849)",12/12/2019
2,999999,"UNKNOWN, PERSON",,"3189 - State and Federal Law Update",01/01/2026
"""

    with app.app_context():
        agency, _ = make_agency_and_officer()

        with pytest.raises(CourseImportError):
            import_training_records(
                agency.id,
                csv_content,
            )

        assert TrainingRecord.query.count() == 0


def test_invalid_date_rolls_back_import(app):
    csv_content = """P_ID1,P_ID,STUDENT_NAME,PLUS_COURSE_ID,COURSE_ID,COURSE_DATE
1,484608,"ACOSTA, CELIA",,"1849 - De-escalation Tech (SB 1849)",NOT-A-DATE
"""

    with app.app_context():
        agency, _ = make_agency_and_officer()

        with pytest.raises(CourseImportError):
            import_training_records(
                agency.id,
                csv_content,
            )

        assert TrainingRecord.query.count() == 0


def test_invalid_file_is_rejected(app):
    csv_content = """PID,NAME,COURSE
484608,CELIA ACOSTA,1849
"""

    with app.app_context():
        agency, _ = make_agency_and_officer()

        with pytest.raises(CourseImportError):
            import_training_records(
                agency.id,
                csv_content,
            )
