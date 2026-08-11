import pytest

from app import create_app
from app.extensions import db
from app.importers.tcole_awards import (
    AwardsImportError,
    import_awards_roster,
    parse_officer_name,
)
from app.models import Agency, Officer, OfficerAward


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
        "suffix": None,
    }


def test_parse_tcole_name_with_middle_and_suffix():
    result = parse_officer_name("AUSMUS JR., JACK J.")

    assert result == {
        "first_name": "JACK",
        "middle_name": "J.",
        "last_name": "AUSMUS",
        "suffix": "JR",
    }


def test_awards_file_creates_officers_and_awards(app):
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

        assert result["rows_processed"] == 4
        assert result["unique_officers"] == 2
        assert result["officers_created"] == 2
        assert result["awards_created"] == 4
        assert result["awards_skipped"] == 0

        assert Officer.query.count() == 2
        assert OfficerAward.query.count() == 4


def test_license_and_certificate_types_are_preserved(app):
    csv_content = """P_ID1,OFFICER_NAME1,Type1,Award,Date
484608,"ACOSTA, CELIA",Certificate,Basic Peace Officer,07/29/2022
484608,"ACOSTA, CELIA",License,Peace Officer License,07/30/2020
"""

    with app.app_context():
        agency = make_agency()

        import_awards_roster(
            agency.id,
            csv_content,
        )

        certificate = OfficerAward.query.filter_by(
            award_type="Certificate"
        ).one()

        license_award = OfficerAward.query.filter_by(
            award_type="License"
        ).one()

        assert certificate.award_name == "Basic Peace Officer"
        assert license_award.award_name == "Peace Officer License"


def test_award_date_is_parsed(app):
    csv_content = """P_ID1,OFFICER_NAME1,Type1,Award,Date
484608,"ACOSTA, CELIA",Certificate,Basic Peace Officer,07/29/2022
"""

    with app.app_context():
        agency = make_agency()

        import_awards_roster(
            agency.id,
            csv_content,
        )

        award = OfficerAward.query.one()

        assert award.award_date.year == 2022
        assert award.award_date.month == 7
        assert award.award_date.day == 29


def test_reimport_does_not_duplicate_awards(app):
    csv_content = """P_ID1,OFFICER_NAME1,Type1,Award,Date
484608,"ACOSTA, CELIA",Certificate,Basic Peace Officer,07/29/2022
484608,"ACOSTA, CELIA",License,Peace Officer License,07/30/2020
"""

    with app.app_context():
        agency = make_agency()

        first = import_awards_roster(
            agency.id,
            csv_content,
        )

        second = import_awards_roster(
            agency.id,
            csv_content,
        )

        assert first["awards_created"] == 2
        assert second["awards_created"] == 0
        assert second["awards_skipped"] == 2

        assert Officer.query.count() == 1
        assert OfficerAward.query.count() == 2


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

        assert Officer.query.filter_by(
            tcole_pid="484608"
        ).count() == 2

        assert OfficerAward.query.count() == 2


def test_invalid_award_type_is_rejected(app):
    csv_content = """P_ID1,OFFICER_NAME1,Type1,Award,Date
484608,"ACOSTA, CELIA",Unknown,Basic Peace Officer,07/29/2022
"""

    with app.app_context():
        agency = make_agency()

        with pytest.raises(AwardsImportError):
            import_awards_roster(
                agency.id,
                csv_content,
            )


def test_invalid_date_rolls_back_entire_import(app):
    csv_content = """P_ID1,OFFICER_NAME1,Type1,Award,Date
484608,"ACOSTA, CELIA",Certificate,Basic Peace Officer,07/29/2022
556622,"ARANZETA, JOE A.",License,Peace Officer License,NOT-A-DATE
"""

    with app.app_context():
        agency = make_agency()

        with pytest.raises(AwardsImportError):
            import_awards_roster(
                agency.id,
                csv_content,
            )

        assert Officer.query.count() == 0
        assert OfficerAward.query.count() == 0


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
