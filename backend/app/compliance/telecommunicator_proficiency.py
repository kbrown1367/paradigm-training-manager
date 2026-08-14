import json
from datetime import date
from pathlib import Path


BASIC_RULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "rules"
    / "data"
    / "telecommunicator_proficiency_basic.json"
)


INTERMEDIATE_RULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "rules"
    / "data"
    / "telecommunicator_proficiency_intermediate.json"
)


ADVANCED_RULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "rules"
    / "data"
    / "telecommunicator_proficiency_advanced.json"
)


MASTER_RULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "rules"
    / "data"
    / "telecommunicator_proficiency_master.json"
)


TELECOMMUNICATOR_CERTIFICATE_SEQUENCE = (
    "Basic Telecommunicator",
    "Intermediate Telecommunicator",
    "Advanced Telecommunicator",
    "Master Telecommunicator",
)


TELECOMMUNICATOR_CERTIFICATE_ALIASES = {
    "Basic Telecommunicator": {
        "Basic Telecommunicator",
        "Basic Telecommunicator Proficiency",
    },
    "Intermediate Telecommunicator": {
        "Intermediate Telecommunicator",
        "Intermediate Telecommunicator Proficiency",
    },
    "Advanced Telecommunicator": {
        "Advanced Telecommunicator",
        "Advanced Telecommunicator Proficiency",
    },
    "Master Telecommunicator": {
        "Master Telecommunicator",
        "Master Telecommunicator Proficiency",
    },
}


def load_basic_telecommunicator_rule():
    with BASIC_RULE_PATH.open() as file:
        return json.load(file)



def load_intermediate_telecommunicator_rule():
    with INTERMEDIATE_RULE_PATH.open() as file:
        return json.load(file)



def load_advanced_telecommunicator_rule():
    with ADVANCED_RULE_PATH.open() as file:
        return json.load(file)



def load_master_telecommunicator_rule():
    with MASTER_RULE_PATH.open() as file:
        return json.load(file)


def _normalize_award_name(value):
    return " ".join(
        (value or "").strip().split()
    )


def get_highest_telecommunicator_certificate(officer):
    certificate_dates = {}

    for award in officer.awards:
        if award.award_type != "Certificate":
            continue

        normalized_name = _normalize_award_name(
            award.award_name
        )

        for canonical, aliases in (
            TELECOMMUNICATOR_CERTIFICATE_ALIASES.items()
        ):
            if normalized_name not in aliases:
                continue

            existing = certificate_dates.get(canonical)

            if (
                existing is None
                or award.award_date > existing
            ):
                certificate_dates[canonical] = (
                    award.award_date
                )

    highest = None

    for certificate in (
        TELECOMMUNICATOR_CERTIFICATE_SEQUENCE
    ):
        if certificate in certificate_dates:
            highest = certificate

    if highest is None:
        return {
            "highest_certificate": None,
            "highest_certificate_date": None,
            "certificate_level": None,
        }

    return {
        "highest_certificate": highest,
        "highest_certificate_date": (
            certificate_dates[highest].isoformat()
        ),
        "certificate_level": (
            highest
            .replace(" Telecommunicator", "")
            .upper()
        ),
    }


def _telecommunicator_certificate_levels(officer):
    levels = set()

    for award in officer.awards:
        if award.award_type != "Certificate":
            continue

        normalized_name = _normalize_award_name(
            award.award_name
        )

        for canonical, aliases in (
            TELECOMMUNICATOR_CERTIFICATE_ALIASES.items()
        ):
            if normalized_name not in aliases:
                continue

            level = (
                canonical
                .replace(" Telecommunicator", "")
                .upper()
            )

            levels.add(level)

    return levels


def has_telecommunicator_license(officer):
    license_names = {
        "Telecommunicator License",
        "Telecommunications Operator License",
    }

    award_present = any(
        award.award_type == "License"
        and _normalize_award_name(
            award.award_name
        )
        in license_names
        for award in officer.awards
    )

    # The current Department Licensee Search report is also
    # an authoritative source for the active appointment
    # start date. A populated date therefore establishes
    # applicability even when the Awards report does not
    # contain a corresponding License row.
    return (
        award_present
        or officer.telecommunicator_service_start_date
        is not None
    )


def _telecommunicator_service_start_date(
    officer,
):
    """
    Resolve the best available Telecommunicator service date.

    Priority:
    1. Department Licensee Search service-date field.
    2. Earliest recognized TCOLE Telecommunicator license
       award already stored for the employee.
    """

    if (
        officer.telecommunicator_service_start_date
        is not None
    ):
        return (
            officer.telecommunicator_service_start_date
        )

    recognized_license_names = {
        "Telecommunicator License",
        "Telecommunications Operator License",
    }

    license_dates = [
        award.award_date
        for award in officer.awards
        if (
            award.award_type == "License"
            and _normalize_award_name(
                award.award_name
            ) in recognized_license_names
            and award.award_date is not None
        )
    ]

    if not license_dates:
        return None

    return min(license_dates)


def _service_years(
    officer,
    evaluation_date,
):
    start_date = (
        _telecommunicator_service_start_date(
            officer
        )
    )

    if start_date is None:
        return None

    if start_date > evaluation_date:
        return None

    years = (
        evaluation_date.year
        - start_date.year
    )

    if (
        evaluation_date.month,
        evaluation_date.day,
    ) < (
        start_date.month,
        start_date.day,
    ):
        years -= 1

    return years


def _subtract_months(value, months):
    year = value.year
    month = value.month - months

    while month <= 0:
        month += 12
        year -= 1

    month_lengths = (
        31,
        29 if (
            year % 4 == 0
            and (
                year % 100 != 0
                or year % 400 == 0
            )
        ) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    )

    day = min(
        value.day,
        month_lengths[month - 1],
    )

    return date(
        year,
        month,
        day,
    )


def _find_course(
    officer,
    accepted_courses,
):
    accepted = {
        str(number)
        for number in accepted_courses
    }

    matches = [
        record
        for record in officer.training_records
        if str(record.course_number) in accepted
    ]

    if not matches:
        return None

    return max(
        matches,
        key=lambda record: record.course_date,
    )


def _training_hours(officer):
    total = 0.0

    for record in officer.training_records:
        if record.credited_hours is None:
            continue

        total += float(record.credited_hours)

    return total


def _career_course_requirement_result(
    officer,
    requirement,
):
    match = _find_course(
        officer,
        requirement["accepted_courses"],
    )

    return {
        "id": requirement["id"],
        "name": requirement["name"],
        "label": requirement["name"],
        "accepted_courses":
            requirement["accepted_courses"],
        "required": True,
        "status": (
            "COMPLETE"
            if match is not None
            else "MISSING"
        ),
        "matched_course": (
            {
                "course_number":
                    match.course_number,
                "course_title":
                    match.course_title,
                "course_date":
                    match.course_date.isoformat(),
            }
            if match is not None
            else None
        ),
    }


def _appointment_requirement_applies(
    officer,
    threshold_value,
):
    appointment_date = (
        officer.telecommunicator_service_start_date
    )

    if appointment_date is None:
        return None

    threshold = date.fromisoformat(
        threshold_value
    )

    return appointment_date > threshold


def _course_requirement_result(
    officer,
    requirement,
    evaluation_date,
):
    applicability = (
        requirement.get("applicability")
        or {}
    )

    applicability_type = applicability.get(
        "type",
        "ALWAYS",
    )

    required = True
    insufficient_data = False

    if applicability_type == "APPOINTMENT_DATE_AFTER":
        applies = _appointment_requirement_applies(
            officer,
            applicability["date"],
        )

        if applies is None:
            required = False
            insufficient_data = True
        else:
            required = applies

    elif applicability_type == "EVALUATION_DATE_AFTER":
        threshold = date.fromisoformat(
            applicability["date"]
        )
        required = evaluation_date > threshold

    elif applicability_type != "ALWAYS":
        raise ValueError(
            "Unsupported Telecommunicator course "
            f"applicability type: {applicability_type}"
        )

    match = (
        _find_course(
            officer,
            requirement["accepted_courses"],
        )
        if required
        else None
    )

    if insufficient_data:
        status = "INSUFFICIENT_DATA"
    elif not required:
        status = "NOT_APPLICABLE"
    elif match is not None:
        status = "COMPLETE"
    else:
        status = "MISSING"

    return {
        "id": requirement["id"],
        "name": requirement["name"],
        "label": requirement["name"],
        "accepted_courses":
            requirement["accepted_courses"],
        "required": required,
        "status": status,
        "applicability": applicability,
        "matched_course": (
            {
                "course_number":
                    match.course_number,
                "course_title":
                    match.course_title,
                "course_date":
                    match.course_date.isoformat(),
            }
            if match is not None
            else None
        ),
    }


def _recent_tdd_tty_result(
    officer,
    rule,
    evaluation_date,
):
    accepted = {
        str(number)
        for number in rule["accepted_courses"]
    }

    lookback_start = _subtract_months(
        evaluation_date,
        rule["lookback_months"],
    )

    matches = [
        record
        for record in officer.training_records
        if (
            str(record.course_number) in accepted
            and lookback_start
            <= record.course_date
            <= evaluation_date
        )
    ]

    match = (
        max(
            matches,
            key=lambda record: record.course_date,
        )
        if matches
        else None
    )

    return {
        "id": "RECENT_TDD_TTY",
        "name": rule["name"],
        "label": rule["name"],
        "accepted_courses":
            rule["accepted_courses"],
        "required": True,
        "status": (
            "COMPLETE"
            if match is not None
            else "MISSING"
        ),
        "lookback_months":
            rule["lookback_months"],
        "lookback_start":
            lookback_start.isoformat(),
        "matched_course": (
            {
                "course_number":
                    match.course_number,
                "course_title":
                    match.course_title,
                "course_date":
                    match.course_date.isoformat(),
            }
            if match is not None
            else None
        ),
    }


def evaluate_basic_telecommunicator_proficiency(
    officer,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    rule = load_basic_telecommunicator_rule()

    credential = (
        get_highest_telecommunicator_certificate(
            officer
        )
    )

    has_license = has_telecommunicator_license(
        officer
    )

    service_years = _service_years(
        officer,
        evaluation_date,
    )

    minimum_service_years = (
        rule["minimum_service_years"]
    )

    service_requirement_met = (
        service_years is not None
        and service_years
        >= minimum_service_years
    )

    course_requirements = [
        _course_requirement_result(
            officer,
            requirement,
            evaluation_date,
        )
        for requirement in rule["required_courses"]
    ]

    tdd_tty_requirement = _recent_tdd_tty_result(
        officer,
        rule["recent_tdd_tty"],
        evaluation_date,
    )

    course_requirements.append(
        tdd_tty_requirement
    )

    missing_courses = [
        item
        for item in course_requirements
        if item["status"] == "MISSING"
    ]

    insufficient_courses = [
        item
        for item in course_requirements
        if item["status"] == "INSUFFICIENT_DATA"
    ]

    existing_level = credential[
        "certificate_level"
    ]

    if existing_level in {
        "BASIC",
        "INTERMEDIATE",
        "ADVANCED",
        "MASTER",
    }:
        status = "AWARDED"

    elif not has_license:
        status = "NOT_APPLICABLE"

    elif (
        _telecommunicator_service_start_date(
            officer
        ) is None
        or service_years is None
        or insufficient_courses
    ):
        status = "INSUFFICIENT_DATA"

    elif not service_requirement_met:
        status = "NOT_ELIGIBLE"

    elif missing_courses:
        status = "NOT_ELIGIBLE"

    else:
        status = "ELIGIBLE"

    missing_requirements = []

    if (
        has_license
        and service_years is not None
        and not service_requirement_met
    ):
        missing_requirements.append(
            (
                f"{minimum_service_years} year "
                "of qualifying Telecommunicator service"
            )
        )

    missing_requirements.extend(
        item["name"]
        for item in missing_courses
    )

    insufficient_data_requirements = []

    if (
        has_license
        and _telecommunicator_service_start_date(
            officer
        ) is None
    ):
        insufficient_data_requirements.append(
            "Telecommunicator appointment/service start date"
        )

    insufficient_data_requirements.extend(
        item["name"]
        for item in insufficient_courses
    )

    return {
        "certificate": "Basic Telecommunicator",
        "status": status,
        "current_certificate":
            credential["highest_certificate"],
        "current_certificate_date":
            credential["highest_certificate_date"],
        "certificate_level":
            credential["certificate_level"],
        "has_telecommunicator_license":
            has_license,
        "telecommunicator_service_start_date": (
            officer.telecommunicator_service_start_date
            .isoformat()
            if officer.telecommunicator_service_start_date
            else None
        ),
        "service_years": service_years,
        "minimum_service_years":
            minimum_service_years,
        "service_requirement_met":
            service_requirement_met,
        "training_hours":
            _training_hours(officer),
        "minimum_training_hours":
            None,
        "course_requirements":
            course_requirements,
        "missing_requirements":
            missing_requirements,
        "insufficient_data_requirements":
            insufficient_data_requirements,
        "rule_set_id": rule["rule_set_id"],
        "rule_version": rule["rule_version"],
    }



def evaluate_intermediate_telecommunicator_proficiency(
    officer,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    rule = load_intermediate_telecommunicator_rule()

    credential = (
        get_highest_telecommunicator_certificate(
            officer
        )
    )

    has_license = has_telecommunicator_license(
        officer
    )

    current_certificate = credential[
        "highest_certificate"
    ]
    current_level = credential[
        "certificate_level"
    ]

    # If Intermediate or a higher Telecommunicator
    # certificate is already present, this level has
    # already been awarded.
    if current_level in {
        "INTERMEDIATE",
        "ADVANCED",
        "MASTER",
    }:
        return {
            "certificate":
                "Intermediate Telecommunicator",
            "status": "AWARDED",
            "current_certificate":
                current_certificate,
            "current_certificate_date":
                credential[
                    "highest_certificate_date"
                ],
            "certificate_level":
                current_level,
            "has_telecommunicator_license":
                has_license,
            "basic_prerequisite_met": True,
            "service_years":
                _service_years(
                    officer,
                    evaluation_date,
                ),
            "minimum_service_years":
                rule["minimum_service_years"],
            "training_hours":
                _training_hours(officer),
            "minimum_training_hours":
                rule["minimum_training_hours"],
            "course_requirements": [],
            "missing_requirements": [],
            "insufficient_data_requirements": [],
            "rule_set_id":
                rule["rule_set_id"],
            "rule_version":
                rule["rule_version"],
        }

    if not has_license:
        return {
            "certificate":
                "Intermediate Telecommunicator",
            "status": "NOT_APPLICABLE",
            "current_certificate":
                current_certificate,
            "current_certificate_date":
                credential[
                    "highest_certificate_date"
                ],
            "certificate_level":
                current_level,
            "has_telecommunicator_license":
                False,
            "basic_prerequisite_met":
                False,
            "service_years": None,
            "minimum_service_years":
                rule["minimum_service_years"],
            "training_hours":
                _training_hours(officer),
            "minimum_training_hours":
                rule["minimum_training_hours"],
            "course_requirements": [],
            "missing_requirements": [],
            "insufficient_data_requirements": [],
            "rule_set_id":
                rule["rule_set_id"],
            "rule_version":
                rule["rule_version"],
        }

    basic_prerequisite_met = (
        current_level == "BASIC"
    )

    service_years = _service_years(
        officer,
        evaluation_date,
    )

    training_hours = _training_hours(
        officer
    )

    minimum_service_years = (
        rule["minimum_service_years"]
    )

    minimum_training_hours = (
        rule["minimum_training_hours"]
    )

    service_requirement_met = (
        service_years is not None
        and service_years
        >= minimum_service_years
    )

    training_requirement_met = (
        training_hours >= minimum_training_hours
    )

    course_requirements = [
        _career_course_requirement_result(
            officer,
            requirement,
        )
        for requirement in (
            rule["required_course_categories"]
        )
    ]

    tdd_tty_requirement = _recent_tdd_tty_result(
        officer,
        rule["recent_tdd_tty"],
        evaluation_date,
    )

    course_requirements.append(
        tdd_tty_requirement
    )

    missing_courses = [
        item
        for item in course_requirements
        if item["status"] == "MISSING"
    ]

    insufficient_data_requirements = []

    if (
        _telecommunicator_service_start_date(
            officer
        ) is None
    ):
        insufficient_data_requirements.append(
            "Telecommunicator appointment/service start date"
        )

    missing_requirements = []

    if not basic_prerequisite_met:
        missing_requirements.append(
            "Basic Telecommunicator Certificate"
        )

    if (
        service_years is not None
        and not service_requirement_met
    ):
        years_short = (
            minimum_service_years
            - service_years
        )

        missing_requirements.append(
            (
                f"{years_short:g} additional year"
                f"{'s' if years_short != 1 else ''} "
                "of qualifying Telecommunicator service"
            )
        )

    if not training_requirement_met:
        hours_short = (
            minimum_training_hours
            - training_hours
        )

        missing_requirements.append(
            (
                f"{hours_short:g} additional "
                "TCOLE training hours"
            )
        )

    missing_requirements.extend(
        item["name"]
        for item in missing_courses
    )

    if insufficient_data_requirements:
        status = "INSUFFICIENT_DATA"

    elif (
        not basic_prerequisite_met
        or not service_requirement_met
        or not training_requirement_met
        or missing_courses
    ):
        status = "NOT_ELIGIBLE"

    else:
        status = "ELIGIBLE"

    return {
        "certificate":
            "Intermediate Telecommunicator",
        "status": status,
        "current_certificate":
            current_certificate,
        "current_certificate_date":
            credential[
                "highest_certificate_date"
            ],
        "certificate_level":
            current_level,
        "has_telecommunicator_license":
            has_license,
        "basic_prerequisite_met":
            basic_prerequisite_met,
        "service_years":
            service_years,
        "minimum_service_years":
            minimum_service_years,
        "service_requirement_met":
            service_requirement_met,
        "training_hours":
            training_hours,
        "minimum_training_hours":
            minimum_training_hours,
        "training_requirement_met":
            training_requirement_met,
        "course_requirements":
            course_requirements,
        "missing_requirements":
            missing_requirements,
        "insufficient_data_requirements":
            insufficient_data_requirements,
        "rule_set_id":
            rule["rule_set_id"],
        "rule_version":
            rule["rule_version"],
    }



def evaluate_advanced_telecommunicator_proficiency(
    officer,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    rule = load_advanced_telecommunicator_rule()

    credential = (
        get_highest_telecommunicator_certificate(
            officer
        )
    )

    has_license = has_telecommunicator_license(
        officer
    )

    current_certificate = credential[
        "highest_certificate"
    ]

    current_level = credential[
        "certificate_level"
    ]

    certificate_levels = (
        _telecommunicator_certificate_levels(
            officer
        )
    )

    # An officially awarded Advanced or Master
    # certificate means this level has already
    # been completed.
    if current_level in {
        "ADVANCED",
        "MASTER",
    }:
        return {
            "certificate":
                "Advanced Telecommunicator",
            "status": "AWARDED",
            "current_certificate":
                current_certificate,
            "current_certificate_date":
                credential[
                    "highest_certificate_date"
                ],
            "certificate_level":
                current_level,
            "has_telecommunicator_license":
                has_license,
            "basic_prerequisite_met": True,
            "intermediate_prerequisite_met": True,
            "service_years":
                _service_years(
                    officer,
                    evaluation_date,
                ),
            "minimum_service_years":
                rule["minimum_service_years"],
            "training_hours":
                _training_hours(officer),
            "minimum_training_hours":
                rule["minimum_training_hours"],
            "course_requirements": [],
            "missing_requirements": [],
            "insufficient_data_requirements": [],
            "rule_set_id":
                rule["rule_set_id"],
            "rule_version":
                rule["rule_version"],
        }

    if not has_license:
        return {
            "certificate":
                "Advanced Telecommunicator",
            "status": "NOT_APPLICABLE",
            "current_certificate":
                current_certificate,
            "current_certificate_date":
                credential[
                    "highest_certificate_date"
                ],
            "certificate_level":
                current_level,
            "has_telecommunicator_license":
                False,
            "basic_prerequisite_met":
                False,
            "intermediate_prerequisite_met":
                False,
            "service_years": None,
            "minimum_service_years":
                rule["minimum_service_years"],
            "training_hours":
                _training_hours(officer),
            "minimum_training_hours":
                rule["minimum_training_hours"],
            "course_requirements": [],
            "missing_requirements": [],
            "insufficient_data_requirements": [],
            "rule_set_id":
                rule["rule_set_id"],
            "rule_version":
                rule["rule_version"],
        }

    basic_prerequisite_met = (
        "BASIC" in certificate_levels
        or "INTERMEDIATE" in certificate_levels
    )

    intermediate_prerequisite_met = (
        "INTERMEDIATE" in certificate_levels
    )

    service_years = _service_years(
        officer,
        evaluation_date,
    )

    training_hours = _training_hours(
        officer
    )

    minimum_service_years = (
        rule["minimum_service_years"]
    )

    minimum_training_hours = (
        rule["minimum_training_hours"]
    )

    service_requirement_met = (
        service_years is not None
        and service_years
        >= minimum_service_years
    )

    training_requirement_met = (
        training_hours
        >= minimum_training_hours
    )

    course_requirements = [
        _career_course_requirement_result(
            officer,
            requirement,
        )
        for requirement in (
            rule["required_course_categories"]
        )
    ]

    course_requirements.append(
        _recent_tdd_tty_result(
            officer,
            rule["recent_tdd_tty"],
            evaluation_date,
        )
    )

    missing_courses = [
        item
        for item in course_requirements
        if item["status"] == "MISSING"
    ]

    insufficient_data_requirements = []

    if (
        _telecommunicator_service_start_date(
            officer
        ) is None
    ):
        insufficient_data_requirements.append(
            "Telecommunicator appointment/service start date"
        )

    missing_requirements = []

    if not basic_prerequisite_met:
        missing_requirements.append(
            "Basic Telecommunicator Certificate"
        )

    if not intermediate_prerequisite_met:
        missing_requirements.append(
            "Intermediate Telecommunicator Certificate"
        )

    if (
        service_years is not None
        and not service_requirement_met
    ):
        years_short = (
            minimum_service_years
            - service_years
        )

        missing_requirements.append(
            (
                f"{years_short:g} additional year"
                f"{'s' if years_short != 1 else ''} "
                "of qualifying Telecommunicator service"
            )
        )

    if not training_requirement_met:
        hours_short = (
            minimum_training_hours
            - training_hours
        )

        missing_requirements.append(
            (
                f"{hours_short:g} additional "
                "TCOLE training hours"
            )
        )

    missing_requirements.extend(
        item["name"]
        for item in missing_courses
    )

    if insufficient_data_requirements:
        status = "INSUFFICIENT_DATA"

    elif (
        not basic_prerequisite_met
        or not intermediate_prerequisite_met
        or not service_requirement_met
        or not training_requirement_met
        or missing_courses
    ):
        status = "NOT_ELIGIBLE"

    else:
        status = "ELIGIBLE"

    return {
        "certificate":
            "Advanced Telecommunicator",
        "status": status,
        "current_certificate":
            current_certificate,
        "current_certificate_date":
            credential[
                "highest_certificate_date"
            ],
        "certificate_level":
            current_level,
        "has_telecommunicator_license":
            has_license,
        "basic_prerequisite_met":
            basic_prerequisite_met,
        "intermediate_prerequisite_met":
            intermediate_prerequisite_met,
        "service_years":
            service_years,
        "minimum_service_years":
            minimum_service_years,
        "service_requirement_met":
            service_requirement_met,
        "training_hours":
            training_hours,
        "minimum_training_hours":
            minimum_training_hours,
        "training_requirement_met":
            training_requirement_met,
        "course_requirements":
            course_requirements,
        "missing_requirements":
            missing_requirements,
        "insufficient_data_requirements":
            insufficient_data_requirements,
        "rule_set_id":
            rule["rule_set_id"],
        "rule_version":
            rule["rule_version"],
    }



def evaluate_master_telecommunicator_proficiency(
    officer,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    rule = load_master_telecommunicator_rule()

    credential = (
        get_highest_telecommunicator_certificate(
            officer
        )
    )

    has_license = has_telecommunicator_license(
        officer
    )

    current_certificate = credential[
        "highest_certificate"
    ]

    current_level = credential[
        "certificate_level"
    ]

    certificate_levels = (
        _telecommunicator_certificate_levels(
            officer
        )
    )

    if current_level == "MASTER":
        return {
            "certificate":
                "Master Telecommunicator",
            "status": "AWARDED",
            "current_certificate":
                current_certificate,
            "current_certificate_date":
                credential[
                    "highest_certificate_date"
                ],
            "certificate_level":
                current_level,
            "has_telecommunicator_license":
                has_license,
            "basic_prerequisite_met": True,
            "intermediate_prerequisite_met": True,
            "advanced_prerequisite_met": True,
            "service_years":
                _service_years(
                    officer,
                    evaluation_date,
                ),
            "minimum_service_years":
                rule["minimum_service_years"],
            "training_hours":
                _training_hours(officer),
            "minimum_training_hours":
                rule["minimum_training_hours"],
            "course_requirements": [],
            "missing_requirements": [],
            "insufficient_data_requirements": [],
            "rule_set_id":
                rule["rule_set_id"],
            "rule_version":
                rule["rule_version"],
        }

    if not has_license:
        return {
            "certificate":
                "Master Telecommunicator",
            "status": "NOT_APPLICABLE",
            "current_certificate":
                current_certificate,
            "current_certificate_date":
                credential[
                    "highest_certificate_date"
                ],
            "certificate_level":
                current_level,
            "has_telecommunicator_license":
                False,
            "basic_prerequisite_met":
                False,
            "intermediate_prerequisite_met":
                False,
            "advanced_prerequisite_met":
                False,
            "service_years": None,
            "minimum_service_years":
                rule["minimum_service_years"],
            "training_hours":
                _training_hours(officer),
            "minimum_training_hours":
                rule["minimum_training_hours"],
            "course_requirements": [],
            "missing_requirements": [],
            "insufficient_data_requirements": [],
            "rule_set_id":
                rule["rule_set_id"],
            "rule_version":
                rule["rule_version"],
        }

    basic_prerequisite_met = (
        "BASIC" in certificate_levels
        or "INTERMEDIATE" in certificate_levels
        or "ADVANCED" in certificate_levels
    )

    intermediate_prerequisite_met = (
        "INTERMEDIATE" in certificate_levels
        or "ADVANCED" in certificate_levels
    )

    advanced_prerequisite_met = (
        "ADVANCED" in certificate_levels
    )

    service_years = _service_years(
        officer,
        evaluation_date,
    )

    training_hours = _training_hours(
        officer
    )

    minimum_service_years = (
        rule["minimum_service_years"]
    )

    minimum_training_hours = (
        rule["minimum_training_hours"]
    )

    service_requirement_met = (
        service_years is not None
        and service_years
        >= minimum_service_years
    )

    training_requirement_met = (
        training_hours
        >= minimum_training_hours
    )

    course_requirements = [
        _career_course_requirement_result(
            officer,
            requirement,
        )
        for requirement in (
            rule["required_course_categories"]
        )
    ]

    course_requirements.append(
        _recent_tdd_tty_result(
            officer,
            rule["recent_tdd_tty"],
            evaluation_date,
        )
    )

    missing_courses = [
        item
        for item in course_requirements
        if item["status"] == "MISSING"
    ]

    insufficient_data_requirements = []

    if (
        _telecommunicator_service_start_date(
            officer
        ) is None
    ):
        insufficient_data_requirements.append(
            "Telecommunicator appointment/service start date"
        )

    missing_requirements = []

    if not basic_prerequisite_met:
        missing_requirements.append(
            "Basic Telecommunicator Certificate"
        )

    if not intermediate_prerequisite_met:
        missing_requirements.append(
            "Intermediate Telecommunicator Certificate"
        )

    if not advanced_prerequisite_met:
        missing_requirements.append(
            "Advanced Telecommunicator Certificate"
        )

    if (
        service_years is not None
        and not service_requirement_met
    ):
        years_short = (
            minimum_service_years
            - service_years
        )

        missing_requirements.append(
            (
                f"{years_short:g} additional year"
                f"{'s' if years_short != 1 else ''} "
                "of qualifying Telecommunicator service"
            )
        )

    if not training_requirement_met:
        hours_short = (
            minimum_training_hours
            - training_hours
        )

        missing_requirements.append(
            (
                f"{hours_short:g} additional "
                "TCOLE training hours"
            )
        )

    missing_requirements.extend(
        item["name"]
        for item in missing_courses
    )

    if insufficient_data_requirements:
        status = "INSUFFICIENT_DATA"

    elif (
        not basic_prerequisite_met
        or not intermediate_prerequisite_met
        or not advanced_prerequisite_met
        or not service_requirement_met
        or not training_requirement_met
        or missing_courses
    ):
        status = "NOT_ELIGIBLE"

    else:
        status = "ELIGIBLE"

    return {
        "certificate":
            "Master Telecommunicator",
        "status": status,
        "current_certificate":
            current_certificate,
        "current_certificate_date":
            credential[
                "highest_certificate_date"
            ],
        "certificate_level":
            current_level,
        "has_telecommunicator_license":
            has_license,
        "basic_prerequisite_met":
            basic_prerequisite_met,
        "intermediate_prerequisite_met":
            intermediate_prerequisite_met,
        "advanced_prerequisite_met":
            advanced_prerequisite_met,
        "service_years":
            service_years,
        "minimum_service_years":
            minimum_service_years,
        "service_requirement_met":
            service_requirement_met,
        "training_hours":
            training_hours,
        "minimum_training_hours":
            minimum_training_hours,
        "training_requirement_met":
            training_requirement_met,
        "course_requirements":
            course_requirements,
        "missing_requirements":
            missing_requirements,
        "insufficient_data_requirements":
            insufficient_data_requirements,
        "rule_set_id":
            rule["rule_set_id"],
        "rule_version":
            rule["rule_version"],
    }



def evaluate_telecommunicator_proficiency(
    officer,
    evaluation_date=None,
):
    if evaluation_date is None:
        evaluation_date = date.today()

    credential = (
        get_highest_telecommunicator_certificate(
            officer
        )
    )

    current_certificate = credential[
        "highest_certificate"
    ]

    current_level = credential[
        "certificate_level"
    ]

    if not has_telecommunicator_license(officer):
        return {
            "status": "NOT_APPLICABLE",
            "current_certificate": None,
            "current_certificate_date": None,
            "next_certificate": None,
            "service_years": None,
            "training_hours": 0.0,
            "course_requirements": [],
            "missing_requirements": [],
            "insufficient_data_requirements": [],
            "rule_version": None,
        }

    if current_level == "MASTER":
        return {
            "status": "TERMINAL",
            "current_certificate":
                current_certificate,
            "current_certificate_date":
                credential[
                    "highest_certificate_date"
                ],
            "next_certificate": None,
            "service_years":
                _service_years(
                    officer,
                    evaluation_date,
                ),
            "training_hours":
                _training_hours(officer),
            "course_requirements": [],
            "missing_requirements": [],
            "insufficient_data_requirements": [],
            "rule_version": None,
        }

    if current_level == "ADVANCED":
        result = (
            evaluate_master_telecommunicator_proficiency(
                officer,
                evaluation_date=evaluation_date,
            )
        )
        result["next_certificate"] = (
            "Master Telecommunicator"
        )
        return result

    if current_level == "INTERMEDIATE":
        result = (
            evaluate_advanced_telecommunicator_proficiency(
                officer,
                evaluation_date=evaluation_date,
            )
        )
        result["next_certificate"] = (
            "Advanced Telecommunicator"
        )
        return result

    if current_level == "BASIC":
        result = (
            evaluate_intermediate_telecommunicator_proficiency(
                officer,
                evaluation_date=evaluation_date,
            )
        )
        result["next_certificate"] = (
            "Intermediate Telecommunicator"
        )
        return result

    result = (
        evaluate_basic_telecommunicator_proficiency(
            officer,
            evaluation_date=evaluation_date,
        )
    )

    result["next_certificate"] = (
        "Basic Telecommunicator"
    )

    return result
