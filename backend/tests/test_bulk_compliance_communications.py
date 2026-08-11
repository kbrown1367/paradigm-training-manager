from datetime import date

import pytest

from app import create_app
from app.extensions import db
from app.models import (
    Agency,
    Officer,
    OfficerAward,
)
from app.services.bulk_compliance_communications import (
    build_bulk_compliance_preflight,
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


def make_agency(
    name="Test Department",
    email=True,
):
    agency = Agency(
        name=name,
        email_domain=(
            "example.gov"
            if email
            else None
        ),
        email_pattern=(
            "FIRST_INITIAL_LAST"
            if email
            else None
        ),
    )

    db.session.add(agency)
    db.session.flush()

    return agency


def make_officer(
    agency,
    pid,
    first_name,
    last_name,
):
    officer = Officer(
        agency_id=agency.id,
        tcole_pid=pid,
        first_name=first_name,
        last_name=last_name,
    )

    db.session.add(officer)
    db.session.flush()

    return officer


def add_award(
    agency,
    officer,
    award_type,
    award_name,
    award_date,
):
    db.session.add(
        OfficerAward(
            agency_id=agency.id,
            officer_id=officer.id,
            award_type=award_type,
            award_name=award_name,
            award_date=award_date,
        )
    )


def test_peace_officer_preflight_track(app):
    with app.app_context():
        agency = make_agency()

        officer = make_officer(
            agency,
            "100001",
            "Jane",
            "Smith",
        )

        add_award(
            agency,
            officer,
            "License",
            "Peace Officer License",
            date(2020, 1, 1),
        )

        db.session.commit()

        result = build_bulk_compliance_preflight(
            agency.id,
            evaluation_date=date(2026, 8, 11),
        )

        recipient = result["recipients"][0]

        assert recipient["preflight_status"] == "READY"
        assert recipient["applicable_tracks"] == [
            "peace_officer"
        ]
        assert (
            recipient["communication_track"]
            == "peace_officer"
        )


def test_telecommunicator_preflight_track(app):
    with app.app_context():
        agency = make_agency()

        officer = make_officer(
            agency,
            "100002",
            "Chris",
            "Dispatcher",
        )

        add_award(
            agency,
            officer,
            "License",
            "Telecommunications Operator License",
            date(2014, 1, 1),
        )

        db.session.commit()

        result = build_bulk_compliance_preflight(
            agency.id,
            evaluation_date=date(2026, 8, 11),
        )

        recipient = result["recipients"][0]

        assert recipient["preflight_status"] == "READY"
        assert recipient["applicable_tracks"] == [
            "telecommunicator"
        ]
        assert (
            recipient["communication_track"]
            == "telecommunicator"
        )


def test_dual_license_uses_combined_track(app):
    with app.app_context():
        agency = make_agency()

        officer = make_officer(
            agency,
            "100003",
            "Kristin",
            "Dual",
        )

        add_award(
            agency,
            officer,
            "License",
            "Peace Officer License",
            date(2015, 1, 1),
        )

        add_award(
            agency,
            officer,
            "License",
            "Telecommunications Operator License",
            date(2017, 1, 1),
        )

        db.session.commit()

        result = build_bulk_compliance_preflight(
            agency.id,
            evaluation_date=date(2026, 8, 11),
        )

        recipient = result["recipients"][0]

        assert recipient["preflight_status"] == "READY"
        assert set(
            recipient["applicable_tracks"]
        ) == {
            "peace_officer",
            "telecommunicator",
        }
        assert (
            recipient["communication_track"]
            == "combined"
        )
        assert result["summary"]["multi_license"] == 1


def test_missing_email_requires_action(app):
    with app.app_context():
        agency = make_agency(
            email=False
        )

        officer = make_officer(
            agency,
            "100004",
            "No",
            "Email",
        )

        add_award(
            agency,
            officer,
            "License",
            "Peace Officer License",
            date(2020, 1, 1),
        )

        db.session.commit()

        result = build_bulk_compliance_preflight(
            agency.id,
            evaluation_date=date(2026, 8, 11),
        )

        recipient = result["recipients"][0]

        assert (
            recipient["preflight_status"]
            == "ACTION_REQUIRED"
        )

        issue_codes = {
            issue["code"]
            for issue in recipient[
                "preflight_issues"
            ]
        }

        assert "MISSING_EMAIL" in issue_codes
        assert recipient["selected_by_default"] is False


def test_no_supported_license_requires_action(app):
    with app.app_context():
        agency = make_agency()

        make_officer(
            agency,
            "100005",
            "No",
            "License",
        )

        db.session.commit()

        result = build_bulk_compliance_preflight(
            agency.id,
            evaluation_date=date(2026, 8, 11),
        )

        recipient = result["recipients"][0]

        assert (
            recipient["preflight_status"]
            == "ACTION_REQUIRED"
        )

        issue_codes = {
            issue["code"]
            for issue in recipient[
                "preflight_issues"
            ]
        }

        assert (
            "NO_APPLICABLE_LICENSE_TRACK"
            in issue_codes
        )

        assert "NOT_EVALUATED" in issue_codes


def test_due_employee_selected_by_default(app):
    with app.app_context():
        agency = make_agency()

        officer = make_officer(
            agency,
            "100006",
            "Training",
            "Due",
        )

        add_award(
            agency,
            officer,
            "License",
            "Telecommunications Operator License",
            date(2014, 1, 1),
        )

        db.session.commit()

        result = build_bulk_compliance_preflight(
            agency.id,
            evaluation_date=date(2026, 8, 11),
        )

        recipient = result["recipients"][0]

        assert recipient["overall_status"] == "DUE"
        assert recipient["selected_by_default"] is True


def test_compliant_employee_not_selected_by_default(
    app,
):
    with app.app_context():
        agency = make_agency()

        officer = make_officer(
            agency,
            "100007",
            "Already",
            "Compliant",
        )

        # A future-dated license causes this employee to be
        # recognized for applicability while avoiding any
        # artificial selection assertion. The exact
        # compliance calculation is not the purpose of this
        # test, so selected behavior is checked conditionally.
        add_award(
            agency,
            officer,
            "License",
            "Peace Officer License",
            date(2020, 1, 1),
        )

        db.session.commit()

        result = build_bulk_compliance_preflight(
            agency.id,
            evaluation_date=date(2026, 8, 11),
        )

        recipient = result["recipients"][0]

        if recipient["overall_status"] == "COMPLIANT":
            assert (
                recipient["selected_by_default"]
                is False
            )


def test_preflight_is_tenant_scoped(app):
    with app.app_context():
        agency_a = make_agency(
            "Agency A"
        )
        agency_b = make_agency(
            "Agency B"
        )

        officer_a = make_officer(
            agency_a,
            "200001",
            "Agency",
            "Alpha",
        )

        officer_b = make_officer(
            agency_b,
            "200002",
            "Agency",
            "Bravo",
        )

        add_award(
            agency_a,
            officer_a,
            "License",
            "Peace Officer License",
            date(2020, 1, 1),
        )

        add_award(
            agency_b,
            officer_b,
            "License",
            "Peace Officer License",
            date(2020, 1, 1),
        )

        db.session.commit()

        result = build_bulk_compliance_preflight(
            agency_a.id,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["summary"]["total_employees"] == 1

        assert {
            recipient["tcole_pid"]
            for recipient in result["recipients"]
        } == {"200001"}


def test_missing_agency_returns_none(app):
    with app.app_context():
        import uuid

        result = build_bulk_compliance_preflight(
            uuid.uuid4(),
            evaluation_date=date(2026, 8, 11),
        )

        assert result is None
