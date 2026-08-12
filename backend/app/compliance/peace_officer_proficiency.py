from datetime import date
from decimal import Decimal

from app.compliance.credentials import (
    get_highest_peace_officer_certificate,
)
from app.compliance.proficiency_rules import (
    load_proficiency_rule,
)
from app.compliance.proficiency_courses import (
    evaluate_course_requirements,
)


CERTIFICATE_SEQUENCE = (
    "Basic Peace Officer",
    "Intermediate Peace Officer",
    "Advanced Peace Officer",
    "Master Peace Officer",
)


PROFICIENCY_PATHWAYS = {
    "Intermediate Peace Officer": {
        "service_training": (
            {"service_years": 8, "training_hours": 400},
            {"service_years": 6, "training_hours": 800},
            {"service_years": 4, "training_hours": 1200},
            {"service_years": 2, "training_hours": 2400},
        ),
        "education": (
            {
                "service_years": 4,
                "education_level": "ASSOCIATE",
            },
            {
                "service_years": 2,
                "education_level": "BACHELOR",
            },
        ),
        "military": (
            {
                "service_years": 4,
                "military_years": 2,
            },
            {
                "service_years": 2,
                "military_years": 4,
            },
        ),
    },
    "Advanced Peace Officer": {
        "service_training": (
            {"service_years": 12, "training_hours": 800},
            {"service_years": 9, "training_hours": 1200},
            {"service_years": 6, "training_hours": 2400},
        ),
        "education": (
            {
                "service_years": 6,
                "education_level": "ASSOCIATE",
            },
            {
                "service_years": 5,
                "education_level": "BACHELOR",
            },
        ),
        "military": (
            {
                "service_years": 6,
                "military_years": 2,
            },
            {
                "service_years": 5,
                "military_years": 4,
            },
        ),
    },
    "Master Peace Officer": {
        "service_training": (
            {"service_years": 20, "training_hours": 1200},
            {"service_years": 15, "training_hours": 2400},
            {"service_years": 12, "training_hours": 3300},
            {"service_years": 10, "training_hours": 4000},
        ),
        "education": (
            {
                "service_years": 12,
                "education_level": "ASSOCIATE",
            },
            {
                "service_years": 9,
                "education_level": "BACHELOR",
            },
            {
                "service_years": 7,
                "education_level": "MASTER",
            },
            {
                "service_years": 5,
                "education_level": "DOCTORATE",
            },
        ),
        "military": (
            {
                "service_years": 12,
                "military_years": 2,
            },
            {
                "service_years": 9,
                "military_years": 4,
            },
            {
                "service_years": 7,
                "military_years": 5,
            },
            {
                "service_years": 5,
                "military_years": 8,
            },
        ),
    },
}


EDUCATION_RANK = {
    None: 0,
    "ASSOCIATE": 1,
    "BACHELOR": 2,
    "MASTER": 3,
    "DOCTORATE": 4,
}


def _next_certificate(current_certificate):
    if current_certificate is None:
        return "Basic Peace Officer"

    try:
        index = CERTIFICATE_SEQUENCE.index(
            current_certificate
        )
    except ValueError:
        return None

    if index == len(CERTIFICATE_SEQUENCE) - 1:
        return None

    return CERTIFICATE_SEQUENCE[index + 1]


def _peace_officer_license_date(officer):
    dates = [
        award.award_date
        for award in officer.awards
        if (
            award.award_type == "License"
            and award.award_name
            == "Peace Officer License"
            and award.award_date is not None
        )
    ]

    if not dates:
        return None

    return min(dates)


def _training_hours(officer):
    return sum(
        (
            Decimal(record.credited_hours)
            for record in officer.training_records
            if record.credited_hours is not None
        ),
        Decimal("0"),
    )


def _education_level(officer):
    recognized = {
        "academic recognition award - associate degree":
            "ASSOCIATE",
        "academic recognition award - bachelor degree":
            "BACHELOR",
        "academic recognition award - master degree":
            "MASTER",
        "academic recognition award - doctorate degree":
            "DOCTORATE",
        "academic recognition award - juris doctor":
            "DOCTORATE",
    }

    level = None

    # Only explicit TCOLE academic recognition awards
    # establish a college education level. Proficiency
    # certificates such as Master Peace Officer must not
    # be interpreted as academic degrees.
    for award in officer.awards:
        name = (
            award.award_name
            or ""
        ).strip().lower()

        candidate = recognized.get(name)

        if candidate is None:
            continue

        if (
            EDUCATION_RANK[candidate]
            > EDUCATION_RANK[level]
        ):
            level = candidate

    if level is not None:
        return level

    # Agency verification is a fallback only when TCOLE
    # does not report a specific academic recognition.
    verified = officer.verified_education_level

    if verified in EDUCATION_RANK:
        return verified

    return None


def _service_years(officer, evaluation_date):
    start_date = officer.peace_officer_service_start_date

    if start_date is None:
        return None

    if start_date > evaluation_date:
        return None

    years = evaluation_date.year - start_date.year

    if (
        evaluation_date.month,
        evaluation_date.day,
    ) < (
        start_date.month,
        start_date.day,
    ):
        years -= 1

    return years


def _military_months(officer):
    months = officer.verified_military_months

    if months is None:
        return None

    if months < 0:
        return None

    return months


def _evaluate_military(
    pathways,
    service_years,
    military_months,
):
    if service_years is None or military_months is None:
        return {
            "satisfied": False,
            "known": False,
            "pathway": None,
        }

    for pathway in pathways:
        required_months = pathway["military_years"] * 12

        if (
            service_years >= pathway["service_years"]
            and military_months >= required_months
        ):
            return {
                "satisfied": True,
                "known": True,
                "pathway": {
                    "type": "MILITARY",
                    **pathway,
                },
            }

    return {
        "satisfied": False,
        "known": True,
        "pathway": None,
    }


def _best_service_training_pathway(
    pathways,
    service_years,
    training_hours,
):
    if service_years is None:
        return None

    candidates = []

    for pathway in pathways:
        required_service = pathway["service_years"]
        required_training = Decimal(
            str(pathway["training_hours"])
        )

        service_short = max(
            0,
            required_service - service_years,
        )
        training_short = max(
            Decimal("0"),
            required_training - training_hours,
        )

        candidates.append(
            {
                "type": "SERVICE_TRAINING",
                **pathway,
                "actual_service_years":
                    service_years,
                "actual_training_hours":
                    float(training_hours),
                "service_years_short":
                    service_short,
                "training_hours_short":
                    float(training_short),
            }
        )

    if not candidates:
        return None

    service_feasible = [
        candidate
        for candidate in candidates
        if candidate["service_years_short"] == 0
    ]

    if service_feasible:
        return min(
            service_feasible,
            key=lambda candidate: (
                candidate["training_hours_short"],
                candidate["training_hours"],
                -candidate["service_years"],
            ),
        )

    return min(
        candidates,
        key=lambda candidate: (
            candidate["service_years_short"],
            candidate["training_hours_short"],
            candidate["training_hours"],
        ),
    )


def _evaluate_service_training(
    pathways,
    service_years,
    training_hours,
):
    if service_years is None:
        return {
            "satisfied": False,
            "known": False,
            "pathway": None,
        }

    for pathway in pathways:
        if (
            service_years >= pathway["service_years"]
            and training_hours
            >= Decimal(str(pathway["training_hours"]))
        ):
            return {
                "satisfied": True,
                "known": True,
                "pathway": {
                    "type": "SERVICE_TRAINING",
                    **pathway,
                },
            }

    return {
        "satisfied": False,
        "known": True,
        "pathway": None,
    }


def _evaluate_education(
    pathways,
    service_years,
    education_level,
):
    if service_years is None:
        return {
            "satisfied": False,
            "known": False,
            "pathway": None,
        }

    if education_level is None:
        return {
            "satisfied": False,
            "known": True,
            "pathway": None,
        }

    officer_rank = EDUCATION_RANK[education_level]

    for pathway in pathways:
        required_level = pathway["education_level"]

        if (
            service_years >= pathway["service_years"]
            and officer_rank
            >= EDUCATION_RANK[required_level]
        ):
            return {
                "satisfied": True,
                "known": True,
                "pathway": {
                    "type": "EDUCATION",
                    **pathway,
                },
            }

    return {
        "satisfied": False,
        "known": True,
        "pathway": None,
    }


def evaluate_peace_officer_proficiency(
    officer,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    credential = get_highest_peace_officer_certificate(
        officer
    )

    current_certificate = credential[
        "highest_certificate"
    ]

    next_certificate = _next_certificate(
        current_certificate
    )

    training_hours = _training_hours(officer)
    education_level = _education_level(officer)
    service_years = _service_years(
        officer,
        evaluation_date,
    )
    military_months = _military_months(officer)
    peace_officer_license_date = (
        _peace_officer_license_date(officer)
    )

    if next_certificate is None:
        return {
            "current_certificate": current_certificate,
            "current_certificate_date":
                credential["highest_certificate_date"],
            "next_certificate": None,
            "status": "TERMINAL",
            "service_years": service_years,
            "training_hours": float(training_hours),
            "education_level": education_level,
            "verified_military_months": military_months,
            "qualifying_pathway": None,
            "alternate_pathway_possible": False,
            "course_requirements": [],
            "missing_requirements": [],
        }

    if next_certificate == "Basic Peace Officer":
        rule = load_proficiency_rule(
            next_certificate,
            evaluation_date=evaluation_date,
        )

        course_result = evaluate_course_requirements(
            rule,
            officer.training_records,
            context={
                "peace_officer_license_date":
                    peace_officer_license_date,
            },
        )

        missing_requirements = [
            requirement["label"]
            for requirement in course_result["missing"]
        ]

        missing_data = [
            requirement["label"]
            for requirement in
            course_result["insufficient_data"]
        ]

        if service_years is None:
            status = "INSUFFICIENT_DATA"
        elif service_years < rule["minimum_service_years"]:
            status = "NOT_ELIGIBLE"
            missing_requirements = [
                (
                    f"{rule['minimum_service_years']} year "
                    "of qualifying peace-officer service"
                ),
                *missing_requirements,
            ]
        elif missing_data:
            status = "INSUFFICIENT_DATA"
        elif missing_requirements:
            status = "NOT_ELIGIBLE"
        else:
            status = "ELIGIBLE"

        return {
            "current_certificate": current_certificate,
            "current_certificate_date":
                credential["highest_certificate_date"],
            "next_certificate": next_certificate,
            "status": status,
            "service_years": service_years,
            "training_hours": float(training_hours),
            "education_level": education_level,
            "verified_military_months":
                military_months,
            "peace_officer_license_date": (
                peace_officer_license_date.isoformat()
                if peace_officer_license_date
                else None
            ),
            "qualifying_pathway": (
                {
                    "type": "SERVICE",
                    "service_years":
                        rule["minimum_service_years"],
                }
                if (
                    service_years is not None
                    and service_years
                    >= rule["minimum_service_years"]
                )
                else None
            ),
            "alternate_pathway_possible": False,
            "pathway_results": {},
            "course_requirements":
                course_result["requirements"],
            "missing_requirements":
                missing_requirements,
            "insufficient_data_requirements":
                missing_data,
            "rule_version": rule["rule_version"],
        }

    rules = PROFICIENCY_PATHWAYS[next_certificate]

    service_training = _evaluate_service_training(
        rules["service_training"],
        service_years,
        training_hours,
    )

    best_available_pathway = (
        _best_service_training_pathway(
            rules["service_training"],
            service_years,
            training_hours,
        )
    )

    education = _evaluate_education(
        rules["education"],
        service_years,
        education_level,
    )

    military = _evaluate_military(
        rules["military"],
        service_years,
        military_months,
    )

    qualifying_pathway = (
        service_training["pathway"]
        or education["pathway"]
        or military["pathway"]
    )

    pathway_known = (
        service_training["known"]
        and education["known"]
        and military["known"]
    )

    rule = load_proficiency_rule(
        next_certificate,
        evaluation_date=evaluation_date,
    )

    course_result = evaluate_course_requirements(
        rule,
        officer.training_records,
        context={
            "peace_officer_license_date":
                peace_officer_license_date,
        },
    )

    missing_course_requirements = [
        requirement["label"]
        for requirement in course_result["missing"]
    ]

    insufficient_course_data = [
        requirement["label"]
        for requirement in
        course_result["insufficient_data"]
    ]

    if qualifying_pathway is None:
        if not pathway_known:
            status = "INSUFFICIENT_DATA"
        else:
            status = "NOT_ELIGIBLE"
    elif insufficient_course_data:
        status = "INSUFFICIENT_DATA"
    elif missing_course_requirements:
        status = "NOT_ELIGIBLE"
    else:
        status = "ELIGIBLE"

    return {
        "current_certificate": current_certificate,
        "current_certificate_date":
            credential["highest_certificate_date"],
        "next_certificate": next_certificate,
        "status": status,
        "service_years": service_years,
        "training_hours": float(training_hours),
        "education_level": education_level,
        "verified_military_months": military_months,
        "qualifying_pathway": qualifying_pathway,
        "best_available_pathway":
            best_available_pathway,
        "alternate_pathway_possible": (
            military_months is None
            and bool(rules["military"])
        ),
        "pathway_results": {
            "service_training": service_training,
            "education": education,
            "military": military,
        },
        "peace_officer_license_date": (
            peace_officer_license_date.isoformat()
            if peace_officer_license_date
            else None
        ),
        "course_requirements":
            course_result["requirements"],
        "missing_requirements":
            missing_course_requirements,
        "insufficient_data_requirements":
            insufficient_course_data,
        "rule_version": rule["rule_version"],
    }
