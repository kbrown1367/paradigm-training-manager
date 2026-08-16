from app.compliance.agency_report_pdf import (
    render_agency_compliance_pdf,
)


def make_report():
    return {
        "report": {
            "title": "Agency Compliance Report",
            "product":
                "Paradigm Training Manager™",
            "evaluation_date":
                "2026-08-16",
        },
        "agency": {
            "id": "agency-1",
            "name": "Example Police Department",
        },
        "training_cycle": {
            "start": "2025-09-01",
            "end": "2029-08-31",
        },
        "training_unit": {
            "number": 1,
            "start": "2025-09-01",
            "end": "2027-08-31",
        },
        "executive_summary": {
            "active_employee_count": 5,
            "compliant_count": 2,
            "due_count": 3,
            "noncompliant_count": 0,
            "pending_review_count": 0,
            "not_evaluated_count": 0,
            "agency_review_required_count": 1,
        },
        "training_plan": [
            {
                "display_name":
                    "State and Federal Law Update",
                "source_component":
                    "PEACE_OFFICER",
                "employee_count": 3,
                "due_date":
                    "2027-08-31",
                "course_numbers":
                    ["3189"],
                "overdue_count": 0,
                "outstanding_count": 3,
                "pending_review_count": 0,
            }
        ],
        "employee_findings": [
            {
                "tcole_pid": "123456",
                "first_name": "JANE",
                "last_name": "SMITH",
                "overall_status": "DUE",
                "highest_certificate":
                    "Intermediate Peace Officer",
                "next_due_date":
                    "2027-08-31",
                "requirements": [
                    {
                        "display_name":
                            "State and Federal Law Update",
                        "source_component":
                            "PEACE_OFFICER",
                        "status":
                            "OUTSTANDING",
                        "due_date":
                            "2027-08-31",
                        "course_numbers":
                            ["3189"],
                    }
                ],
            }
        ],
        "proficiency_opportunities": [
            {
                "tcole_pid": "654321",
                "first_name": "JOHN",
                "last_name": "DOE",
                "track_label":
                    "Peace Officer",
                "current_certificate":
                    "Basic Peace Officer",
                "next_certificate":
                    "Intermediate Peace Officer",
                "status": "ELIGIBLE",
            }
        ],
    }


def test_render_report_returns_pdf_bytes():
    pdf = render_agency_compliance_pdf(
        make_report()
    )

    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_render_report_contains_multiple_pages():
    report = make_report()

    report["employee_findings"] = (
        report["employee_findings"] * 30
    )

    pdf = render_agency_compliance_pdf(
        report
    )

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 2000
