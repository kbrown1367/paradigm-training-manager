# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.
#
# Paradigm Training Manager™ is proprietary and confidential software.
# Unauthorized copying, modification, distribution, or use is prohibited.
# Software ID: PTM-PSP-2026

from datetime import date
from io import BytesIO

from flask import (
    Blueprint,
    g,
    jsonify,
    request,
    send_file,
)

from app.authorization import (
    authorize_operational_api_request,
)
from app.auth import (
    ROLE_AGENCY_ADMIN,
    ROLE_PLATFORM_ADMIN,
)
from app.models import Agency, Officer
from app.services.credential_verifications import (
    CREDENTIAL_TYPES,
    CredentialVerificationError,
    list_verifications,
    revoke_verification,
    verify_credential,
)

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
from app.compliance.public_information_officer import (
    evaluate_public_information_officer,
)
from app.compliance.supervisor import (
    evaluate_supervisor,
)
from app.compliance.officer_profile import (
    evaluate_officer_compliance_profile,
)
from app.services.employee_workspace import (
    get_employee_workspace,
)
from app.services.license_tracking import (
    LicenseTrackingError,
    set_license_tracking,
)
from app.services.employee_lifecycle import (
    EmployeeLifecycleError,
    archive_employee,
    restore_employee,
)
from app.services.qualification_facts import (
    QualificationFactsError,
    get_qualification_facts,
    update_qualification_facts,
)
from app.services.compliance_email import (
    get_compliance_email,
)
from app.compliance.agency_dashboard import (
    evaluate_agency_compliance_dashboard,
)
from app.compliance.agency_report import (
    evaluate_agency_compliance_report,
)
from app.compliance.agency_report_pdf import (
    render_agency_compliance_pdf,
)
from app.services.bulk_compliance_communications import (
    build_bulk_compliance_preflight,
)
from app.extensions import db
from app.services.tcole_import import (
    TcoleImportError,
    get_import_summary,
    run_tcole_import,
    start_tcole_awards_import,
    run_tcole_courses_stage,
    run_tcole_cycle_stage,
    run_tcole_licensee_search_stage,
)


api = Blueprint("api", __name__)


@api.before_request
def enforce_operational_api_authorization():
    return authorize_operational_api_request()


@api.get("/agencies")
def list_agencies():
    user = g.current_user

    if user.role == ROLE_PLATFORM_ADMIN:
        agencies = (
            Agency.query
            .order_by(Agency.name)
            .all()
        )
    elif (
        user.role == ROLE_AGENCY_ADMIN
        and user.agency_id is not None
    ):
        agency = Agency.query.filter_by(
            id=user.agency_id,
        ).one_or_none()

        agencies = (
            [agency]
            if agency is not None
            else []
        )
    else:
        return jsonify(
            {
                "error":
                    "Resource not found."
            }
        ), 404

    return jsonify(
        [
            {
                "id": str(agency.id),
                "name": agency.name,
                "email_domain": agency.email_domain,
                "email_pattern": agency.email_pattern,
            }
            for agency in agencies
        ]
    ), 200


@api.post("/agencies/<uuid:agency_id>/imports/tcole/awards")
def import_tcole_awards_stage(agency_id):
    uploaded_file = request.files.get("file")

    if uploaded_file is None:
        return jsonify({"error": "file is required."}), 400

    try:
        result = start_tcole_awards_import(
            agency_id=agency_id,
            awards_content=uploaded_file.read(),
            awards_filename=(
                uploaded_file.filename or "rptAwards.csv"
            ),
        )
    except (TcoleImportError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(result), 201


@api.post(
    "/agencies/<uuid:agency_id>/imports/tcole/"
    "<uuid:import_job_id>/courses"
)
def import_tcole_courses_stage(
    agency_id,
    import_job_id,
):
    uploaded_file = request.files.get("file")

    if uploaded_file is None:
        return jsonify({"error": "file is required."}), 400

    try:
        result = run_tcole_courses_stage(
            agency_id=agency_id,
            import_job_id=import_job_id,
            courses_content=uploaded_file.read(),
            courses_filename=(
                uploaded_file.filename
                or "rptCourseTaken.csv"
            ),
        )
    except (TcoleImportError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(result), 200


@api.post(
    "/agencies/<uuid:agency_id>/imports/tcole/"
    "<uuid:import_job_id>/cycle"
)
def import_tcole_cycle_stage(
    agency_id,
    import_job_id,
):
    uploaded_file = request.files.get("file")

    if uploaded_file is None:
        return jsonify({"error": "file is required."}), 400

    try:
        result = run_tcole_cycle_stage(
            agency_id=agency_id,
            import_job_id=import_job_id,
            cycle_content=uploaded_file.read(),
            cycle_filename=(
                uploaded_file.filename
                or "rptCycleT_All.csv"
            ),
        )
    except (TcoleImportError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(result), 200


@api.post(
    "/agencies/<uuid:agency_id>/imports/tcole/"
    "<uuid:import_job_id>/licensee-search"
)
def import_tcole_licensee_search_stage(
    agency_id,
    import_job_id,
):
    uploaded_file = request.files.get("file")

    if uploaded_file is None:
        return jsonify({"error": "file is required."}), 400

    try:
        result = run_tcole_licensee_search_stage(
            agency_id=agency_id,
            import_job_id=import_job_id,
            licensee_search_content=uploaded_file.read(),
            licensee_search_filename=(
                uploaded_file.filename
                or "rptDepartmentOfficerSearch.csv"
            ),
        )
    except (TcoleImportError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(result), 200


@api.post("/agencies/<uuid:agency_id>/imports/tcole")
def import_tcole_records(agency_id):
    awards_file = request.files.get("awards_file")
    courses_file = request.files.get("courses_file")
    cycle_file = request.files.get("cycle_file")
    licensee_search_file = request.files.get(
        "licensee_search_file"
    )

    if (
        awards_file is None
        or courses_file is None
        or cycle_file is None
        or licensee_search_file is None
    ):
        return (
            jsonify(
                {
                    "error": (
                        "awards_file, courses_file, "
                        "cycle_file, and "
                        "licensee_search_file are required."
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
            licensee_search_content=(
                licensee_search_file.read()
            ),
            awards_filename=awards_file.filename or "rptAwards.csv",
            courses_filename=(
                courses_file.filename or "rptCourseTaken.csv"
            ),
            cycle_filename=(
                cycle_file.filename
                or "rptCycleT_All.csv"
            ),
            licensee_search_filename=(
                licensee_search_file.filename
                or "rptDepartmentOfficerSearch.csv"
            ),
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


@api.get(
    "/agencies/<uuid:agency_id>"
    "/reports/compliance.pdf"
)
def agency_compliance_report_pdf(agency_id):
    agency = Agency.query.filter_by(
        id=agency_id,
    ).one_or_none()

    if agency is None:
        return jsonify(
            {
                "error": "Agency not found."
            }
        ), 404

    report = evaluate_agency_compliance_report(
        agency_id,
        evaluation_date=date.today(),
    )

    if report is None:
        return jsonify(
            {
                "error":
                    "Compliance report could not be generated."
            }
        ), 404

    pdf_bytes = render_agency_compliance_pdf(
        report
    )

    filename_base = "".join(
        character
        if (
            character.isalnum()
            or character in {"-", "_"}
        )
        else "-"
        for character in agency.name.strip()
    )

    while "--" in filename_base:
        filename_base = filename_base.replace(
            "--",
            "-",
        )

    filename_base = filename_base.strip("-")

    if not filename_base:
        filename_base = "agency"

    filename = (
        f"{filename_base}-"
        "compliance-report.pdf"
    )

    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


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


@api.patch(
    "/agencies/<uuid:agency_id>"
    "/officers/<uuid:officer_id>"
    "/license-tracking/<license_type>"
)
def update_officer_license_tracking(
    agency_id,
    officer_id,
    license_type,
):
    payload = request.get_json(
        silent=True
    ) or {}

    user = g.current_user

    changed_by = " ".join(
        part
        for part in [
            getattr(user, "first_name", None),
            getattr(user, "last_name", None),
        ]
        if part
    ).strip()

    if not changed_by:
        changed_by = getattr(
            user,
            "email",
            None,
        )

    try:
        result = set_license_tracking(
            agency_id=agency_id,
            officer_id=officer_id,
            license_type=license_type,
            tracking_enabled=payload.get(
                "tracking_enabled"
            ),
            changed_by=changed_by,
            reason=payload.get("reason"),
        )
    except LicenseTrackingError as exc:
        return jsonify(
            {"error": str(exc)}
        ), 400

    return jsonify(
        {"license_tracking": result}
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
            inactive_date=payload.get(
                "inactive_date"
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


@api.get(
    "/agencies/<uuid:agency_id>"
    "/officers/<uuid:officer_id>"
    "/compliance/public-information-officer"
)
def public_information_officer_compliance(
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

    result = evaluate_public_information_officer(
        officer
    )

    return jsonify(result), 200


@api.get("/credential-types")
def credential_types():
    return jsonify(
        [
            {
                "credential_type": key,
                "credential_name": value,
            }
            for key, value
            in CREDENTIAL_TYPES.items()
        ]
    ), 200


@api.get(
    "/agencies/<uuid:agency_id>"
    "/officers/<uuid:officer_id>"
    "/credential-verifications"
)
def officer_credential_verifications(
    agency_id,
    officer_id,
):
    try:
        result = list_verifications(
            agency_id,
            officer_id,
        )
    except CredentialVerificationError as exc:
        return jsonify(
            {"error": str(exc)}
        ), 404

    return jsonify(result), 200


@api.post(
    "/agencies/<uuid:agency_id>"
    "/officers/<uuid:officer_id>"
    "/credential-verifications/<credential_type>"
)
def create_credential_verification(
    agency_id,
    officer_id,
    credential_type,
):
    payload = request.get_json(
        silent=True
    ) or {}

    try:
        result = verify_credential(
            agency_id=agency_id,
            officer_id=officer_id,
            credential_type=credential_type,
            effective_date=payload.get(
                "effective_date"
            ),
            verified_by=payload.get(
                "verified_by"
            ),
            reference=payload.get(
                "reference"
            ),
            notes=payload.get(
                "notes"
            ),
        )
    except CredentialVerificationError as exc:
        return jsonify(
            {"error": str(exc)}
        ), 400

    return jsonify(result), 201


@api.patch(
    "/agencies/<uuid:agency_id>"
    "/officers/<uuid:officer_id>"
    "/credential-verifications/<credential_type>/revoke"
)
def revoke_officer_credential_verification(
    agency_id,
    officer_id,
    credential_type,
):
    try:
        result = revoke_verification(
            agency_id,
            officer_id,
            credential_type,
        )
    except CredentialVerificationError as exc:
        return jsonify(
            {"error": str(exc)}
        ), 400

    return jsonify(result), 200


@api.get(
    "/agencies/<uuid:agency_id>"
    "/officers/<uuid:officer_id>"
    "/compliance/supervisor"
)
def supervisor_compliance(
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

    result = evaluate_supervisor(
        officer
    )

    return jsonify(result), 200


@api.get(
    "/agencies/<uuid:agency_id>"
    "/officers/<uuid:officer_id>"
    "/qualification-facts"
)
def officer_qualification_facts(
    agency_id,
    officer_id,
):
    result = get_qualification_facts(
        agency_id,
        officer_id,
    )

    if result is None:
        return jsonify(
            {"error": "Officer not found."}
        ), 404

    return jsonify(result), 200


@api.patch(
    "/agencies/<uuid:agency_id>"
    "/officers/<uuid:officer_id>"
    "/qualification-facts"
)
def update_officer_qualification_facts(
    agency_id,
    officer_id,
):
    payload = request.get_json(silent=True) or {}

    try:
        result = update_qualification_facts(
            agency_id,
            officer_id,
            verified_education_level=payload.get(
                "verified_education_level"
            ),
            verified_college_credit_hours=payload.get(
                "verified_college_credit_hours"
            ),
            verified_military_training_credit_hours=(
                payload.get(
                    "verified_military_training_credit_hours"
                )
            ),
            verified_military_months=payload.get(
                "verified_military_months"
            ),
            education_supplied=(
                "verified_education_level" in payload
            ),
            college_hours_supplied=(
                "verified_college_credit_hours" in payload
            ),
            military_training_credit_supplied=(
                "verified_military_training_credit_hours"
                in payload
            ),
            military_supplied=(
                "verified_military_months" in payload
            ),
            verified_jailer_cultural_diversity_exemption=(
                payload.get(
                    "verified_jailer_cultural_diversity_exemption"
                )
            ),
            jailer_exemption_supplied=(
                "verified_jailer_cultural_diversity_exemption"
                in payload
            ),
        )
    except QualificationFactsError as exc:
        return jsonify(
            {"error": str(exc)}
        ), 400

    if result is None:
        return jsonify(
            {"error": "Officer not found."}
        ), 404

    return jsonify(result), 200


@api.post(
    "/agencies/<uuid:agency_id>"
    "/officers/<uuid:officer_id>"
    "/archive"
)
def archive_agency_employee(
    agency_id,
    officer_id,
):
    payload = request.get_json(
        silent=True
    ) or {}

    try:
        result = archive_employee(
            agency_id,
            officer_id,
            reason=payload.get("reason"),
        )
    except EmployeeLifecycleError as exc:
        return jsonify(
            {
                "error": str(exc),
            }
        ), 400

    if result is None:
        return jsonify(
            {
                "error": "Resource not found.",
            }
        ), 404

    return jsonify(result), 200


@api.post(
    "/agencies/<uuid:agency_id>"
    "/officers/<uuid:officer_id>"
    "/restore"
)
def restore_agency_employee(
    agency_id,
    officer_id,
):
    try:
        result = restore_employee(
            agency_id,
            officer_id,
        )
    except EmployeeLifecycleError as exc:
        return jsonify(
            {
                "error": str(exc),
            }
        ), 400

    if result is None:
        return jsonify(
            {
                "error": "Resource not found.",
            }
        ), 404

    return jsonify(result), 200


@api.get(
    "/agencies/<uuid:agency_id>"
    "/officers/<uuid:officer_id>"
    "/workspace"
)
def employee_workspace(
    agency_id,
    officer_id,
):
    result = get_employee_workspace(
        agency_id,
        officer_id,
    )

    if result is None:
        return jsonify(
            {"error": "Officer not found."}
        ), 404

    return jsonify(result), 200


@api.get(
    "/agencies/<uuid:agency_id>"
    "/officers/<uuid:officer_id>"
    "/compliance-email"
)
def officer_compliance_email(
    agency_id,
    officer_id,
):
    track = request.args.get(
        "track",
        "peace_officer",
    )

    supported_tracks = {
        "peace_officer",
        "jailer",
        "telecommunicator",
        "combined",
    }

    if track not in supported_tracks:
        return jsonify(
            {
                "error": (
                    "Invalid compliance email track. "
                    "Supported tracks are peace_officer, "
                    "jailer, telecommunicator, and combined."
                )
            }
        ), 400

    result = get_compliance_email(
        agency_id,
        officer_id,
        track=track,
    )

    if result is None:
        return jsonify(
            {"error": "Officer not found."}
        ), 404

    return jsonify(result), 200


@api.get(
    "/agencies/<uuid:agency_id>"
    "/officers/<uuid:officer_id>"
    "/compliance/profile"
)
def officer_compliance_profile(
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

    result = evaluate_officer_compliance_profile(
        officer
    )

    return jsonify(result), 200


@api.get(
    "/agencies/<uuid:agency_id>"
    "/compliance/dashboard"
)
def agency_compliance_dashboard(
    agency_id,
):
    result = evaluate_agency_compliance_dashboard(
        agency_id
    )

    if result is None:
        return jsonify(
            {"error": "Agency not found."}
        ), 404

    return jsonify(result), 200


@api.get(
    "/agencies/<uuid:agency_id>"
    "/compliance/communications/preflight"
)
def bulk_compliance_communications_preflight(
    agency_id,
):
    evaluation_date_value = request.args.get(
        "evaluation_date"
    )

    evaluation_date = None

    if evaluation_date_value:
        try:
            evaluation_date = date.fromisoformat(
                evaluation_date_value
            )
        except ValueError:
            return jsonify(
                {
                    "error": (
                        "evaluation_date must use "
                        "YYYY-MM-DD format."
                    )
                }
            ), 400

    result = build_bulk_compliance_preflight(
        agency_id,
        evaluation_date=evaluation_date,
    )

    if result is None:
        return jsonify(
            {"error": "Agency not found."}
        ), 404

    return jsonify(result), 200


@api.patch(
    "/agencies/<uuid:agency_id>/email-configuration"
)
def update_agency_email_configuration(agency_id):
    payload = request.get_json(silent=True) or {}

    agency = db.session.get(Agency, agency_id)

    if agency is None:
        return jsonify(
            {"error": "Agency not found."}
        ), 404

    supported_patterns = {
        "FIRST_INITIAL_LAST",
        "FIRST_DOT_LAST",
        "FIRST_LAST",
        "LAST_FIRST_INITIAL",
    }

    email_domain = payload.get("email_domain")
    email_pattern = payload.get("email_pattern")

    if email_domain is not None:
        email_domain = email_domain.strip().lower()

        if email_domain.startswith("@"):
            email_domain = email_domain[1:]

        if not email_domain:
            email_domain = None

        elif (
            "@" in email_domain
            or " " in email_domain
            or "." not in email_domain
        ):
            return jsonify(
                {
                    "error":
                        "Enter a valid email domain."
                }
            ), 400

    if email_pattern is not None:
        email_pattern = email_pattern.strip()

        if not email_pattern:
            email_pattern = None

        elif email_pattern not in supported_patterns:
            return jsonify(
                {
                    "error":
                        "Unsupported email pattern."
                }
            ), 400

    agency.email_domain = email_domain
    agency.email_pattern = email_pattern

    db.session.commit()

    return jsonify(
        {
            "agency_id": str(agency.id),
            "email_domain": agency.email_domain,
            "email_pattern": agency.email_pattern,
        }
    ), 200


@api.patch(
    "/agencies/<uuid:agency_id>"
    "/officers/<uuid:officer_id>/email"
)
def update_officer_email(agency_id, officer_id):
    payload = request.get_json(silent=True) or {}

    officer = Officer.query.filter_by(
        id=officer_id,
        agency_id=agency_id,
    ).one_or_none()

    if officer is None:
        return jsonify(
            {"error": "Officer not found."}
        ), 404

    email_override = payload.get("email_override")

    if email_override is not None:
        email_override = email_override.strip()

        if not email_override:
            email_override = None

        elif (
            "@" not in email_override
            or email_override.startswith("@")
            or email_override.endswith("@")
            or " " in email_override
        ):
            return jsonify(
                {
                    "error":
                        "Enter a valid email address."
                }
            ), 400

    officer.email_override = email_override
    db.session.commit()

    from app.compliance.email_resolver import (
        resolve_officer_email,
    )

    return jsonify(
        {
            "officer_id": str(officer.id),
            "email_override":
                officer.email_override,
            "resolved_email":
                resolve_officer_email(officer),
        }
    ), 200
