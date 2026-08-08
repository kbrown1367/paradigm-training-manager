from flask import Blueprint, jsonify, request

from app.models import Agency
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
