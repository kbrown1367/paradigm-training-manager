import pytest

from app import create_app
from app.compliance.email_resolver import (
    resolve_officer_email,
)
from app.extensions import db
from app.models import Agency, Officer


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


def make_officer(
    email_pattern="FIRST_INITIAL_LAST",
    email_domain="example.gov",
    first_name="Jane",
    last_name="Smith",
    email_override=None,
):
    agency = Agency(
        name="Test Police Department",
        email_pattern=email_pattern,
        email_domain=email_domain,
    )
    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="123456",
        first_name=first_name,
        last_name=last_name,
        email_override=email_override,
    )
    db.session.add(officer)
    db.session.commit()

    return officer


def test_first_initial_last(app):
    with app.app_context():
        officer = make_officer()

        result = resolve_officer_email(officer)

        assert result["email"] == (
            "jsmith@example.gov"
        )
        assert result["source"] == (
            "AGENCY_PATTERN"
        )


def test_first_dot_last(app):
    with app.app_context():
        officer = make_officer(
            email_pattern="FIRST_DOT_LAST"
        )

        result = resolve_officer_email(officer)

        assert result["email"] == (
            "jane.smith@example.gov"
        )


def test_first_last(app):
    with app.app_context():
        officer = make_officer(
            email_pattern="FIRST_LAST"
        )

        result = resolve_officer_email(officer)

        assert result["email"] == (
            "janesmith@example.gov"
        )


def test_last_first_initial(app):
    with app.app_context():
        officer = make_officer(
            email_pattern="LAST_FIRST_INITIAL"
        )

        result = resolve_officer_email(officer)

        assert result["email"] == (
            "smithj@example.gov"
        )


def test_officer_override_wins(app):
    with app.app_context():
        officer = make_officer(
            email_override=(
                "special.address@example.gov"
            )
        )

        result = resolve_officer_email(officer)

        assert result["email"] == (
            "special.address@example.gov"
        )
        assert result["source"] == (
            "OFFICER_OVERRIDE"
        )


def test_name_normalization(app):
    with app.app_context():
        officer = make_officer(
            first_name="José",
            last_name="De La Cruz",
        )

        result = resolve_officer_email(officer)

        assert result["email"] == (
            "jdelacruz@example.gov"
        )


def test_apostrophe_and_hyphen_normalization(app):
    with app.app_context():
        officer = make_officer(
            first_name="Anne-Marie",
            last_name="O'Brien",
            email_pattern="FIRST_DOT_LAST",
        )

        result = resolve_officer_email(officer)

        assert result["email"] == (
            "annemarie.obrien@example.gov"
        )


def test_leading_at_sign_removed_from_domain(app):
    with app.app_context():
        officer = make_officer(
            email_domain="@example.gov"
        )

        result = resolve_officer_email(officer)

        assert result["email"] == (
            "jsmith@example.gov"
        )


def test_missing_agency_configuration_returns_none(
    app,
):
    with app.app_context():
        officer = make_officer(
            email_pattern=None,
            email_domain=None,
        )

        result = resolve_officer_email(officer)

        assert result["email"] is None
        assert result["source"] is None


def test_unknown_pattern_returns_none(app):
    with app.app_context():
        officer = make_officer(
            email_pattern="UNKNOWN_PATTERN"
        )

        result = resolve_officer_email(officer)

        assert result["email"] is None
