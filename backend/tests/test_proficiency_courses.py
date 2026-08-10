from datetime import date
from types import SimpleNamespace

from app.compliance.proficiency_courses import (
    evaluate_course_requirement,
    evaluate_course_requirements,
)


def training(course_number, course_date):
    return SimpleNamespace(
        course_number=course_number,
        course_date=course_date,
    )


def test_direct_course_satisfies_requirement():
    requirement = {
        "id": "ICS_300",
        "label": "FEMA ICS 300",
        "accepted_courses": ["66300"],
    }

    result = evaluate_course_requirement(
        requirement,
        [
            training(
                "66300",
                date(2025, 10, 1),
            )
        ],
    )

    assert result["status"] == "MET"
    assert result["satisfied_by"]["type"] == "COURSE"


def test_equivalent_course_satisfies_requirement():
    requirement = {
        "id": "CRISIS_INTERVENTION",
        "label": "Crisis Intervention",
        "accepted_courses": [
            "1850",
            "1000667",
        ],
    }

    result = evaluate_course_requirement(
        requirement,
        [
            training(
                "1000667",
                date(2024, 1, 1),
            )
        ],
    )

    assert result["status"] == "MET"
    assert (
        result["satisfied_by"]["courses"][0]
        ["course_number"]
        == "1000667"
    )


def test_missing_course_is_reported():
    requirement = {
        "id": "ICS_400",
        "label": "FEMA ICS 400",
        "accepted_courses": ["66400"],
    }

    result = evaluate_course_requirement(
        requirement,
        [],
    )

    assert result["status"] == "MISSING"


def test_safvic_group_requires_all_three():
    requirement = {
        "id": "SPECIAL_INVESTIGATIVE_TOPICS",
        "label": "Special Investigative Topics",
        "accepted_courses": [],
        "accepted_course_groups": [
            {
                "courses": [
                    "3261",
                    "3262",
                    "3263",
                ],
                "require_all": True,
                "same_two_year_unit": True,
            }
        ],
    }

    result = evaluate_course_requirement(
        requirement,
        [
            training("3261", date(2025, 10, 1)),
            training("3262", date(2025, 11, 1)),
        ],
    )

    assert result["status"] == "MISSING"


def test_safvic_group_satisfies_same_unit():
    requirement = {
        "id": "SPECIAL_INVESTIGATIVE_TOPICS",
        "label": "Special Investigative Topics",
        "accepted_courses": [],
        "accepted_course_groups": [
            {
                "courses": [
                    "3261",
                    "3262",
                    "3263",
                ],
                "require_all": True,
                "same_two_year_unit": True,
            }
        ],
    }

    result = evaluate_course_requirement(
        requirement,
        [
            training("3261", date(2025, 10, 1)),
            training("3262", date(2026, 1, 1)),
            training("3263", date(2026, 2, 1)),
        ],
    )

    assert result["status"] == "MET"
    assert (
        result["satisfied_by"]["type"]
        == "COURSE_GROUP"
    )


def test_safvic_group_rejects_different_units():
    requirement = {
        "id": "SPECIAL_INVESTIGATIVE_TOPICS",
        "label": "Special Investigative Topics",
        "accepted_courses": [],
        "accepted_course_groups": [
            {
                "courses": [
                    "3261",
                    "3262",
                    "3263",
                ],
                "require_all": True,
                "same_two_year_unit": True,
            }
        ],
    }

    result = evaluate_course_requirement(
        requirement,
        [
            training("3261", date(2024, 1, 1)),
            training("3262", date(2024, 2, 1)),
            training("3263", date(2025, 10, 1)),
        ],
    )

    assert result["status"] == "MISSING"


def test_legacy_sit_before_cutoff_is_valid():
    requirement = {
        "id": "SPECIAL_INVESTIGATIVE_TOPICS",
        "label": "Special Investigative Topics",
        "accepted_courses": [],
        "dated_equivalencies": [
            {
                "courses": ["3214"],
                "completed_before": "2013-12-31",
            }
        ],
    }

    result = evaluate_course_requirement(
        requirement,
        [
            training(
                "3214",
                date(2013, 12, 30),
            )
        ],
    )

    assert result["status"] == "MET"


def test_legacy_sit_after_cutoff_is_invalid():
    requirement = {
        "id": "SPECIAL_INVESTIGATIVE_TOPICS",
        "label": "Special Investigative Topics",
        "accepted_courses": [],
        "dated_equivalencies": [
            {
                "courses": ["3214"],
                "completed_before": "2013-12-31",
            }
        ],
    }

    result = evaluate_course_requirement(
        requirement,
        [
            training(
                "3214",
                date(2014, 1, 1),
            )
        ],
    )

    assert result["status"] == "MISSING"


def test_basic_requirement_not_applicable_before_cutoff():
    requirement = {
        "id": "FIELD_TRAINING",
        "label": "Peace Officer Field Training",
        "accepted_courses": ["3722"],
        "applicability": {
            "peace_officer_license_on_or_after":
                "2004-06-01"
        },
    }

    result = evaluate_course_requirement(
        requirement,
        [],
        context={
            "peace_officer_license_date":
                date(2003, 5, 1)
        },
    )

    assert result["status"] == "NOT_APPLICABLE"


def test_basic_requirement_applies_on_cutoff():
    requirement = {
        "id": "FIELD_TRAINING",
        "label": "Peace Officer Field Training",
        "accepted_courses": ["3722"],
        "applicability": {
            "peace_officer_license_on_or_after":
                "2004-06-01"
        },
    }

    result = evaluate_course_requirement(
        requirement,
        [],
        context={
            "peace_officer_license_date":
                date(2004, 6, 1)
        },
    )

    assert result["status"] == "MISSING"


def test_missing_license_date_is_insufficient_data():
    requirement = {
        "id": "FIELD_TRAINING",
        "label": "Peace Officer Field Training",
        "accepted_courses": ["3722"],
        "applicability": {
            "peace_officer_license_on_or_after":
                "2004-06-01"
        },
    }

    result = evaluate_course_requirement(
        requirement,
        [],
        context={},
    )

    assert result["status"] == "INSUFFICIENT_DATA"


def test_collection_reports_missing_requirements():
    rule = {
        "required_courses": [
            {
                "id": "ICS_300",
                "label": "FEMA ICS 300",
                "accepted_courses": ["66300"],
            },
            {
                "id": "ICS_400",
                "label": "FEMA ICS 400",
                "accepted_courses": ["66400"],
            },
        ]
    }

    result = evaluate_course_requirements(
        rule,
        [
            training(
                "66300",
                date(2025, 1, 1),
            )
        ],
    )

    assert result["all_satisfied"] is False
    assert len(result["missing"]) == 1
    assert result["missing"][0]["id"] == "ICS_400"


def test_safvic_group_finds_later_valid_same_unit_set():
    requirement = {
        "id": "SPECIAL_INVESTIGATIVE_TOPICS",
        "label": "Special Investigative Topics",
        "accepted_courses": [],
        "accepted_course_groups": [
            {
                "courses": [
                    "3261",
                    "3262",
                    "3263",
                ],
                "require_all": True,
                "same_two_year_unit": True,
            }
        ],
    }

    result = evaluate_course_requirement(
        requirement,
        [
            # Older completions that do not form
            # a valid group together.
            training("3261", date(2022, 1, 1)),
            training("3262", date(2022, 2, 1)),

            # Later qualifying set in one unit.
            training("3261", date(2025, 10, 1)),
            training("3262", date(2026, 1, 1)),
            training("3263", date(2026, 2, 1)),
        ],
    )

    assert result["status"] == "MET"
    assert (
        result["satisfied_by"]["type"]
        == "COURSE_GROUP"
    )

    courses = {
        item["course_number"]
        for item in
        result["satisfied_by"]["courses"]
    }

    assert courses == {
        "3261",
        "3262",
        "3263",
    }

    assert (
        result["satisfied_by"]["training_unit"]
        ["start"]
        == "2025-09-01"
    )
