import os
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import html

from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Image as RLImage
)
from reportlab.pdfgen import canvas

from ..models.schemas import (
    Section, Question, PaperConfig, ReferenceAnalysis,
    AnswerKeyItem, TeacherAnswerKeySummary
)
from ..db.question_bank_db import QuestionBankRepository
from ..utils.file_utils import TEMP_BASE_DIR, cleanup_file
from .pdf_generator import NumberedBorderCanvas, sanitize_pdf_text, PAGE_SIZES


def extract_teacher_answer_metadata(sections: List[Section]) -> Tuple[List[AnswerKeyItem], TeacherAnswerKeySummary]:
    """
    Extracts structured answer key metadata for all questions in the paper sections.
    Reconciles with the Question Bank where bank_question_id is present.
    Strictly avoids fabricating or inventing answers when none exist.
    """
    items: List[AnswerKeyItem] = []
    
    # Collect bank IDs to query bank in batch
    bank_ids = [q.bank_question_id for sec in sections for q in sec.questions if q.bank_question_id]
    bank_records = {b["id"]: b for b in QuestionBankRepository.get_by_ids(bank_ids)} if bank_ids else {}

    total_questions = 0
    total_marks = 0.0
    questions_with_answers = 0
    questions_missing_answers = 0
    questions_with_rubrics = 0
    inconsistencies = []

    for sec in sections:
        sec_title = sec.title or "General"
        for q in sec.questions:
            total_questions += 1
            q_marks = float(q.marks or 1.0)
            total_marks += q_marks

            # Resolve from bank record if available, fallback to snapshot
            bank_rec = bank_records.get(q.bank_question_id) if q.bank_question_id else None

            # 1. Correct answer
            ans = ""
            if bank_rec and bank_rec.get("correct_answer"):
                ans = bank_rec["correct_answer"].strip()
            elif q.correct_answer:
                ans = q.correct_answer.strip()

            # 2. Explanation
            expl = ""
            if bank_rec and bank_rec.get("explanation"):
                expl = bank_rec["explanation"].strip()
            elif q.explanation:
                expl = q.explanation.strip()

            # 3. Rubric
            rub = ""
            if bank_rec and bank_rec.get("rubric"):
                rub = bank_rec["rubric"].strip()
            elif q.rubric:
                rub = q.rubric.strip()

            # 4. Alternative answers
            alts = []
            if bank_rec and bank_rec.get("alternative_answers"):
                alts = list(bank_rec["alternative_answers"])
            elif q.alternative_answers:
                alts = list(q.alternative_answers)

            # 5. Key points
            kps = []
            if bank_rec and bank_rec.get("key_points"):
                kps = list(bank_rec["key_points"])
            elif q.key_points:
                kps = list(q.key_points)

            # 6. Matching answers
            m_answers = None
            if bank_rec and bank_rec.get("matching_answers"):
                m_answers = dict(bank_rec["matching_answers"])
            elif q.matching_answers:
                m_answers = dict(q.matching_answers)

            # If matching question has left and right items, build pair mapping
            matching_pairs = {}
            if q.matching_left and q.matching_right:
                if m_answers:
                    # m_answers could be {"A": "2", "B": "1"} or direct index
                    for l_idx, l_text in enumerate(q.matching_left):
                        l_key = chr(65 + l_idx) # 'A', 'B', etc.
                        target_r_key = m_answers.get(l_key, m_answers.get(str(l_idx + 1), ""))
                        # Find corresponding right text
                        matched_r_text = ""
                        for r_text in q.matching_right:
                            if target_r_key and (r_text.startswith(str(target_r_key)) or target_r_key in r_text):
                                matched_r_text = r_text
                                break
                        matching_pairs[l_text] = matched_r_text or (f"Option {target_r_key}" if target_r_key else "Not mapped")
                else:
                    # In standard matching without shuffle, Column A[i] corresponds to original Column B[i] if recorded
                    for l_text, r_text in zip(q.matching_left, q.matching_right):
                        matching_pairs[l_text] = r_text

            # 7. Diagram markers labels
            markers = []
            has_diagram_labels = False
            for m in q.diagram_markers:
                lbl = getattr(m, "label", m.get("label") if isinstance(m, dict) else None)
                if lbl:
                    has_diagram_labels = True
                markers.append(m)

            # Determine whether answer is provided
            effective_type = (q.question_type or sec.question_type or "mcq").lower()
            has_ans = bool(
                ans or 
                (effective_type == "matching" and matching_pairs) or 
                (effective_type in ["diagram_identify", "diagram"] and has_diagram_labels)
            )

            status = "available" if has_ans else "not_provided"

            if has_ans:
                questions_with_answers += 1
            else:
                questions_missing_answers += 1

            if rub:
                questions_with_rubrics += 1

            item = AnswerKeyItem(
                question_id=q.id,
                bank_question_id=q.bank_question_id,
                number=q.number or str(total_questions),
                section_title=sec_title,
                question_text=q.text,
                question_type=effective_type,
                marks=q_marks,
                has_answer=has_ans,
                status=status,
                correct_answer=ans if ans else None,
                alternative_answers=alts,
                explanation=expl if expl else None,
                rubric=rub if rub else None,
                key_points=kps,
                matching_pairs=matching_pairs if matching_pairs else None,
                diagram_mode=q.diagram_mode,
                diagram_markers=markers,
                image_base64=q.image_base64,
                image_caption=q.image_caption
            )
            items.append(item)

    summary = TeacherAnswerKeySummary(
        total_questions=total_questions,
        total_marks=round(total_marks, 2),
        questions_with_answers=questions_with_answers,
        questions_missing_answers=questions_missing_answers,
        questions_with_rubrics=questions_with_rubrics,
        inconsistencies=inconsistencies,
        items=items
    )
    return items, summary


def generate_teacher_answer_key_pdf(
    sections: List[Section],
    config: PaperConfig,
    reference_style: Optional[ReferenceAnalysis] = None
) -> Tuple[Path, int, TeacherAnswerKeySummary]:
    """
    Generates a dedicated, professional Teacher Answer Key PDF.
    Strictly isolates teacher-only solutions, rubrics, and marking schemes from the student paper.
    """
    items, summary = extract_teacher_answer_metadata(sections)

    out_path = TEMP_BASE_DIR / f"teacher_answer_key_{uuid.uuid4().hex[:10]}.pdf"
    page_size = PAGE_SIZES.get(config.page_size, A4)
    page_w, page_h = page_size

    # Layout margins
    m_top = 35.0
    m_bottom = 35.0
    m_left = 40.0
    m_right = 40.0
    printable_w = page_w - m_left - m_right

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=page_size,
        leftMargin=m_left,
        rightMargin=m_right,
        topMargin=m_top,
        bottomMargin=m_bottom
    )

    styles = getSampleStyleSheet()

    # Dedicated Teacher Document Typography Styles
    title_style = ParagraphStyle(
        name="TeacherTitle",
        fontName="Helvetica-Bold",
        fontSize=15.0,
        leading=19.0,
        alignment=1, # Center
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=3
    )

    badge_style = ParagraphStyle(
        name="TeacherBadge",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11.0,
        alignment=1,
        textColor=colors.HexColor("#b91c1c"), # Dark red warning badge
        spaceAfter=6
    )

    meta_style = ParagraphStyle(
        name="TeacherMeta",
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.0,
        alignment=1,
        textColor=colors.HexColor("#334155"),
        spaceAfter=8
    )

    sec_hdr_style = ParagraphStyle(
        name="TeacherSecHdr",
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=15.0,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=4
    )

    q_num_style = ParagraphStyle(
        name="TeacherQNum",
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13.0,
        textColor=colors.HexColor("#0f172a")
    )

    q_text_style = ParagraphStyle(
        name="TeacherQText",
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.0,
        textColor=colors.HexColor("#1e293b")
    )

    ans_box_style = ParagraphStyle(
        name="TeacherAnsBox",
        fontName="Helvetica-Bold",
        fontSize=9.0,
        leading=12.5,
        textColor=colors.HexColor("#047857") # Emerald green
    )

    ans_body_style = ParagraphStyle(
        name="TeacherAnsBody",
        fontName="Helvetica",
        fontSize=8.5,
        leading=12.0,
        textColor=colors.HexColor("#0f172a")
    )

    missing_style = ParagraphStyle(
        name="TeacherMissing",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#b45309") # Amber warning
    )

    rubric_hdr_style = ParagraphStyle(
        name="TeacherRubricHdr",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#4338ca") # Indigo
    )

    expl_style = ParagraphStyle(
        name="TeacherExpl",
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#475569")
    )

    story = []
    temp_files_to_clean: List[Path] = []

    # Document Header Banner
    story.append(Paragraph("<b>TEACHER ANSWER KEY &amp; MARKING SCHEME</b>", title_style))
    story.append(Paragraph("CONFIDENTIAL · FOR TEACHER &amp; EXAMINER EVALUATION ONLY · DO NOT DISTRIBUTE", badge_style))

    # Meta Line: Institution, Subject, Grade, Marks
    meta_parts = []
    if config.institution_name:
        meta_parts.append(sanitize_pdf_text(config.institution_name))
    if config.exam_name:
        meta_parts.append(sanitize_pdf_text(config.exam_name))
    if config.subject_name:
        meta_parts.append(f"<b>Subject:</b> {sanitize_pdf_text(config.subject_name)}")
    if config.semester_class:
        meta_parts.append(f"<b>Class:</b> {sanitize_pdf_text(config.semester_class)}")
    meta_parts.append(f"<b>Total Marks:</b> {summary.total_marks:g}")
    meta_parts.append(f"<b>Total Questions:</b> {summary.total_questions}")

    story.append(Paragraph(" · ".join(meta_parts), meta_style))
    story.append(HRFlowable(width="100%", thickness=1.0, color=colors.HexColor("#cbd5e1"), spaceBefore=2, spaceAfter=8))

    # Answer Key Content by Section
    current_sec = ""
    for item in items:
        q_elements = []

        if item.section_title != current_sec:
            current_sec = item.section_title
            story.append(Spacer(1, 4))
            story.append(Paragraph(f"<b>{sanitize_pdf_text(current_sec)}</b>", sec_hdr_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceBefore=1, spaceAfter=6))

        # Question Line
        q_line = [
            [
                Paragraph(f"<b>Q{sanitize_pdf_text(item.number)}.</b>", q_num_style),
                Paragraph(sanitize_pdf_text(item.question_text), q_text_style),
                Paragraph(f"<b>[{item.marks:g} M]</b>", ParagraphStyle(name="Marks", fontName="Helvetica-Bold", fontSize=9, alignment=2, textColor=colors.HexColor("#64748b")))
            ]
        ]
        q_tbl = Table(q_line, colWidths=[printable_w * 0.08, printable_w * 0.80, printable_w * 0.12])
        q_tbl.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        q_elements.append(q_tbl)

        # Answer Guidance Box (Inner Content Table)
        ans_box_rows = []

        if item.has_answer:
            # Correct answer row
            if item.correct_answer:
                ans_box_rows.append([
                    Paragraph("<b>Correct Answer:</b>", ans_box_style),
                    Paragraph(sanitize_pdf_text(item.correct_answer), ans_body_style)
                ])

            # Alternatives row
            if item.alternative_answers:
                alts_str = " ; ".join(sanitize_pdf_text(a) for a in item.alternative_answers)
                ans_box_rows.append([
                    Paragraph("<b>Accepted Alternatives:</b>", ans_box_style),
                    Paragraph(alts_str, ans_body_style)
                ])

            # Matching pairs row
            if item.matching_pairs:
                pairs_str = "<br/>".join(f"• <b>{sanitize_pdf_text(k)}</b> &rarr; {sanitize_pdf_text(v)}" for k, v in item.matching_pairs.items())
                ans_box_rows.append([
                    Paragraph("<b>Matching Key:</b>", ans_box_style),
                    Paragraph(pairs_str, ans_body_style)
                ])

            # Diagram labels row
            if item.diagram_markers:
                marker_labels = []
                for m_idx, m in enumerate(item.diagram_markers, 1):
                    m_num = getattr(m, "number", m.get("number", m_idx) if isinstance(m, dict) else m_idx)
                    m_lbl = getattr(m, "label", m.get("label") if isinstance(m, dict) else None)
                    marker_labels.append(f"<b>({m_num})</b> {sanitize_pdf_text(m_lbl) if m_lbl else '<i>[Label not provided]</i>'}")
                labels_str = " &nbsp;&nbsp;|&nbsp;&nbsp; ".join(marker_labels)
                ans_box_rows.append([
                    Paragraph("<b>Diagram Labels:</b>", ans_box_style),
                    Paragraph(labels_str, ans_body_style)
                ])

            # Key points
            if item.key_points:
                kps_str = "<br/>".join(f"• {sanitize_pdf_text(p)}" for p in item.key_points)
                ans_box_rows.append([
                    Paragraph("<b>Expected Points:</b>", rubric_hdr_style),
                    Paragraph(kps_str, ans_body_style)
                ])

            # Marking rubric
            if item.rubric:
                ans_box_rows.append([
                    Paragraph("<b>Marking Rubric:</b>", rubric_hdr_style),
                    Paragraph(sanitize_pdf_text(item.rubric), ans_body_style)
                ])

            # Solution / Explanation
            if item.explanation:
                ans_box_rows.append([
                    Paragraph("<b>Explanation:</b>", expl_style),
                    Paragraph(sanitize_pdf_text(item.explanation), expl_style)
                ])

        else:
            ans_box_rows.append([
                Paragraph("<b>Answer Status:</b>", missing_style),
                Paragraph("<b>Answer not provided</b> in Question Bank. Evaluate based on examiner discretion.", missing_style)
            ])

        # Style the Answer Box
        box_tbl = Table(ans_box_rows, colWidths=[printable_w * 0.24, printable_w * 0.72])
        bg_col = colors.HexColor("#f0fdf4") if item.has_answer else colors.HexColor("#fffbeb") # Light green or light amber
        border_col = colors.HexColor("#bbf7d0") if item.has_answer else colors.HexColor("#fde68a")

        box_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), bg_col),
            ('BOX', (0,0), (-1,-1), 0.75, border_col),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('LINEBELOW', (0,0), (-1,-2), 0.5, colors.HexColor("#e2e8f0")),
        ]))

        q_elements.append(Spacer(1, 2))
        q_elements.append(box_tbl)
        q_elements.append(Spacer(1, 6))

        story.append(KeepTogether(q_elements))

    # Canvas properties for Teacher Document (clean numbered border canvas)
    NumberedBorderCanvas.has_page_border = True
    NumberedBorderCanvas.border_inset = 22.0
    NumberedBorderCanvas.border_width = 1.0
    NumberedBorderCanvas.border_color = colors.HexColor("#cbd5e1")
    NumberedBorderCanvas.show_page_numbers = True
    NumberedBorderCanvas.footer_has_line = True
    NumberedBorderCanvas.custom_footer_text = f"Teacher Answer Key · {config.subject_name or 'Exam'} · CONFIDENTIAL"

    try:
        doc.build(story, canvasmaker=NumberedBorderCanvas)
    finally:
        for tf in temp_files_to_clean:
            cleanup_file(tf)

    try:
        import pymupdf as fitz
        check_doc = fitz.open(out_path)
        actual_page_count = len(check_doc)
        check_doc.close()
    except Exception:
        actual_page_count = 1

    return out_path, actual_page_count, summary
