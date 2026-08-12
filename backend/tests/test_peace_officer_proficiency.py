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
from app.compliance.peace_officer_proficiency import (
    evaluate_peace_officer_proficiency,
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


def make_officer(
    certificate=None,
    education=None,
    training_hours=0,
):
    agency = Agency(name="Test Department")
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

    if certificate:
        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="Certificate",
                award_name=certificate,
                award_date=date(2020, 1, 1),
            )
        )

    if education:
        db.session.add(
            OfficerAward(
                agency_id=agency.id,
                officer_id=officer.id,
                award_type="Academic Recognition",
                award_name=(
                    "Academic Recognition Award - "
                    f"{education}"
                ),
                award_date=date(2019, 1, 1),
            )
        )

    if training_hours:
        db.session.add(
            TrainingRecord(
                agency_id=agency.id,
                officer_id=officer.id,
                course_number="9999",
                course_title="General Training",
                course_date=date(2025, 1, 1),
                credited_hours=Decimal(
                    str(training_hours)
                ),
                hours_source="TCOLE",
                source="TCOLE",
            )
        )

    db.session.commit()

    return officer


def test_basic_advances_to_intermediate(app):
    with app.app_context():
        officer = make_officer(
            certificate="Basic Peace Officer",
        )

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["current_certificate"] == (
            "Basic Peace Officer"
        )
        assert result["next_certificate"] == (
            "Intermediate Peace Officer"
        )


def test_intermediate_advances_to_advanced(app):
    with app.app_context():
        officer = make_officer(
            certificate="Intermediate Peace Officer",
        )

        result = evaluate_peace_officer_proficiency(
            officer,
        )

        assert result["next_certificate"] == (
            "Advanced Peace Officer"
        )


def test_advanced_advances_to_master(app):
    with app.app_context():
        officer = make_officer(
            certificate="Advanced Peace Officer",
        )

        result = evaluate_peace_officer_proficiency(
            officer,
        )

        assert result["next_certificate"] == (
            "Master Peace Officer"
        )


def test_master_is_terminal(app):
    with app.app_context():
        officer = make_officer(
            certificate="Master Peace Officer",
        )

        result = evaluate_peace_officer_proficiency(
            officer,
        )

        assert result["status"] == "TERMINAL"
        assert result["next_certificate"] is None


def test_no_certificate_targets_basic(app):
    with app.app_context():
        officer = make_officer()

        result = evaluate_peace_officer_proficiency(
            officer,
        )

        assert result["next_certificate"] == (
            "Basic Peace Officer"
        )
        assert result["status"] == (
            "INSUFFICIENT_DATA"
        )


def test_training_hours_use_all_imported_history(app):
    with app.app_context():
        officer = make_officer(
            certificate="Intermediate Peace Officer",
            training_hours=1234,
        )

        result = evaluate_peace_officer_proficiency(
            officer,
        )

        assert result["training_hours"] == 1234.0


def test_tcole_academic_award_is_detected(app):
    with app.app_context():
        officer = make_officer(
            certificate="Intermediate Peace Officer",
            education="Bachelor Degree",
        )

        result = evaluate_peace_officer_proficiency(
            officer,
        )

        assert result["education_level"] == "BACHELOR"


def test_service_is_not_inferred_from_agency_tenure(app):
    with app.app_context():
        officer = make_officer(
            certificate="Basic Peace Officer",
            training_hours=5000,
        )

        result = evaluate_peace_officer_proficiency(
            officer,
        )

        assert result["service_years"] is None
        assert result["status"] == "INSUFFICIENT_DATA"


def test_military_pathway_defaults_to_no_service(app):
    with app.app_context():
        officer = make_officer(
            certificate="Advanced Peace Officer",
        )

        result = evaluate_peace_officer_proficiency(
            officer,
        )

        military = result["pathway_results"][
            "military"
        ]

        assert officer.verified_military_months == 0
        assert military["known"] is False
        assert military["satisfied"] is False


def test_service_years_exact_anniversary(app):
    with app.app_context():
        officer = make_officer(
            certificate="Basic Peace Officer",
            training_hours=400,
        )
        officer.peace_officer_service_start_date = date(
            2018,
            8,
            9,
        )
        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["service_years"] == 8


def test_service_years_day_before_anniversary(app):
    with app.app_context():
        officer = make_officer(
            certificate="Basic Peace Officer",
            training_hours=400,
        )
        officer.peace_officer_service_start_date = date(
            2018,
            8,
            10,
        )
        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["service_years"] == 7


def test_future_service_start_date_is_unknown(app):
    with app.app_context():
        officer = make_officer(
            certificate="Basic Peace Officer",
        )
        officer.peace_officer_service_start_date = date(
            2027,
            1,
            1,
        )
        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["service_years"] is None
        assert result["status"] == "INSUFFICIENT_DATA"


def test_intermediate_8_year_400_hour_pathway(app):
    with app.app_context():
        officer = make_officer(
            certificate="Basic Peace Officer",
            training_hours=400,
        )
        officer.peace_officer_service_start_date = date(
            2018,
            8,
            9,
        )
        officer.verified_military_months = 0
        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["qualifying_pathway"] == {
            "type": "SERVICE_TRAINING",
            "service_years": 8,
            "training_hours": 400,
        }
        assert result["status"] == (
            "NOT_ELIGIBLE"
        )


def test_intermediate_6_year_800_hour_pathway(app):
    with app.app_context():
        officer = make_officer(
            certificate="Basic Peace Officer",
            training_hours=800,
        )
        officer.peace_officer_service_start_date = date(
            2020,
            8,
            9,
        )
        officer.verified_military_months = 0
        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["qualifying_pathway"][
            "service_years"
        ] == 6
        assert result["qualifying_pathway"][
            "training_hours"
        ] == 800


def test_intermediate_associate_pathway(app):
    with app.app_context():
        officer = make_officer(
            certificate="Basic Peace Officer",
            education="Associate Degree",
        )
        officer.peace_officer_service_start_date = date(
            2022,
            8,
            9,
        )
        officer.verified_military_months = 0
        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["qualifying_pathway"] == {
            "type": "EDUCATION",
            "service_years": 4,
            "education_level": "ASSOCIATE",
        }


def test_intermediate_bachelor_pathway(app):
    with app.app_context():
        officer = make_officer(
            certificate="Basic Peace Officer",
            education="Bachelor Degree",
        )
        officer.peace_officer_service_start_date = date(
            2024,
            8,
            9,
        )
        officer.verified_military_months = 0
        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["qualifying_pathway"] == {
            "type": "EDUCATION",
            "service_years": 2,
            "education_level": "BACHELOR",
        }


def test_intermediate_two_year_military_pathway(app):
    with app.app_context():
        officer = make_officer(
            certificate="Basic Peace Officer",
        )
        officer.peace_officer_service_start_date = date(
            2022,
            8,
            9,
        )
        officer.verified_military_months = 24
        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["qualifying_pathway"] == {
            "type": "MILITARY",
            "service_years": 4,
            "military_years": 2,
        }


def test_intermediate_four_year_military_pathway(app):
    with app.app_context():
        officer = make_officer(
            certificate="Basic Peace Officer",
        )
        officer.peace_officer_service_start_date = date(
            2024,
            8,
            9,
        )
        officer.verified_military_months = 48
        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["qualifying_pathway"] == {
            "type": "MILITARY",
            "service_years": 2,
            "military_years": 4,
        }


def test_known_inputs_but_no_pathway_is_not_eligible(app):
    with app.app_context():
        officer = make_officer(
            certificate="Basic Peace Officer",
            training_hours=100,
        )
        officer.peace_officer_service_start_date = date(
            2025,
            8,
            9,
        )
        officer.verified_military_months = 0
        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["qualifying_pathway"] is None
        assert result["status"] == "NOT_ELIGIBLE"


def test_default_no_military_does_not_block_known_training_pathway(
    app,
):
    with app.app_context():
        officer = make_officer(
            certificate="Basic Peace Officer",
            training_hours=400,
        )
        officer.peace_officer_service_start_date = date(
            2018,
            8,
            9,
        )
        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert officer.verified_military_months == 0
        assert result["qualifying_pathway"][
            "type"
        ] == "SERVICE_TRAINING"
        assert result["status"] == (
            "NOT_ELIGIBLE"
        )


def add_course(
    officer,
    course_number,
    course_date=date(2025, 1, 1),
):
    db.session.add(
        TrainingRecord(
            agency_id=officer.agency_id,
            officer_id=officer.id,
            course_number=course_number,
            course_title=f"Course {course_number}",
            course_date=course_date,
            credited_hours=Decimal("8.00"),
            hours_source="TCOLE",
            source="TCOLE",
        )
    )


def test_master_eligible_when_pathway_and_courses_met(app):
    with app.app_context():
        officer = make_officer(
            certificate="Advanced Peace Officer",
            training_hours=1200,
        )

        officer.peace_officer_service_start_date = date(
            2006,
            8,
            9,
        )
        officer.verified_military_months = 0

        add_course(officer, "66300")
        add_course(officer, "66400")

        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["status"] == "ELIGIBLE"
        assert result["next_certificate"] == (
            "Master Peace Officer"
        )
        assert result["missing_requirements"] == []


def test_master_missing_ics_400_not_eligible(app):
    with app.app_context():
        officer = make_officer(
            certificate="Advanced Peace Officer",
            training_hours=1200,
        )

        officer.peace_officer_service_start_date = date(
            2006,
            8,
            9,
        )
        officer.verified_military_months = 0

        add_course(officer, "66300")

        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["status"] == "NOT_ELIGIBLE"
        assert "FEMA ICS 400" in (
            result["missing_requirements"]
        )


def test_intermediate_full_course_matrix_can_be_eligible(app):
    with app.app_context():
        officer = make_officer(
            certificate="Basic Peace Officer",
            training_hours=400,
        )

        officer.peace_officer_service_start_date = date(
            2018,
            8,
            9,
        )
        officer.verified_military_months = 0

        required_courses = [
            "2105",
            "2106",
            "2107",
            "2108",
            "2109",
            "3277",
            "3255",
            "3256",
            "3270",
            "1850",
            "7887",
            "1849",
            "3275",
            "4068",
            "4065",
            "3232",
            "3939",
            "66300",
        ]

        for course_number in required_courses:
            add_course(
                officer,
                course_number,
            )

        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["status"] == "ELIGIBLE"
        assert result["missing_requirements"] == []
        assert len(
            result["course_requirements"]
        ) == 18


def test_intermediate_missing_one_course_not_eligible(app):
    with app.app_context():
        officer = make_officer(
            certificate="Basic Peace Officer",
            training_hours=400,
        )

        officer.peace_officer_service_start_date = date(
            2018,
            8,
            9,
        )
        officer.verified_military_months = 0

        required_courses = [
            "2105",
            "2106",
            "2107",
            "2108",
            "2109",
            "3277",
            "3255",
            "3256",
            "3270",
            "1850",
            "7887",
            "1849",
            "3275",
            "4068",
            "4065",
            "3232",
            "3939",
            # ICS 300 intentionally absent
        ]

        for course_number in required_courses:
            add_course(
                officer,
                course_number,
            )

        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["status"] == "NOT_ELIGIBLE"
        assert result["missing_requirements"] == [
            "FEMA ICS 300"
        ]


def test_basic_eligible_with_service_and_courses(app):
    with app.app_context():
        officer = make_officer()

        officer.peace_officer_service_start_date = date(
            2025,
            8,
            9,
        )

        db.session.add(
            OfficerAward(
                agency_id=officer.agency_id,
                officer_id=officer.id,
                award_type="License",
                award_name="Peace Officer License",
                award_date=date(2025, 8, 9),
            )
        )

        for course_number in [
            "1999",
            "3722",
            "4202",
            "66100",
            "66200",
            "66700",
            "3270",
        ]:
            add_course(
                officer,
                course_number,
            )

        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["status"] == "ELIGIBLE"
        assert result["next_certificate"] == (
            "Basic Peace Officer"
        )


def test_basic_pre_cutoff_courses_become_not_applicable(app):
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
                award_type="License",
                award_name="Peace Officer License",
                award_date=date(2000, 1, 1),
            )
        )

        for course_number in [
            "1999",
            "4202",
            "66100",
            "66200",
            "66700",
            "3270",
        ]:
            add_course(
                officer,
                course_number,
            )

        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        field_training = next(
            item
            for item in result["course_requirements"]
            if item["id"] == "FIELD_TRAINING"
        )

        assert (
            field_training["status"]
            == "NOT_APPLICABLE"
        )


def test_agency_verified_education_is_fallback(app):
    with app.app_context():
        officer = make_officer(
            certificate="Basic Peace Officer",
        )
        officer.peace_officer_service_start_date = date(
            2024,
            8,
            9,
        )
        officer.verified_education_level = "BACHELOR"
        officer.verified_military_months = 0
        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 9),
        )

        assert result["education_level"] == "BACHELOR"
        assert result["qualifying_pathway"]["type"] == (
            "EDUCATION"
        )


def test_tcole_education_overrides_agency_fallback(app):
    with app.app_context():
        officer = make_officer(
            certificate="Basic Peace Officer",
            education="Master Degree",
        )
        officer.verified_education_level = "ASSOCIATE"
        officer.verified_military_months = 0
        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
        )

        assert result["education_level"] == "MASTER"


def test_best_available_service_training_pathway_reports_training_shortfall(
    app,
):
    with app.app_context():
        officer = make_officer(
            certificate="Intermediate Peace Officer",
            training_hours=1461,
        )
        officer.peace_officer_service_start_date = date(
            2020,
            8,
            10,
        )
        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 10),
        )

        assert result["status"] == "NOT_ELIGIBLE"
        assert result["qualifying_pathway"] is None

        pathway = result["best_available_pathway"]

        assert pathway["type"] == "SERVICE_TRAINING"
        assert pathway["service_years"] == 6
        assert pathway["training_hours"] == 2400

        assert pathway["actual_service_years"] == 6
        assert pathway["actual_training_hours"] == 1461.0

        assert pathway["service_years_short"] == 0
        assert pathway["training_hours_short"] == 939.0


def test_best_available_service_training_pathway_can_report_service_shortfall(
    app,
):
    with app.app_context():
        officer = make_officer(
            certificate="Intermediate Peace Officer",
            training_hours=3000,
        )
        officer.peace_officer_service_start_date = date(
            2022,
            8,
            10,
        )
        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 10),
        )

        pathway = result["best_available_pathway"]

        assert pathway["type"] == "SERVICE_TRAINING"
        assert pathway["service_years"] == 6
        assert pathway["training_hours"] == 2400
        assert pathway["actual_service_years"] == 4
        assert pathway["actual_training_hours"] == 3000.0
        assert pathway["service_years_short"] == 2
        assert pathway["training_hours_short"] == 0.0


def test_satisfied_pathway_is_also_best_available_pathway(
    app,
):
    with app.app_context():
        officer = make_officer(
            certificate="Basic Peace Officer",
            training_hours=1200,
        )
        officer.peace_officer_service_start_date = date(
            2022,
            8,
            10,
        )
        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 10),
        )

        assert result["qualifying_pathway"] == {
            "type": "SERVICE_TRAINING",
            "service_years": 4,
            "training_hours": 1200,
        }

        pathway = result["best_available_pathway"]

        assert pathway["service_years"] == 4
        assert pathway["training_hours"] == 1200
        assert pathway["service_years_short"] == 0
        assert pathway["training_hours_short"] == 0.0


def test_master_peace_officer_certificate_is_not_academic_education(
    app,
):
    with app.app_context():
        officer = make_officer(
            certificate="Master Peace Officer",
        )

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 12),
        )

        assert result["education_level"] is None


def test_generic_academic_recognition_does_not_invent_degree(
    app,
):
    with app.app_context():
        officer = make_officer()

        db.session.add(
            OfficerAward(
                agency_id=officer.agency_id,
                officer_id=officer.id,
                award_type="Academic Recognition",
                award_name="Academic Recognition Award",
                award_date=date(2020, 1, 1),
            )
        )
        db.session.commit()

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 12),
        )

        assert result["education_level"] is None


def test_explicit_tcole_master_degree_remains_academic_education(
    app,
):
    with app.app_context():
        officer = make_officer(
            certificate="Advanced Peace Officer",
            education="Master Degree",
        )

        result = evaluate_peace_officer_proficiency(
            officer,
            evaluation_date=date(2026, 8, 12),
        )

        assert result["education_level"] == "MASTER"
