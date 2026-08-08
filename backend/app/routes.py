from flask import Blueprint, jsonify, request

from app.models import Agency, Officer
from app.services.officer_assignments import (
    ASSIGNMENT_TYPES,
    AssignmentError,
    activate_assignment,
    end_assignment,
    get_assignment_summary,
    list_assignments,
)
from app.compliance.peace_officer_unit import (
    evaluate_agency_peace_officers,
)
from app.compliance.police_chief import (
    evaluate_police_chief,
)
from app.services.tcole_import import (
    TcoleImportError,
    get_import_summary,
    run_tcole_import,
)


api = Blueprint("api", __name__)


@api.get("/agencies")
def list_agencies():
    agencies = Agency.query.order_by(Agency.name).all()

    return jsonify(
        [
            {
                "id": str(agency.id),
                "name": agency.name,
            }
            for agency in agencies
        ]
    ), 200


@api.post("/agencies/<uuid:agency_id>/imports/tcole")
def import_tcole_records(agency_id):
    awards_file = request.files.get("awards_file")
    courses_file = request.files.get("courses_file")
    cycle_file = request.files.get("cycle_file")

    if (
        awards_file is None
        or courses_file is None
        or cycle_file is None
    ):
        return (
            jsonify(
                {
                    "error": (
                        "awards_file, courses_file, "
                        "and cycle_file are required."
                    )
                }
            ),
            400,
        )

    try:
        result = run_tcole_import(
            agency_id=agency_id,
            awards_content=awards_file.read(),
            courses_content=courses_file.read(),
            cycle_content=cycle_file.read(),
            awards_filename=awards_file.filename or "rptAwards.csv",
            courses_filename=(
                courses_file.filename or "rptCourseTaken.csv"
            ),
            cycle_filename=cycle_file.filename or "rptCycleT_All.csv",
        )
    except TcoleImportError as exc:
        return jsonify({"error": str(exc)}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(result), 201


@api.get("/agencies/<uuid:agency_id>/imports/<uuid:import_job_id>")
def import_summary(agency_id, import_job_id):
    try:
        result = get_import_summary(
            import_job_id=import_job_id,
            agency_id=agency_id,
        )
    except TcoleImportError as exc:
        return jsonify({"error": str(exc)}), 404

    return jsonify(result), 200


@api.get("/agencies/<uuid:agency_id>/compliance/peace-officer-unit")
def peace_officer_unit_compliance(agency_id):
    agency = Agency.query.filter_by(
        id=agency_id
    ).one_or_none()

    if agency is None:
        return jsonify({"error": "Agency not found."}), 404

    result = evaluate_agency_peace_officers(
        agency_id
    )

    return jsonify(result), 200


@api.get("/agencies/<uuid:agency_id>/officers")
def list_agency_officers(agency_id):
    agency = Agency.query.filter_by(
        id=agency_id
    ).one_or_none()

    if agency is None:
        return jsonify(
            {"error": "Agency not found."}
        ), 404

    include_archived = (
        request.args.get(
            "include_archived",
            "false",
        ).lower()
        == "true"
    )

    query = Officer.query.filter_by(
        agency_id=agency_id
    )

    if not include_archived:
        query = query.filter(
            Officer.employment_status
            != "archived"
        )

    officers = query.order_by(
        Officer.last_name,
        Officer.first_name,
    ).all()

    return jsonify(
        [
            {
                "id": str(officer.id),
                "tcole_pid": officer.tcole_pid,
                "first_name": officer.first_name,
                "middle_name": officer.middle_name,
                "last_name": officer.last_name,
                "name": " ".join(
                    part
                    for part in [
                        officer.first_name,
                        officer.middle_name,
                        officer.last_name,
                    ]
                    if part
                ),
                "employment_status": (
                    officer.employment_status
                ),
                "archived_at": (
                    officer.archived_at.isoformat()
                    if officer.archived_at
                    is not None
                    else None
                ),
            }
            for officer in officers
        ]
    ), 200


@api.get(
    "/agencies/<uuid:agency_id>"
    "/officers/<uuid:officer_id>/assignments"
)
def officer_assignments(
    agency_id,
    officer_id,
):
    try:
        result = list_assignments(
            agency_id,
            officer_id,
        )
    except AssignmentError as exc:
        return jsonify(
            {"error": str(exc)}
        ), 404

    return jsonify(result), 200


@api.get(
    "/agencies/<uuid:agency_id>"
    "/officers/<uuid:officer_id>"
    "/assignment-summary"
)
def officer_assignment_summary(
    agency_id,
    officer_id,
):
    try:
        result = get_assignment_summary(
            agency_id,
            officer_id,
        )
    except AssignmentError as exc:
        return jsonify(
            {"error": str(exc)}
        ), 404

    return jsonify(result), 200


@api.post(
    "/agencies/<uuid:agency_id>"
    "/officers/<uuid:officer_id>"
    "/assignments/<assignment_type>"
)
def activate_officer_assignment(
    agency_id,
    officer_id,
    assignment_type,
):
    payload = request.get_json(
        silent=True
    ) or {}

    try:
        result = activate_assignment(
            agency_id=agency_id,
            officer_id=officer_id,
            assignment_type=assignment_type,
            effective_date=payload.get(
                "effective_date"
            ),
        )
    except AssignmentError as exc:
        return jsonify(
            {"error": str(exc)}
        ), 400

    return jsonify(result), 201


@api.patch(
    "/agencies/<uuid:agency_id>"
    "/officers/<uuid:officer_id>"
    "/assignments/<assignment_type>"
)
def end_officer_assignment(
    agency_id,
    officer_id,
    assignment_type,
):
    payload = request.get_json(
        silent=True
    ) or {}

    try:
        result = end_assignment(
            agency_id=agency_id,
            officer_id=officer_id,
            assignment_type=assignment_type,
            end_date=payload.get(
                "end_date"
            ),
        )
    except AssignmentError as exc:
        return jsonify(
            {"error": str(exc)}
        ), 400

    return jsonify(result), 200


@api.get("/assignment-types")
def assignment_types():
    return jsonify(
        [
            {
                "assignment_type": key,
                "assignment_name": value,
            }
            for key, value
            in ASSIGNMENT_TYPES.items()
        ]
    ), 200


@api.get(
    "/agencies/<uuid:agency_id>"
    "/officers/<uuid:officer_id>"
    "/compliance/police-chief"
)
def police_chief_compliance(
    agency_id,
    officer_id,
):
    officer = Officer.query.filter_by(
        id=officer_id,
        agency_id=agency_id,
    ).one_or_none()

    if officer is None:
        return jsonify(
            {"error": "Officer not found."}
        ), 404

    result = evaluate_police_chief(
        officer
    )

    return jsonify(result), 200
