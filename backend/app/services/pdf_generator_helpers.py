from typing import List
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from ..models.schemas import OverviewData
import html

def sanitize_pdf_text(text: str) -> str:
    if not text:
        return ""
    t = text.replace("\u2013", "–").replace("\u2014", "—").replace("\u2018", "'").replace("\u2019", "'")
    return html.escape(t).replace("\n", "<br/>")

def build_overview_table_flowables(overview: OverviewData, printable_width: float, styles: dict) -> List:
    elements = []
    
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("<b>QUESTION PAPER OVERVIEW & ANALYSIS</b>", styles["WorksheetSectionTitle"]))
    elements.append(Spacer(1, 4))

    match_status = "MATCHED" if overview.marks_match else "VERIFY"
    match_color = "#166534" if overview.marks_match else "#b91c1c"

    summary_data = [
        [
            Paragraph("<b>Total Questions:</b>", styles["MetaText"]),
            Paragraph(str(overview.total_questions_count), styles["MetaText"]),
            Paragraph("<b>Total Sections:</b>", styles["MetaText"]),
            Paragraph(str(overview.total_sections_count), styles["MetaText"])
        ],
        [
            Paragraph("<b>Calculated Student Marks:</b>", styles["MetaText"]),
            Paragraph(f"<b>{overview.calculated_student_marks}</b>", styles["MetaText"]),
            Paragraph("<b>Configured Maximum Marks:</b>", styles["MetaText"]),
            Paragraph(f"<b>{overview.configured_max_marks or '-'}</b>", styles["MetaText"])
        ],
        [
            Paragraph("<b>Sum of All Questions:</b>", styles["MetaText"]),
            Paragraph(f"{overview.total_marks_sum}", styles["MetaText"]),
            Paragraph("<b>Status:</b>", styles["MetaText"]),
            Paragraph(f"<font color='{match_color}'><b>{match_status}</b></font>", styles["MetaText"])
        ]
    ]

    c_w = printable_width / 4.0
    sum_table = Table(summary_data, colWidths=[c_w, c_w, c_w, c_w])
    sum_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#94a3b8")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(sum_table)
    elements.append(Spacer(1, 8))

    # Section breakdown table
    elements.append(Paragraph("<b>Section-Wise Breakdown:</b>", styles["SubHeader"]))
    elements.append(Spacer(1, 3))

    sec_table_data = [
        ["Section", "Questions", "Total Available Marks", "Required / Student Marks", "Instructions"]
    ]

    for s in overview.section_summaries:
        sec_table_data.append([
            Paragraph(f"<b>{sanitize_pdf_text(s.section_title)}</b>", styles["MetaText"]),
            Paragraph(str(s.question_count), styles["MetaText"]),
            Paragraph(f"{s.total_marks_available:g}", styles["MetaText"]),
            Paragraph(f"{s.expected_marks:g}" if s.expected_marks is not None else "-", styles["MetaText"]),
            Paragraph(sanitize_pdf_text(s.instructions or "Answer all"), styles["MetaText"])
        ])

    w_sec = [printable_width * 0.20, printable_width * 0.12, printable_width * 0.18, printable_width * 0.20, printable_width * 0.30]
    sec_breakdown_table = Table(sec_table_data, colWidths=w_sec)
    sec_breakdown_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 5),
        ('TOPPADDING', (0,0), (-1,0), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('TOPPADDING', (0,1), (-1,-1), 4),
        ('BOTTOMPADDING', (0,1), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(sec_breakdown_table)

    if overview.validation_issues:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("<b>Detected Formatting & Structure Issues:</b>", styles["SubHeader"]))
        elements.append(Spacer(1, 3))
        for issue in overview.validation_issues:
            color = "#b91c1c" if issue.severity == "error" else "#b45309" if issue.severity == "warning" else "#2563eb"
            loc = f"[{issue.location}] " if issue.location else ""
            msg = f"<font color='{color}'>●</font> <b>{loc}</b>{sanitize_pdf_text(issue.message)}"
            elements.append(Paragraph(msg, styles["InstrBody"]))

    return elements
