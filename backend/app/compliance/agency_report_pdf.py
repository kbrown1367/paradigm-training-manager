# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.
#
# Paradigm Training Manager™ is proprietary and confidential software.
# Unauthorized copying, modification, distribution, or use is prohibited.
# Software ID: PTM-PSP-2026

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.software_identity import (
    get_copyright_notice,
    get_version,
)


NAVY = colors.HexColor("#172033")
TEAL = colors.HexColor("#267A78")
COPPER = colors.HexColor("#B8794A")
TEXT = colors.HexColor("#344054")
MUTED = colors.HexColor("#667085")
BORDER = colors.HexColor("#D0D5DD")
LIGHT = colors.HexColor("#F9FAFB")
DUE_BG = colors.HexColor("#FFF7E8")
OVERDUE_BG = colors.HexColor("#FDECEC")
REVIEW_BG = colors.HexColor("#FFF5E5")
SUCCESS_BG = colors.HexColor("#ECFDF3")


def _get_logo_path():
    project_root = (
        Path(__file__).resolve().parents[3]
    )

    logo_path = (
        project_root
        / "frontend"
        / "public"
        / "ptm-logo.png"
    )

    if not logo_path.exists():
        return None

    return logo_path


def _report_brand_header(
    report,
    styles,
):
    logo_path = _get_logo_path()

    title_block = [
        Paragraph(
            "Paradigm Training Manager™",
            styles["small"],
        ),
        Paragraph(
            "Agency Compliance Report",
            styles["title"],
        ),
        Paragraph(
            report["agency"]["name"],
            styles["agency"],
        ),
    ]

    if logo_path is None:
        return title_block

    logo = Image(
        str(logo_path),
        width=0.58 * inch,
        height=0.58 * inch,
    )

    title_content = [
        Paragraph(
            "Paradigm Training Manager™",
            styles["small"],
        ),
        Paragraph(
            "Agency Compliance Report",
            styles["title"],
        ),
        Paragraph(
            report["agency"]["name"],
            styles["agency"],
        ),
    ]

    table = Table(
        [
            [
                logo,
                title_content,
            ]
        ],
        colWidths=[
            0.72 * inch,
            6.0 * inch,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
            ]
        )
    )

    return [table]


def _format_date(value):
    if not value:
        return "Not specified"

    year, month, day = value.split("-")

    months = {
        "01": "January",
        "02": "February",
        "03": "March",
        "04": "April",
        "05": "May",
        "06": "June",
        "07": "July",
        "08": "August",
        "09": "September",
        "10": "October",
        "11": "November",
        "12": "December",
    }

    return (
        f"{months[month]} {int(day)}, {year}"
    )


def _employee_name(employee):
    return (
        f"{employee['last_name']}, "
        f"{employee['first_name']}"
    )


def _course_text(course_numbers):
    if not course_numbers:
        return ""

    return " / ".join(
        f"#{number}"
        for number in course_numbers
    )


def _status_label(status):
    labels = {
        "NONCOMPLIANT": "NONCOMPLIANT",
        "OVERDUE": "OVERDUE",
        "PENDING_REVIEW": "AGENCY REVIEW",
        "OUTSTANDING": "OUTSTANDING",
        "DUE": "DUE",
    }

    return labels.get(status, status or "")


def _build_styles():
    sample = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "PTMTitle",
            parent=sample["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=23,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=4,
        ),
        "agency": ParagraphStyle(
            "PTMAgency",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            textColor=TEAL,
            spaceAfter=10,
        ),
        "section": ParagraphStyle(
            "PTMSection",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=NAVY,
            spaceBefore=8,
            spaceAfter=8,
        ),
        "subsection": ParagraphStyle(
            "PTMSubsection",
            parent=sample["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=NAVY,
            spaceBefore=4,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "PTMBody",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=TEXT,
        ),
        "small": ParagraphStyle(
            "PTMSmall",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=MUTED,
        ),
        "tiny": ParagraphStyle(
            "PTMTiny",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=8,
            textColor=MUTED,
        ),
        "table_header": ParagraphStyle(
            "PTMTableHeader",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9,
            textColor=colors.white,
            alignment=TA_LEFT,
        ),
        "table": ParagraphStyle(
            "PTMTable",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=TEXT,
        ),
        "table_bold": ParagraphStyle(
            "PTMTableBold",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=TEXT,
        ),
        "center": ParagraphStyle(
            "PTMCenter",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=TEXT,
            alignment=TA_CENTER,
        ),
    }


def _draw_page(canvas, doc):
    canvas.saveState()

    width, height = letter

    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)

    canvas.line(
        doc.leftMargin,
        0.58 * inch,
        width - doc.rightMargin,
        0.58 * inch,
    )

    canvas.setFont(
        "Helvetica",
        6.5,
    )
    canvas.setFillColor(MUTED)

    canvas.drawString(
        doc.leftMargin,
        0.38 * inch,
        (
            "Paradigm Training Manager™ | "
            f"v{get_version()}"
        ),
    )

    canvas.drawRightString(
        width - doc.rightMargin,
        0.38 * inch,
        f"Page {doc.page}",
    )

    canvas.restoreState()


def _summary_table(report, styles):
    summary = report["executive_summary"]

    data = [
        [
            Paragraph(
                "Active Employees",
                styles["table_header"],
            ),
            Paragraph(
                "Compliant",
                styles["table_header"],
            ),
            Paragraph(
                "Due",
                styles["table_header"],
            ),
            Paragraph(
                "Noncompliant",
                styles["table_header"],
            ),
            Paragraph(
                "Agency Review",
                styles["table_header"],
            ),
        ],
        [
            Paragraph(
                str(
                    summary[
                        "active_employee_count"
                    ]
                ),
                styles["center"],
            ),
            Paragraph(
                str(
                    summary[
                        "compliant_count"
                    ]
                ),
                styles["center"],
            ),
            Paragraph(
                str(summary["due_count"]),
                styles["center"],
            ),
            Paragraph(
                str(
                    summary[
                        "noncompliant_count"
                    ]
                ),
                styles["center"],
            ),
            Paragraph(
                str(
                    summary[
                        "agency_review_required_count"
                    ]
                ),
                styles["center"],
            ),
        ],
    ]

    table = Table(
        data,
        colWidths=[
            1.25 * inch,
            1.1 * inch,
            0.9 * inch,
            1.15 * inch,
            1.25 * inch,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    NAVY,
                ),
                (
                    "BACKGROUND",
                    (0, 1),
                    (-1, 1),
                    LIGHT,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    BORDER,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    return table


def _training_plan_table(report, styles):
    data = [
        [
            Paragraph(
                "Requirement",
                styles["table_header"],
            ),
            Paragraph(
                "Track",
                styles["table_header"],
            ),
            Paragraph(
                "Employees",
                styles["table_header"],
            ),
            Paragraph(
                "Due",
                styles["table_header"],
            ),
            Paragraph(
                "Courses",
                styles["table_header"],
            ),
        ]
    ]

    for item in report["training_plan"]:
        data.append(
            [
                Paragraph(
                    item["display_name"],
                    styles["table_bold"],
                ),
                Paragraph(
                    (
                        item["source_component"]
                        or ""
                    )
                    .replace("_", " ")
                    .title(),
                    styles["table"],
                ),
                Paragraph(
                    str(
                        item["employee_count"]
                    ),
                    styles["center"],
                ),
                Paragraph(
                    _format_date(
                        item["due_date"]
                    ),
                    styles["table"],
                ),
                Paragraph(
                    _course_text(
                        item["course_numbers"]
                    )
                    or "N/A",
                    styles["table"],
                ),
            ]
        )

    table = Table(
        data,
        repeatRows=1,
        colWidths=[
            2.12 * inch,
            1.2 * inch,
            0.65 * inch,
            1.15 * inch,
            1.35 * inch,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    NAVY,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    BORDER,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    for row in range(
        1,
        len(data),
    ):
        if row % 2 == 0:
            table.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, row),
                            (-1, row),
                            LIGHT,
                        )
                    ]
                )
            )

    return table


def _employee_block(employee, styles):
    heading = (
        f"{_employee_name(employee)}"
        f" &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"PID {employee['tcole_pid']}"
    )

    certificate = (
        employee.get("highest_certificate")
        or "Certificate not reported"
    )

    elements = [
        Paragraph(
            heading,
            styles["subsection"],
        ),
        Paragraph(
            (
                f"<b>Status:</b> "
                f"{_status_label(employee['overall_status'])}"
                f" &nbsp;&nbsp; "
                f"<b>Certificate:</b> {certificate}"
                f" &nbsp;&nbsp; "
                f"<b>Next Due:</b> "
                f"{_format_date(employee['next_due_date'])}"
            ),
            styles["small"],
        ),
        Spacer(1, 4),
    ]

    data = [
        [
            Paragraph(
                "Requirement",
                styles["table_header"],
            ),
            Paragraph(
                "Track",
                styles["table_header"],
            ),
            Paragraph(
                "Due",
                styles["table_header"],
            ),
            Paragraph(
                "Courses",
                styles["table_header"],
            ),
        ]
    ]

    for requirement in employee["requirements"]:
        data.append(
            [
                Paragraph(
                    requirement[
                        "display_name"
                    ],
                    styles["table_bold"],
                ),
                Paragraph(
                    (
                        requirement[
                            "source_component"
                        ]
                        or ""
                    )
                    .replace("_", " ")
                    .title(),
                    styles["table"],
                ),
                Paragraph(
                    _format_date(
                        requirement[
                            "due_date"
                        ]
                    ),
                    styles["table"],
                ),
                Paragraph(
                    _course_text(
                        requirement[
                            "course_numbers"
                        ]
                    )
                    or "N/A",
                    styles["table"],
                ),
            ]
        )

    table = Table(
        data,
        repeatRows=1,
        colWidths=[
            2.6 * inch,
            1.45 * inch,
            1.25 * inch,
            1.55 * inch,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    TEAL,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    BORDER,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    elements.extend(
        [
            table,
            Spacer(1, 10),
        ]
    )

    return KeepTogether(elements)


def _proficiency_table(report, styles):
    data = [
        [
            Paragraph(
                "Employee",
                styles["table_header"],
            ),
            Paragraph(
                "Track",
                styles["table_header"],
            ),
            Paragraph(
                "Current",
                styles["table_header"],
            ),
            Paragraph(
                "Eligible For",
                styles["table_header"],
            ),
        ]
    ]

    for item in report[
        "proficiency_opportunities"
    ]:
        data.append(
            [
                Paragraph(
                    (
                        f"{item['last_name']}, "
                        f"{item['first_name']}"
                    ),
                    styles["table_bold"],
                ),
                Paragraph(
                    item["track_label"],
                    styles["table"],
                ),
                Paragraph(
                    (
                        item[
                            "current_certificate"
                        ]
                        or "None"
                    ),
                    styles["table"],
                ),
                Paragraph(
                    item[
                        "next_certificate"
                    ],
                    styles["table_bold"],
                ),
            ]
        )

    table = Table(
        data,
        repeatRows=1,
        colWidths=[
            1.75 * inch,
            1.2 * inch,
            1.8 * inch,
            2.1 * inch,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    COPPER,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    BORDER,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    return table


def render_agency_compliance_pdf(report):
    buffer = BytesIO()

    styles = _build_styles()

    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.75 * inch,
        title=report["report"]["title"],
        author="Paradigm Strategic Partners, LLC",
        subject="Agency TCOLE Compliance Report",
    )

    story = []

    story.extend(
        _report_brand_header(
            report,
            styles,
        )
    )

    story.append(
        Paragraph(
            (
                f"<b>Generated As Of:</b> "
                f"{_format_date(report['report']['evaluation_date'])}"
                f"<br/>"
                f"<b>Training Unit "
                f"{report['training_unit']['number']}:</b> "
                f"{_format_date(report['training_unit']['start'])} "
                f"through "
                f"{_format_date(report['training_unit']['end'])}"
                f"<br/>"
                f"<b>Training Cycle:</b> "
                f"{_format_date(report['training_cycle']['start'])} "
                f"through "
                f"{_format_date(report['training_cycle']['end'])}"
            ),
            styles["body"],
        )
    )

    story.append(
        Spacer(1, 12)
    )

    story.append(
        Paragraph(
            "Executive Compliance Summary",
            styles["section"],
        )
    )

    story.append(
        _summary_table(
            report,
            styles,
        )
    )

    story.append(
        Spacer(1, 7)
    )

    story.append(
        Paragraph(
            (
                "<b>Important:</b> Employees listed as "
                "<b>Due</b> have one or more requirements "
                "that remain outstanding but have not yet "
                "passed their applicable deadline. "
                "Due does not mean the employee is currently "
                "noncompliant."
            ),
            styles["small"],
        )
    )

    story.append(
        Spacer(1, 12)
    )

    story.append(
        Paragraph(
            "Training Planning Summary",
            styles["section"],
        )
    )

    story.append(
        Paragraph(
            (
                "This section groups outstanding requirements "
                "by training need so the agency can quickly "
                "identify how many employees require each "
                "course or training category."
            ),
            styles["small"],
        )
    )

    story.append(
        Spacer(1, 6)
    )

    story.append(
        _training_plan_table(
            report,
            styles,
        )
    )

    story.append(
        PageBreak()
    )

    story.append(
        Paragraph(
            "Employees Requiring Attention",
            styles["section"],
        )
    )

    story.append(
        Paragraph(
            (
                "Only employees with an outstanding, overdue, "
                "or agency-review finding are listed in this "
                "section."
            ),
            styles["small"],
        )
    )

    story.append(
        Spacer(1, 8)
    )

    if report["employee_findings"]:
        for employee in report[
            "employee_findings"
        ]:
            story.append(
                _employee_block(
                    employee,
                    styles,
                )
            )
    else:
        story.append(
            Paragraph(
                (
                    "No employees have reportable "
                    "compliance findings."
                ),
                styles["body"],
            )
        )

    story.append(
        PageBreak()
    )

    story.append(
        Paragraph(
            "Certification Advancement Opportunities",
            styles["section"],
        )
    )

    story.append(
        Paragraph(
            (
                "This section is informational. These items "
                "are certification advancement opportunities "
                "and are not compliance deficiencies."
            ),
            styles["small"],
        )
    )

    story.append(
        Spacer(1, 8)
    )

    if report[
        "proficiency_opportunities"
    ]:
        story.append(
            _proficiency_table(
                report,
                styles,
            )
        )
    else:
        story.append(
            Paragraph(
                (
                    "No employees are currently identified "
                    "as eligible for a higher proficiency "
                    "certificate."
                ),
                styles["body"],
            )
        )

    story.append(
        Spacer(1, 18)
    )

    story.append(
        Paragraph(
            "Data Source and Use Notice",
            styles["section"],
        )
    )

    story.append(
        Paragraph(
            (
                "This report is generated from TCOLE data "
                "imported by the agency and compliance rules "
                "maintained by Paradigm Training Manager. "
                "It is intended as an administrative "
                "compliance-management tool and does not "
                "replace official TCOLE records or "
                "determinations. Agencies should verify "
                "matters requiring an official certification "
                "or regulatory determination with TCOLE."
            ),
            styles["body"],
        )
    )

    story.append(
        Spacer(1, 10)
    )

    story.append(
        Paragraph(
            (
                f"Generated using Paradigm Training Manager™ "
                f"v{get_version()}. "
                f"{get_copyright_notice()}"
            ),
            styles["tiny"],
        )
    )

    document.build(
        story,
        onFirstPage=_draw_page,
        onLaterPages=_draw_page,
    )

    buffer.seek(0)

    return buffer.getvalue()
