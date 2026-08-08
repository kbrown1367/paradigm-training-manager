import pytest

from app import create_app
from app.extensions import db
from app.importers.tcole_awards import (
    AwardsImportError,
    import_awards_roster,
    parse_officer_name,
)
from app.models import Agency, Officer


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
    return agency


def test_parse_simple_tcole_name():
    result = parse_officer_name("ACOSTA, CELIA")

    assert result == {
        "first_name": "CELIA",
        "middle_name": None,
        "last_name": "ACOSTA",
    }


def test_parse_tcole_name_with_middle_and_suffix():
    result = parse_officer_name("AUSMUS JR., JACK J.")

    assert result == {
        "first_name": "JACK",
        "middle_name": "J.",
        "last_name": "AUSMUS JR.",
    }


def test_awards_file_creates_unique_officers(app):
    csv_content = """P_ID1,OFFICER_NAME1,Type1,Award,Date
484608,"ACOSTA, CELIA",Certificate,Basic Peace Officer,07/29/2022
484608,"ACOSTA, CELIA",Certificate,Intermediate Peace Officer,08/20/2025
484608,"ACOSTA, CELIA",License,Peace Officer License,07/30/2020
556622,"ARANZETA, JOE A.",License,Peace Officer License,09/03/2024
"""

    with app.app_context():
        agency = make_agency()

        result = import_awards_roster(
            agency.id,
            csv_content,
        )

        officers = Officer.query.order_by(Officer.tcole_pid).all()

        assert result["rows_processed"] == 4
        assert result["unique_officers"] == 2
        assert result["officers_created"] == 2
        assert result["officers_updated"] == 0

        assert len(officers) == 2

        assert officers[0].tcole_pid == "484608"
        assert officers[0].first_name == "CELIA"
        assert officers[0].last_name == "ACOSTA"

        assert officers[1].tcole_pid == "556622"
        assert officers[1].first_name == "JOE"
        assert officers[1].middle_name == "A."
        assert officers[1].last_name == "ARANZETA"


def test_reimport_updates_existing_officer_without_duplicate(app):
    original = """P_ID1,OFFICER_NAME1,Type1,Award,Date
484608,"ACOSTA, CELIA",License,Peace Officer License,07/30/2020
"""

    updated = """P_ID1,OFFICER_NAME1,Type1,Award,Date
484608,"ACOSTA, CELIA M.",License,Peace Officer License,07/30/2020
"""

    with app.app_context():
        agency = make_agency()

        first_result = import_awards_roster(
            agency.id,
            original,
        )

        second_result = import_awards_roster(
            agency.id,
            updated,
        )

        officers = Officer.query.all()

        assert first_result["officers_created"] == 1
        assert second_result["officers_created"] == 0
        assert second_result["officers_updated"] == 1

        assert len(officers) == 1
        assert officers[0].middle_name == "M."


def test_same_pid_is_isolated_between_agencies(app):
    csv_content = """P_ID1,OFFICER_NAME1,Type1,Award,Date
484608,"ACOSTA, CELIA",License,Peace Officer License,07/30/2020
"""

    with app.app_context():
        agency_one = make_agency("Agency One")
        agency_two = make_agency("Agency Two")

        import_awards_roster(
            agency_one.id,
            csv_content,
        )

        import_awards_roster(
            agency_two.id,
            csv_content,
        )

        officers = Officer.query.filter_by(
            tcole_pid="484608"
        ).all()

        assert len(officers) == 2
        assert officers[0].agency_id != officers[1].agency_id


def test_invalid_file_is_rejected(app):
    csv_content = """PID,Name,Award
484608,CELIA ACOSTA,Basic Peace Officer
"""

    with app.app_context():
        agency = make_agency()

        with pytest.raises(AwardsImportError):
            import_awards_roster(
                agency.id,
                csv_content,
            )
