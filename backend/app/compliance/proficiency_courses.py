from datetime import date

from app.compliance.training_calendar import get_unit


def _course_number(record):
    return str(record.course_number or "").strip()


def _completed_direct_course(
    training_records,
    accepted_courses,
):
    accepted = set(accepted_courses or [])

    matches = [
        record
        for record in training_records
        if _course_number(record) in accepted
    ]

    if not matches:
        return None

    matches.sort(
        key=lambda record: (
            record.course_date is None,
            record.course_date,
        )
    )

    return matches[0]


def _completed_dated_equivalency(
    training_records,
    equivalencies,
):
    for equivalency in equivalencies or []:
        accepted = set(equivalency["courses"])

        before = equivalency.get("completed_before")
        before_date = (
            date.fromisoformat(before)
            if before
            else None
        )

        matches = []

        for record in training_records:
            if _course_number(record) not in accepted:
                continue

            if record.course_date is None:
                continue

            if (
                before_date is not None
                and record.course_date > before_date
            ):
                continue

            matches.append(record)

        if matches:
            matches.sort(
                key=lambda record: record.course_date
            )
            return {
                "type": "DATED_EQUIVALENCY",
                "courses": [
                    {
                        "course_number":
                            _course_number(matches[0]),
                        "course_date":
                            matches[0].course_date.isoformat(),
                    }
                ],
            }

    return None


def _same_two_year_unit(records):
    if not records:
        return False

    if any(
        record.course_date is None
        for record in records
    ):
        return False

    units = {
        (
            get_unit(record.course_date)["start"],
            get_unit(record.course_date)["end"],
        )
        for record in records
    }

    return len(units) == 1


def _completed_course_group(
    training_records,
    groups,
):
    for group in groups or []:
        required_courses = group.get("courses", [])

        if not group.get("require_all", False):
            continue

        if group.get("same_two_year_unit"):
            records_by_unit = {}

            for record in training_records:
                course_number = _course_number(record)

                if course_number not in required_courses:
                    continue

                if record.course_date is None:
                    continue

                unit = get_unit(record.course_date)

                unit_key = (
                    unit["start"],
                    unit["end"],
                )

                records_by_unit.setdefault(
                    unit_key,
                    {},
                )

                existing = records_by_unit[
                    unit_key
                ].get(course_number)

                if (
                    existing is None
                    or record.course_date
                    < existing.course_date
                ):
                    records_by_unit[
                        unit_key
                    ][course_number] = record

            for unit_key in sorted(records_by_unit):
                unit_records = records_by_unit[unit_key]

                if not all(
                    required_course in unit_records
                    for required_course in required_courses
                ):
                    continue

                selected = [
                    unit_records[required_course]
                    for required_course in required_courses
                ]

                return {
                    "type": "COURSE_GROUP",
                    "courses": [
                        {
                            "course_number":
                                _course_number(record),
                            "course_date":
                                record.course_date.isoformat(),
                        }
                        for record in selected
                    ],
                    "training_unit": {
                        "start":
                            unit_key[0].isoformat(),
                        "end":
                            unit_key[1].isoformat(),
                    },
                }

            continue

        selected = []

        for required_course in required_courses:
            matches = [
                record
                for record in training_records
                if _course_number(record)
                == required_course
            ]

            if not matches:
                selected = []
                break

            matches.sort(
                key=lambda record: (
                    record.course_date is None,
                    record.course_date,
                )
            )

            selected.append(matches[0])

        if not selected:
            continue

        return {
            "type": "COURSE_GROUP",
            "courses": [
                {
                    "course_number":
                        _course_number(record),
                    "course_date":
                        (
                            record.course_date.isoformat()
                            if record.course_date
                            else None
                        ),
                }
                for record in selected
            ],
        }

    return None


def _requirement_applicable(
    requirement,
    context,
):
    applicability = requirement.get("applicability")

    if not applicability:
        return True, None

    license_on_or_after = applicability.get(
        "peace_officer_license_on_or_after"
    )

    if license_on_or_after:
        license_date = context.get(
            "peace_officer_license_date"
        )

        if license_date is None:
            return None, (
                "Peace Officer license date is required "
                "to determine applicability."
            )

        cutoff = date.fromisoformat(
            license_on_or_after
        )

        if license_date < cutoff:
            return False, None

    return True, None


def evaluate_course_requirement(
    requirement,
    training_records,
    context=None,
):
    context = context or {}
    accepted_courses = list(
        requirement.get("accepted_courses", [])
    )

    applicable, applicability_reason = (
        _requirement_applicable(
            requirement,
            context,
        )
    )

    if applicable is False:
        return {
            "id": requirement["id"],
            "label": requirement["label"],
            "accepted_courses": accepted_courses,
            "applicable": False,
            "status": "NOT_APPLICABLE",
            "satisfied_by": None,
            "reason": None,
        }

    if applicable is None:
        return {
            "id": requirement["id"],
            "label": requirement["label"],
            "accepted_courses": accepted_courses,
            "applicable": None,
            "status": "INSUFFICIENT_DATA",
            "satisfied_by": None,
            "reason": applicability_reason,
        }

    direct = _completed_direct_course(
        training_records,
        requirement.get("accepted_courses", []),
    )

    if direct is not None:
        return {
            "id": requirement["id"],
            "label": requirement["label"],
            "accepted_courses": accepted_courses,
            "applicable": True,
            "status": "MET",
            "satisfied_by": {
                "type": "COURSE",
                "courses": [
                    {
                        "course_number":
                            _course_number(direct),
                        "course_date":
                            (
                                direct.course_date.isoformat()
                                if direct.course_date
                                else None
                            ),
                    }
                ],
            },
            "reason": None,
        }

    group = _completed_course_group(
        training_records,
        requirement.get(
            "accepted_course_groups",
            [],
        ),
    )

    if group is not None:
        return {
            "id": requirement["id"],
            "label": requirement["label"],
            "accepted_courses": accepted_courses,
            "applicable": True,
            "status": "MET",
            "satisfied_by": group,
            "reason": None,
        }

    dated = _completed_dated_equivalency(
        training_records,
        requirement.get(
            "dated_equivalencies",
            [],
        ),
    )

    if dated is not None:
        return {
            "id": requirement["id"],
            "label": requirement["label"],
            "accepted_courses": accepted_courses,
            "applicable": True,
            "status": "MET",
            "satisfied_by": dated,
            "reason": None,
        }

    return {
        "id": requirement["id"],
        "label": requirement["label"],
        "accepted_courses": accepted_courses,
        "applicable": True,
        "status": "MISSING",
        "satisfied_by": None,
        "reason": None,
    }


def evaluate_course_requirements(
    rule,
    training_records,
    context=None,
):
    results = [
        evaluate_course_requirement(
            requirement,
            training_records,
            context=context,
        )
        for requirement in rule.get(
            "required_courses",
            []
        )
    ]

    missing = [
        result
        for result in results
        if result["status"] == "MISSING"
    ]

    insufficient = [
        result
        for result in results
        if result["status"]
        == "INSUFFICIENT_DATA"
    ]

    return {
        "requirements": results,
        "missing": missing,
        "insufficient_data": insufficient,
        "all_satisfied": (
            not missing
            and not insufficient
        ),
    }
