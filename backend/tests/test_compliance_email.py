from datetime import date
from decimal import Decimal

import pytest

from app import create_app
from app.extensions import db
from app.models import (
    Agency,
    Officer,
    OfficerAward,
    TrainingRecord,
)
from app.services.compliance_email import (
    build_compliance_email,
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


def make_officer():
    agency = Agency(
        name="Test Police Department",
        email_domain="example.gov",
        email_pattern="FIRST_INITIAL_LAST",
    )

    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="123456",
        first_name="Jane",
        last_name="Smith",
    )

    db.session.add(officer)
    db.session.flush()

    db.session.add(
        OfficerAward(
            agency_id=agency.id,
            officer_id=officer.id,
            award_type="License",
            award_name="Peace Officer License",
            award_date=date(2020, 1, 1),
        )
    )

    db.session.add(
        TrainingRecord(
            agency_id=agency.id,
            officer_id=officer.id,
            course_number="9999",
            course_title="General Training",
            course_date=date(2026, 1, 1),
            credited_hours=Decimal("8.00"),
            hours_source="TCOLE",
            source="TCOLE",
        )
    )

    db.session.commit()

    return officer


def test_compliance_email_uses_resolved_address(app):
    with app.app_context():
        officer = make_officer()

        result = build_compliance_email(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["recipient"] == (
            "jsmith@example.gov"
        )
        assert result["can_email"] is True


def test_compliance_email_contains_status(app):
    with app.app_context():
        officer = make_officer()

        result = build_compliance_email(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert "Current Status:" in result["body"]
        assert (
            "TCOLE Peace Officer Compliance Status"
            == result["subject"]
        )


def test_compliance_email_contains_due_items(app):
    with app.app_context():
        officer = make_officer()

        result = build_compliance_email(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert (
            "OUTSTANDING REQUIREMENTS"
            in result["body"]
        )
        assert "Due 8/31/2027" in result["body"]


def test_compliance_email_without_address_is_disabled(
    app,
):
    with app.app_context():
        officer = make_officer()

        officer.agency.email_domain = None
        officer.agency.email_pattern = None
        db.session.commit()

        result = build_compliance_email(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["recipient"] is None
        assert result["can_email"] is False


def test_compliance_email_includes_suffix_in_display_name(app):
    with app.app_context():
        officer = make_officer()

        officer.first_name = "Jack"
        officer.middle_name = "J."
        officer.last_name = "Ausmus"
        officer.suffix = "JR"

        db.session.commit()

        result = build_compliance_email(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["employee_name"] == (
            "Jack J. Ausmus JR"
        )

        # The suffix must not become part of the
        # generated email address.
        assert result["recipient"] == (
            "jausmus@example.gov"
        )


def test_compliance_email_includes_proficiency_progress(app):
    with app.app_context():
        officer = make_officer()

        officer.peace_officer_service_start_date = date(
            2020,
            1,
            1,
        )

        db.session.add(
            OfficerAward(
                agency_id=officer.agency_id,
                officer_id=officer.id,
                award_type="Certificate",
                award_name="Basic Peace Officer",
                award_date=date(2021, 1, 1),
            )
        )

        db.session.commit()

        result = build_compliance_email(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        body = result["body"]

        assert "PEACE OFFICER PROFICIENCY" in body
        assert (
            "Current Certificate: Basic Peace Officer"
            in body
        )
        assert (
            "Next Certificate: Intermediate Peace Officer"
            in body
        )
        assert (
            "REMAINING CERTIFICATE REQUIREMENTS"
            in body
        )
        assert (
            "Proficiency certificate requirements are "
            "separate from your current legislative "
            "training compliance requirements."
            in body
        )


def test_master_peace_officer_email_has_no_next_certificate(app):
    with app.app_context():
        officer = make_officer()

        officer.peace_officer_service_start_date = date(
            2000,
            1,
            1,
        )

        db.session.add(
            OfficerAward(
                agency_id=officer.agency_id,
                officer_id=officer.id,
                award_type="Certificate",
                award_name="Master Peace Officer",
                award_date=date(2025, 1, 1),
            )
        )

        db.session.commit()

        result = build_compliance_email(
            officer,
            evaluation_date=date(2026, 8, 10),
        )

        body = result["body"]

        assert "PEACE OFFICER PROFICIENCY" in body
        assert (
            "Current Certificate: Master Peace Officer"
            in body
        )
        assert "Next Certificate:" not in body
        assert (
            "Master Peace Officer is the highest "
            "Peace Officer proficiency certificate."
            in body
        )


def test_proficiency_email_formats_remaining_courses_cleanly(app):
    with app.app_context():
        officer = make_officer()

        officer.peace_officer_service_start_date = date(
            2022,
            1,
            1,
        )

        db.session.add(
            OfficerAward(
                agency_id=officer.agency_id,
                officer_id=officer.id,
                award_type="Certificate",
                award_name="Basic Peace Officer",
                award_date=date(2023, 1, 1),
            )
        )

        db.session.commit()

        result = build_compliance_email(
            officer,
            evaluation_date=date(2026, 8, 10),
        )

        body = result["body"]

        assert "Accepted courses:" in body
        assert "Required course:" in body
        assert "TCOLE #" in body


def make_jailer():
    agency = Agency(
        name="Test Sheriff's Office",
        email_domain="example.gov",
        email_pattern="FIRST_INITIAL_LAST",
    )

    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="700001",
        first_name="John",
        last_name="Jailer",
        jailer_service_start_date=date(
            2020,
            1,
            1,
        ),
    )

    db.session.add(officer)
    db.session.flush()

    db.session.add(
        OfficerAward(
            agency_id=agency.id,
            officer_id=officer.id,
            award_type="License",
            award_name="Jailer License",
            award_date=date(2020, 1, 1),
        )
    )

    db.session.commit()

    return officer


def test_jailer_email_includes_basic_progress(app):
    with app.app_context():
        officer = make_jailer()

        db.session.add(
            TrainingRecord(
                agency_id=officer.agency_id,
                officer_id=officer.id,
                course_number="1999",
                course_title="Personnel Orientation",
                course_date=date(2020, 1, 1),
                credited_hours=Decimal("8"),
                hours_source="TCOLE",
                source="TCOLE",
            )
        )

        db.session.commit()

        result = build_compliance_email(
            officer,
            evaluation_date=date(2026, 8, 11),
            track="jailer",
        )

        body = result["body"]

        assert "COUNTY JAILER PROFICIENCY" in body
        assert (
            "Current Certificate: None identified"
            in body
        )
        assert "Next Certificate: Basic Jailer" in body
        assert (
            "County Correction Officer Field Training"
            in body
        )
        assert "Required course: TCOLE #3721" in body
        assert (
            body.count(
                "County Correction Officer Field Training"
            )
            == 1
        )


def test_basic_jailer_email_advances_to_intermediate(app):
    with app.app_context():
        officer = make_jailer()

        db.session.add(
            OfficerAward(
                agency_id=officer.agency_id,
                officer_id=officer.id,
                award_type="Certificate",
                award_name="Basic Jailer",
                award_date=date(2021, 1, 1),
            )
        )

        db.session.commit()

        result = build_compliance_email(
            officer,
            evaluation_date=date(2026, 8, 11),
            track="jailer",
        )

        body = result["body"]

        assert "COUNTY JAILER PROFICIENCY" in body
        assert (
            "Current Certificate: Basic Jailer"
            in body
        )
        assert (
            "Next Certificate: Intermediate Jailer"
            in body
        )


def test_master_jailer_email_has_no_next_certificate(app):
    with app.app_context():
        officer = make_jailer()

        db.session.add(
            OfficerAward(
                agency_id=officer.agency_id,
                officer_id=officer.id,
                award_type="Certificate",
                award_name="Master Jailer Proficiency",
                award_date=date(2025, 1, 1),
            )
        )

        db.session.commit()

        result = build_compliance_email(
            officer,
            evaluation_date=date(2026, 8, 11),
            track="jailer",
        )

        body = result["body"]

        assert "COUNTY JAILER PROFICIENCY" in body
        assert (
            "Current Certificate: Master Jailer"
            in body
        )
        assert (
            "HIGHEST CERTIFICATE ACHIEVED"
            in body
        )
        assert (
            "Master Jailer is the highest County Jailer "
            "proficiency certificate."
            in body
        )


def test_dual_license_email_contains_both_tracks(app):
    with app.app_context():
        officer = make_officer()

        officer.jailer_service_start_date = date(
            2020,
            1,
            1,
        )

        db.session.add(
            OfficerAward(
                agency_id=officer.agency_id,
                officer_id=officer.id,
                award_type="License",
                award_name="Jailer License",
                award_date=date(2020, 1, 1),
            )
        )

        db.session.commit()

        result = build_compliance_email(
            officer,
            evaluation_date=date(2026, 8, 11),
            track="combined",
        )

        body = result["body"]

        assert "PEACE OFFICER PROFICIENCY" in body
        assert "COUNTY JAILER PROFICIENCY" in body

        assert (
            body.index("PEACE OFFICER PROFICIENCY")
            < body.index("COUNTY JAILER PROFICIENCY")
        )


def test_peace_officer_only_email_has_no_jailer_section(
    app,
):
    with app.app_context():
        officer = make_officer()

        result = build_compliance_email(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        body = result["body"]

        assert "PEACE OFFICER PROFICIENCY" in body
        assert "COUNTY JAILER PROFICIENCY" not in body



def test_telecommunicator_email_includes_proficiency(
    app,
):
    with app.app_context():
        officer = make_officer()

        officer.telecommunicator_service_start_date = (
            date(2020, 1, 1)
        )

        db.session.add(
            OfficerAward(
                agency_id=officer.agency_id,
                officer_id=officer.id,
                award_type="License",
                award_name="Telecommunicator License",
                award_date=date(2020, 1, 1),
            )
        )

        db.session.commit()

        result = build_compliance_email(
            officer,
            evaluation_date=date(2026, 8, 11),
            track="telecommunicator",
        )

        body = result["body"]

        assert result["subject"] == (
            "TCOLE Telecommunicator Compliance Status"
        )

        assert (
            "TELECOMMUNICATOR PROFICIENCY"
            in body
        )

        assert (
            "Next Certificate: Basic Telecommunicator"
            in body
        )


def test_compliance_email_includes_ptm_identity_footer(app):
    with app.app_context():
        officer = make_officer()

        result = build_compliance_email(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        body = result["body"]

        assert "Paradigm Training Manager™" in body
        assert (
            "© 2026 Paradigm Strategic Partners, LLC. "
            "All Rights Reserved."
            in body
        )
        assert "Software ID: PTM-PSP-2026" in body

        assert body.rstrip().endswith(
            "Software ID: PTM-PSP-2026"
        )
