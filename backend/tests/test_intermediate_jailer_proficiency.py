from datetime import date
from decimal import Decimal

import pytest

from app import create_app
from app.compliance.jailer_proficiency import (
    evaluate_intermediate_jailer_proficiency,
)
from app.extensions import db
from app.models import (
    Agency,
    Officer,
    OfficerAward,
    TrainingRecord,
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


def make_jailer(
    service_start=date(2018, 1, 1),
    basic_date=date(2020, 1, 1),
):
    agency = Agency(
        name="Test Sheriff's Office"
    )
    db.session.add(agency)
    db.session.flush()

    officer = Officer(
        agency_id=agency.id,
        tcole_pid="123456",
        first_name="JOHN",
        last_name="SMITH",
        jailer_service_start_date=service_start,
    )
    db.session.add(officer)
    db.session.flush()

    db.session.add(
        OfficerAward(
            agency_id=agency.id,
            officer_id=officer.id,
            award_type="License",
            award_name="Jailer License",
            award_date=service_start,
        )
    )

    if basic_date is not None:
        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="Certificate",
                award_name="Basic Jailer",
                award_date=basic_date,
            )
        )

    db.session.commit()

    return agency, officer


def add_training(
    agency,
    officer,
    course_number,
    hours,
    course_date=date(2020, 1, 1),
):
    db.session.add(
        TrainingRecord(
            agency_id=agency.id,
            officer_id=officer.id,
            course_number=course_number,
            course_title=f"Course {course_number}",
            course_date=course_date,
            credited_hours=Decimal(str(hours)),
            hours_source="TCOLE_CYCLE_REPORT",
            source="TCOLE",
        )
    )


def add_required_intermediate_courses(
    agency,
    officer,
):
    for course in (
        "3501",
        "3502",
        "3503",
        "3504",
        "2109",
    ):
        add_training(
            agency,
            officer,
            course,
            8,
        )


def add_certificate(
    agency,
    officer,
    name,
    award_date=date(2025, 1, 1),
):
    db.session.add(
        OfficerAward(
            agency_id=agency.id,
            officer_id=officer.id,
            award_type="Certificate",
            award_name=name,
            award_date=award_date,
        )
    )


def test_six_year_400_hour_pathway(app):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(2020, 1, 1),
        )

        add_training(
            agency,
            officer,
            "9000",
            360,
        )
        add_required_intermediate_courses(
            agency,
            officer,
        )

        db.session.commit()

        result = evaluate_intermediate_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "ELIGIBLE"
        assert result["qualifying_pathway"][
            "service_years"
        ] == 6
        assert result["qualifying_pathway"][
            "training_hours"
        ] == 400


def test_four_year_800_hour_pathway(app):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(2022, 1, 1),
        )

        add_training(
            agency,
            officer,
            "9000",
            760,
        )
        add_required_intermediate_courses(
            agency,
            officer,
        )

        db.session.commit()

        result = evaluate_intermediate_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "ELIGIBLE"
        assert result["qualifying_pathway"][
            "service_years"
        ] == 4
        assert result["qualifying_pathway"][
            "training_hours"
        ] == 800


def test_two_year_1200_hour_pathway(app):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(2024, 1, 1),
        )

        add_training(
            agency,
            officer,
            "9000",
            1160,
        )
        add_required_intermediate_courses(
            agency,
            officer,
        )

        db.session.commit()

        result = evaluate_intermediate_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "ELIGIBLE"
        assert result["qualifying_pathway"][
            "service_years"
        ] == 2
        assert result["qualifying_pathway"][
            "training_hours"
        ] == 1200


def test_one_year_2400_hour_pathway(app):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(2025, 1, 1),
        )

        add_training(
            agency,
            officer,
            "9000",
            2360,
        )
        add_required_intermediate_courses(
            agency,
            officer,
        )

        db.session.commit()

        result = evaluate_intermediate_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "ELIGIBLE"
        assert result["qualifying_pathway"][
            "service_years"
        ] == 1
        assert result["qualifying_pathway"][
            "training_hours"
        ] == 2400


def test_associate_degree_two_year_pathway(app):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(2024, 1, 1),
        )

        officer.verified_education_level = "ASSOCIATE"

        add_required_intermediate_courses(
            agency,
            officer,
        )

        db.session.commit()

        result = evaluate_intermediate_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "ELIGIBLE"
        assert result["qualifying_pathway"][
            "type"
        ] == "EDUCATION"
        assert result["qualifying_pathway"][
            "education_level"
        ] == "ASSOCIATE"


def test_bachelor_degree_one_year_pathway(app):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(2025, 1, 1),
        )

        officer.verified_education_level = "BACHELOR"

        add_required_intermediate_courses(
            agency,
            officer,
        )

        db.session.commit()

        result = evaluate_intermediate_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "ELIGIBLE"
        assert result["qualifying_pathway"][
            "type"
        ] == "EDUCATION"
        assert result["qualifying_pathway"][
            "education_level"
        ] == "BACHELOR"


def test_basic_jailer_certificate_is_required(app):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(2018, 1, 1),
            basic_date=None,
        )

        add_training(
            agency,
            officer,
            "9000",
            1000,
        )

        db.session.commit()

        result = evaluate_intermediate_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "NOT_ELIGIBLE"
        assert (
            "Basic Jailer certificate"
            in result["missing_requirements"]
        )


def test_pre_1993_basic_certificate_skips_course_categories(
    app,
):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(1980, 1, 1),
            basic_date=date(1993, 2, 28),
        )

        add_training(
            agency,
            officer,
            "9000",
            400,
        )

        db.session.commit()

        result = evaluate_intermediate_jailer_proficiency(
            officer,
            evaluation_date=date(1994, 3, 1),
        )

        statuses = {
            item["id"]: item["status"]
            for item in result["course_requirements"]
        }

        assert all(
            status == "NOT_APPLICABLE"
            for status in statuses.values()
        )


def test_march_1_1993_basic_certificate_does_not_trigger_courses(
    app,
):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(1980, 1, 1),
            basic_date=date(1993, 3, 1),
        )

        add_training(
            agency,
            officer,
            "9000",
            400,
        )

        db.session.commit()

        result = evaluate_intermediate_jailer_proficiency(
            officer,
            evaluation_date=date(1994, 3, 1),
        )

        assert all(
            item["status"] == "NOT_APPLICABLE"
            for item in result["course_requirements"]
        )


def test_after_march_1_1993_requires_course_categories(app):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(1980, 1, 1),
            basic_date=date(1993, 3, 2),
        )

        add_training(
            agency,
            officer,
            "9000",
            400,
        )

        db.session.commit()

        result = evaluate_intermediate_jailer_proficiency(
            officer,
            evaluation_date=date(1994, 3, 2),
        )

        assert result["status"] == "NOT_ELIGIBLE"

        statuses = {
            item["id"]: item["status"]
            for item in result["course_requirements"]
        }

        assert all(
            status == "MISSING"
            for status in statuses.values()
        )


@pytest.mark.parametrize(
    "course_number",
    [
        "3501",
        "1120",
        "2018",
        "91209",
    ],
)
def test_suicide_detection_equivalencies(
    app,
    course_number,
):
    with app.app_context():
        agency, officer = make_jailer()

        add_training(
            agency,
            officer,
            course_number,
            8,
        )

        db.session.commit()

        result = evaluate_intermediate_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        requirement = next(
            item
            for item in result["course_requirements"]
            if item["id"] == "SUICIDE_DETECTION"
        )

        assert requirement["status"] == "COMPLETE"
        assert (
            requirement["matched_course"][
                "course_number"
            ]
            == course_number
        )


@pytest.mark.parametrize(
    "course_number",
    [
        "2109",
        "2110",
        "34001",
        "34002",
        "2111",
    ],
)
def test_spanish_equivalencies(
    app,
    course_number,
):
    with app.app_context():
        agency, officer = make_jailer()

        add_training(
            agency,
            officer,
            course_number,
            8,
        )

        db.session.commit()

        result = evaluate_intermediate_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        requirement = next(
            item
            for item in result["course_requirements"]
            if item["id"] == "SPANISH"
        )

        assert requirement["status"] == "COMPLETE"


def test_best_pathway_reports_training_hours_short(app):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(2022, 1, 1),
        )

        add_training(
            agency,
            officer,
            "9000",
            610,
        )
        add_required_intermediate_courses(
            agency,
            officer,
        )

        db.session.commit()

        result = evaluate_intermediate_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "NOT_ELIGIBLE"

        best = result["best_available_pathway"]

        assert best["type"] == "SERVICE_TRAINING"
        assert best["service_years"] == 4
        assert best["training_hours"] == 800
        assert best["training_hours_short"] == 150.0

        assert (
            "150 additional training hours"
            in result["missing_requirements"]
        )


def test_specific_tcole_academic_award_is_authoritative(app):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(2024, 1, 1),
        )

        officer.verified_education_level = "ASSOCIATE"

        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="Certificate",
                award_name=(
                    "Academic Recognition Award - "
                    "Bachelor Degree"
                ),
                award_date=date(2025, 1, 1),
            )
        )

        add_required_intermediate_courses(
            agency,
            officer,
        )

        db.session.commit()

        result = evaluate_intermediate_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["education_level"] == "BACHELOR"


def test_generic_academic_award_does_not_guess_degree(app):
    with app.app_context():
        agency, officer = make_jailer(
            service_start=date(2024, 1, 1),
        )

        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="Certificate",
                award_name="Academic Recognition Award",
                award_date=date(2025, 1, 1),
            )
        )

        db.session.commit()

        result = evaluate_intermediate_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["education_level"] is None


def test_advanced_certificate_satisfies_intermediate(app):
    with app.app_context():
        agency, officer = make_jailer()

        add_certificate(
            agency,
            officer,
            "Advanced Jailer Proficiency",
        )

        db.session.commit()

        result = evaluate_intermediate_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "AWARDED"
        assert (
            result["current_certificate"]
            == "Advanced Jailer"
        )


def test_master_certificate_satisfies_intermediate(app):
    with app.app_context():
        agency, officer = make_jailer()

        add_certificate(
            agency,
            officer,
            "Master Jailer Proficiency",
        )

        db.session.commit()

        result = evaluate_intermediate_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "AWARDED"
        assert (
            result["current_certificate"]
            == "Master Jailer"
        )


def test_non_jailer_is_not_applicable(app):
    with app.app_context():
        agency = Agency(
            name="Test Police Department"
        )
        db.session.add(agency)
        db.session.flush()

        officer = Officer(
            agency_id=agency.id,
            tcole_pid="999999",
            first_name="JANE",
            last_name="DOE",
        )
        db.session.add(officer)
        db.session.commit()

        result = evaluate_intermediate_jailer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 11),
        )

        assert result["status"] == "NOT_APPLICABLE"
