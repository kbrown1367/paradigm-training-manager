from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import Agency, Officer, OfficerAssignment


ASSIGNMENT_TYPES = {
    "POLICE_CHIEF": "Police Chief",
    "SUPERVISOR": "Supervisor",
    "PUBLIC_INFORMATION_OFFICER": "Public Information Officer",
    "SHERIFF": "Sheriff",
    "CONSTABLE": "Constable",
    "DEPUTY_CONSTABLE": "Deputy Constable",
}


class AssignmentError(ValueError):
    pass


def parse_assignment_date(value, field_name):
    if isinstance(value, date):
        return value

    value = (value or "").strip()

    if not value:
        raise AssignmentError(
            f"{field_name} is required."
        )

    try:
        return datetime.strptime(
            value,
            "%Y-%m-%d",
        ).date()
    except ValueError as exc:
        raise AssignmentError(
            f"{field_name} must use YYYY-MM-DD format."
        ) from exc


def get_officer_for_agency(agency_id, officer_id):
    agency = db.session.get(
        Agency,
        agency_id,
    )

    if agency is None:
        raise AssignmentError(
            "Agency does not exist."
        )

    officer = Officer.query.filter_by(
        id=officer_id,
        agency_id=agency_id,
    ).one_or_none()

    if officer is None:
        raise AssignmentError(
            "Officer does not exist for this agency."
        )

    return officer


def serialize_assignment(assignment):
    return {
        "id": str(assignment.id),
        "assignment_type": assignment.assignment_type,
        "assignment_name": ASSIGNMENT_TYPES.get(
            assignment.assignment_type,
            assignment.assignment_type,
        ),
        "effective_date": (
            assignment.effective_date.isoformat()
        ),
        "end_date": (
            assignment.end_date.isoformat()
            if assignment.end_date is not None
            else None
        ),
        "active": assignment.end_date is None,
    }


def list_assignments(
    agency_id,
    officer_id,
):
    officer = get_officer_for_agency(
        agency_id,
        officer_id,
    )

    assignments = (
        OfficerAssignment.query
        .filter_by(
            agency_id=agency_id,
            officer_id=officer.id,
        )
        .order_by(
            OfficerAssignment.effective_date,
            OfficerAssignment.assignment_type,
        )
        .all()
    )

    return [
        serialize_assignment(assignment)
        for assignment in assignments
    ]


def activate_assignment(
    agency_id,
    officer_id,
    assignment_type,
    effective_date,
):
    officer = get_officer_for_agency(
        agency_id,
        officer_id,
    )

    assignment_type = (
        assignment_type or ""
    ).strip().upper()

    if assignment_type not in ASSIGNMENT_TYPES:
        raise AssignmentError(
            "Assignment type is invalid."
        )

    effective_date = parse_assignment_date(
        effective_date,
        "effective_date",
    )

    existing_active = (
        OfficerAssignment.query
        .filter_by(
            agency_id=agency_id,
            officer_id=officer.id,
            assignment_type=assignment_type,
            end_date=None,
        )
        .one_or_none()
    )

    if existing_active is not None:
        raise AssignmentError(
            f"{ASSIGNMENT_TYPES[assignment_type]} "
            "is already active for this officer."
        )

    # An agency may have only one active Police Chief.
    # This rule is enforced here so it cannot be bypassed
    # by calling the API directly.
    if assignment_type == "POLICE_CHIEF":
        existing_chief = (
            OfficerAssignment.query
            .filter_by(
                agency_id=agency_id,
                assignment_type="POLICE_CHIEF",
                end_date=None,
            )
            .one_or_none()
        )

        if existing_chief is not None:
            chief_officer = db.session.get(
                Officer,
                existing_chief.officer_id,
            )

            chief_name = "another officer"

            if chief_officer is not None:
                chief_name = " ".join(
                    part
                    for part in [
                        chief_officer.first_name,
                        chief_officer.middle_name,
                        chief_officer.last_name,
                    ]
                    if part
                )

            raise AssignmentError(
                "Police Chief is already assigned to "
                f"{chief_name}."
            )

    assignment = OfficerAssignment(
        agency_id=agency_id,
        officer_id=officer.id,
        assignment_type=assignment_type,
        effective_date=effective_date,
    )

    db.session.add(assignment)
    db.session.commit()

    return serialize_assignment(assignment)


def end_assignment(
    agency_id,
    officer_id,
    assignment_type,
    inactive_date,
):
    officer = get_officer_for_agency(
        agency_id,
        officer_id,
    )

    assignment_type = (
        assignment_type or ""
    ).strip().upper()

    if assignment_type not in ASSIGNMENT_TYPES:
        raise AssignmentError(
            "Assignment type is invalid."
        )

    inactive_date = parse_assignment_date(
        inactive_date,
        "inactive_date",
    )

    assignment = (
        OfficerAssignment.query
        .filter_by(
            agency_id=agency_id,
            officer_id=officer.id,
            assignment_type=assignment_type,
            end_date=None,
        )
        .one_or_none()
    )

    if assignment is None:
        raise AssignmentError(
            f"{ASSIGNMENT_TYPES[assignment_type]} "
            "is not currently active for this officer."
        )

    # inactive_date is the first date on which the
    # assignment no longer applies. OfficerAssignment.end_date
    # remains the final date on which it did apply.
    last_active_date = (
        inactive_date - timedelta(days=1)
    )

    if inactive_date < assignment.effective_date:
        raise AssignmentError(
            "inactive_date cannot be before "
            "effective_date."
        )

    # A same-day ON/OFF action has no complete calendar
    # day of applicability in PTM's date-based model.
    # Remove that newly created assignment rather than
    # create an impossible end date before its start date.
    if inactive_date == assignment.effective_date:
        db.session.delete(assignment)
        db.session.commit()

        return {
            "assignment_type": assignment_type,
            "assignment_name":
                ASSIGNMENT_TYPES[assignment_type],
            "active": False,
            "effective_date": None,
            "end_date": None,
            "removed_same_day": True,
        }

    assignment.end_date = last_active_date

    db.session.commit()

    return serialize_assignment(assignment)


def get_assignment_summary(
    agency_id,
    officer_id,
):
    officer = get_officer_for_agency(
        agency_id,
        officer_id,
    )

    active_assignments = {
        assignment.assignment_type: assignment
        for assignment in OfficerAssignment.query.filter_by(
            agency_id=agency_id,
            officer_id=officer.id,
            end_date=None,
        ).all()
    }

    active_chief = (
        OfficerAssignment.query
        .filter_by(
            agency_id=agency_id,
            assignment_type="POLICE_CHIEF",
            end_date=None,
        )
        .one_or_none()
    )

    chief_holder = None

    if active_chief is not None:
        chief_officer = db.session.get(
            Officer,
            active_chief.officer_id,
        )

        if chief_officer is not None:
            chief_holder = {
                "officer_id": str(chief_officer.id),
                "name": " ".join(
                    part
                    for part in [
                        chief_officer.first_name,
                        chief_officer.middle_name,
                        chief_officer.last_name,
                    ]
                    if part
                ),
            }

    return {
        "officer_id": str(officer.id),
        "chief_holder": chief_holder,
        "assignment_types": [
            {
                "assignment_type": assignment_type,
                "assignment_name": assignment_name,
                "active": assignment_type
                in active_assignments,
                "effective_date": (
                    active_assignments[
                        assignment_type
                    ].effective_date.isoformat()
                    if assignment_type
                    in active_assignments
                    else None
                ),
            }
            for assignment_type, assignment_name
            in ASSIGNMENT_TYPES.items()
        ],
    }
