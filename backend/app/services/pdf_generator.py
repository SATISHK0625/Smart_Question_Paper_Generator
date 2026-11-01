import os
import uuid
import base64
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import html

from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch
pt = 1
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Image as RLImage
)
from reportlab.pdfgen import canvas

from ..models.schemas import Section, Question, PaperConfig, ReferenceAnalysis, OverviewData
from ..utils.file_utils import TEMP_BASE_DIR, REFERENCES_DIR, cleanup_file, get_reference_path

PAGE_SIZES = {
    "A4": A4,
    "Letter": letter
}

class NumberedBorderCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and draw:
    1. Outer Page Border (if detected in reference or requested by user)
    2. 'Page X of Y' and document running footers (only if requested)
    """
    has_page_border = False
    border_inset = 25.0
    border_width = 1.2
    border_color = colors.black

    show_page_numbers = False
    footer_has_line = False
    custom_footer_text = ""

    def __init__(self, *args, **kwargs):
        super(NumberedBorderCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        page_w, page_h = self._pagesize

        # 1. Draw Page Border if enabled
        if getattr(self, "has_page_border", False):
            inset = getattr(self, "border_inset", 25.0)
            b_width = getattr(self, "border_width", 1.2)
            b_color = getattr(self, "border_color", colors.black)
            self.setStrokeColor(b_color)
            self.setLineWidth(b_width)
            self.rect(inset, inset, page_w - 2 * inset, page_h - 2 * inset)

        # 2. Draw Footers only if requested
        show_numbers = getattr(self, "show_page_numbers", False)
        footer_line = getattr(self, "footer_has_line", False)
        footer_text = getattr(self, "custom_footer_text", "")

        if show_numbers or footer_line or footer_text:
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#4b5563"))

            if footer_line:
                self.setStrokeColor(colors.HexColor("#d1d5db"))
                self.setLineWidth(0.5)
                self.line(40, 32, page_w - 40, 32)

            if footer_text:
                self.drawString(40, 20, str(footer_text))

            if show_numbers:
                page_text = f"Page {self._pageNumber} of {page_count}"
                self.drawRightString(page_w - 40, 20, page_text)

        self.restoreState()

def sanitize_pdf_text(text: Optional[str]) -> str:
    if not text:
        return ""
    t = text.replace("\u2013", "–").replace("\u2014", "—").replace("\u2018", "'").replace("\u2019", "'")
    t = t.replace("\u201c", '"').replace("\u201d", '"').replace("\u00a0", " ")
    return html.escape(t).replace("\n", "<br/>")

def build_header_flowables(
    config: PaperConfig,
    reference_style: Optional[ReferenceAnalysis],
    width: float,
    styles: dict,
    temp_files_to_clean: List[Path]
) -> List:
    elements = []

    # Check if reference has a worksheet header or logo
    is_worksheet_mode = (
        reference_style is not None and 
        reference_style.document_type == "worksheet" and 
        config.use_reference_header
    )

    if is_worksheet_mode and reference_style:
        # 1. Logo if present
        if reference_style.header_logo_base64:
            try:
                logo_bytes = base64.b64decode(reference_style.header_logo_base64)
                logo_path = TEMP_BASE_DIR / f"logo_{uuid.uuid4().hex[:8]}.png"
                logo_path.write_bytes(logo_bytes)
                temp_files_to_clean.append(logo_path)

                l_w = min(reference_style.header_logo_width, 140.0)
                l_h = min(reference_style.header_logo_height, 60.0)
                logo_img = RLImage(str(logo_path), width=l_w, height=l_h)
                logo_img.hAlign = 'CENTER'
                elements.append(logo_img)
                elements.append(Spacer(1, 4))
            except Exception:
                pass

        # 2. Header Title Lines
        # If user explicitly supplied institution_name / exam_name, use user's
        if config.institution_name:
            elements.append(Paragraph(f"<b>{sanitize_pdf_text(config.institution_name)}</b>", styles["SchoolTitle"]))
            if config.subject_name:
                subj_line = config.subject_name + (f" ({config.subject_code})" if config.subject_code else "")
                elements.append(Paragraph(sanitize_pdf_text(subj_line), styles["GradeSub"]))
            if config.exam_name:
                elements.append(Paragraph(f"<b>{sanitize_pdf_text(config.exam_name)}</b>", styles["WorksheetTitle"]))
        elif reference_style.header_lines:
            # Re-use detected header lines from reference
            for idx, hl in enumerate(reference_style.header_lines):
                s_text = sanitize_pdf_text(hl.text)
                if idx == 0:
                    elements.append(Paragraph(f"<b>{s_text}</b>", styles["SchoolTitle"]))
                elif idx == 1:
                    elements.append(Paragraph(s_text, styles["GradeSub"]))
                else:
                    elements.append(Paragraph(f"<b>{s_text}</b>", styles["WorksheetTitle"]))

        # 3. Horizontal rule divider if in reference
        if reference_style.has_header_divider:
            elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.black, spaceBefore=3, spaceAfter=8))
        else:
            elements.append(Spacer(1, 6))

        return elements

    # Traditional Examination Paper Mode (College/University format)
    inst_name = sanitize_pdf_text(config.institution_name)
    dept_name = sanitize_pdf_text(config.department)
    exam_name = sanitize_pdf_text(config.exam_name)
    subj_name = sanitize_pdf_text(config.subject_name)
    subj_code = sanitize_pdf_text(config.subject_code)
    sem_class = sanitize_pdf_text(config.semester_class)
    date_str = sanitize_pdf_text(config.date_str)
    duration = sanitize_pdf_text(config.duration)
    max_marks = f"{config.maximum_marks:g}" if config.maximum_marks is not None else ""

    if inst_name:
        elements.append(Paragraph(f"<b>{inst_name.upper()}</b>", styles["SchoolTitle"]))
    if dept_name:
        elements.append(Paragraph(f"<b>{dept_name}</b>", styles["SubHeader"]))
    if exam_name:
        elements.append(Paragraph(f"<b>{exam_name}</b>", styles["SubHeader"]))

    elements.append(Spacer(1, 4))

    # Only show metadata grid if user actually provided these fields or explicitly selected boxed style
    has_meta_fields = bool(subj_name or subj_code or sem_class or duration or max_marks)
    if has_meta_fields and (config.header_style == "boxed" or config.header_style == "underlined"):
        row1_left = (f"<b>Subject:</b> {subj_name}" + (f" ({subj_code})" if subj_code else "")) if subj_name else ""
        row1_right = f"<b>Semester/Class:</b> {sem_class}" if sem_class else ""
        row2_left = f"<b>Time / Duration:</b> {duration}" if duration else ""
        row2_right = f"<b>Maximum Marks:</b> {max_marks}" if max_marks else ""

        if date_str:
            row2_left = f"{row2_left} | <b>Date:</b> {date_str}" if row2_left else f"<b>Date:</b> {date_str}"

        grid_data = [
            [Paragraph(row1_left, styles["MetaText"]), Paragraph(row1_right, styles["MetaTextRight"])],
            [Paragraph(row2_left, styles["MetaText"]), Paragraph(row2_right, styles["MetaTextRight"])]
        ]

        col_w = width / 2.0
        meta_table = Table(grid_data, colWidths=[col_w, col_w])
        if config.header_style == "boxed":
            meta_table.setStyle(TableStyle([
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#1e293b")),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc"))
            ]))
        else:
            meta_table.setStyle(TableStyle([
                ('LINEBELOW', (0,1), (-1,1), 1, colors.HexColor("#1e293b")),
                ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ]))

        elements.append(meta_table)
        elements.append(Spacer(1, 8))

    # General Instructions
    if config.general_instructions:
        elements.append(Paragraph("<b>General Instructions:</b>", styles["InstrHeading"]))
        for idx, instr in enumerate(config.general_instructions, start=1):
            s_instr = sanitize_pdf_text(instr)
            bullet = f"{idx}. {s_instr}" if len(config.general_instructions) > 1 else s_instr
            elements.append(Paragraph(bullet, styles["InstrBody"]))
        elements.append(Spacer(1, 8))

    return elements

def build_section_flowables(
    section: Section,
    printable_width: float,
    styles: dict,
    reference_style: Optional[ReferenceAnalysis],
    config: PaperConfig,
    temp_files_to_clean: List[Path]
) -> List:
    elements = []

    # Determine if section banner should be shaded or unshaded
    has_background = False
    if reference_style and reference_style.section_style:
        has_background = reference_style.section_style.get("has_background", False)

    sec_title = sanitize_pdf_text(section.title)

    if has_background:
        # Shaded examination banner
        sec_header_p = Paragraph(f"<b>{sec_title}</b>", styles["ExamSectionTitle"])
        sec_table_data = [[sec_header_p]]
        if section.instructions:
            s_instr = sanitize_pdf_text(section.instructions)
            sec_table_data.append([Paragraph(f"<i>{s_instr}</i>", styles["SectionInstr"])])

        sec_banner = Table(sec_table_data, colWidths=[printable_width])
        sec_banner.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('LINEBELOW', (0,-1), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ]))
        elements.append(Spacer(1, 8))
        elements.append(sec_banner)
        elements.append(Spacer(1, 6))
    else:
        # Clean worksheet section heading (unshaded, bold, left-aligned)
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"<b>{sec_title}</b>", styles["WorksheetSectionTitle"]))
        if section.instructions:
            s_instr = sanitize_pdf_text(section.instructions)
            elements.append(Paragraph(f"<i>{s_instr}</i>", styles["WorksheetSectionInstr"]))
        elements.append(Spacer(1, 6))

    # Check if section has matching questions
    matching_questions = [q for q in section.questions if q.is_matching or (q.matching_col_a and q.matching_col_b)]
    if matching_questions and len(matching_questions) >= 2:
        # Render as a two-column matching table
        col_w1 = printable_width * 0.48
        col_w2 = printable_width * 0.52
        table_rows = [
            [Paragraph("<b>Column A</b>", styles["MatchHdr"]), Paragraph("<b>Column B</b>", styles["MatchHdr"])]
        ]
        for mq in matching_questions:
            col_a_txt = mq.matching_col_a or mq.text
            col_b_txt = mq.matching_col_b or ""
            # Format with number if not present
            if not col_a_txt.startswith(f"{mq.number}."):
                col_a_txt = f"{mq.number}. {col_a_txt}"
            table_rows.append([
                Paragraph(sanitize_pdf_text(col_a_txt), styles["MatchTxt"]),
                Paragraph(sanitize_pdf_text(col_b_txt), styles["MatchTxt"])
            ])

        match_table = Table(table_rows, colWidths=[col_w1, col_w2])
        match_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 2.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        elements.append(match_table)
        elements.append(Spacer(1, 6))
        return elements

    # Regular questions
    has_any_marks = any(q.marks is not None for q in section.questions)

    for q in section.questions:
        q_elements = []

        q_num = sanitize_pdf_text(q.number)
        q_text = sanitize_pdf_text(q.text)
        marks_str = f"[{q.marks:g}]" if q.marks is not None else ""

        if has_any_marks and marks_str:
            # 3-column table: [Number, Text, Marks]
            col_num = 24.0
            col_marks = 38.0
            col_text = printable_width - col_num - col_marks

            row = [
                Paragraph(f"<b>{q_num}.</b>", styles["QuestionNum"]),
                Paragraph(q_text, styles["QuestionBody"]),
                Paragraph(f"<b>{marks_str}</b>", styles["MarksRight"])
            ]
            q_table = Table([row], colWidths=[col_num, col_text, col_marks])
            q_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ]))
            q_elements.append(q_table)
        else:
            # Clean full-width question line
            full_q_line = f"<b>{q_num}.</b> {q_text}"
            q_elements.append(Paragraph(full_q_line, styles["QuestionBody"]))

        # Match the Following Two-Column Table
        if (q.question_type in ["matching", "match_the_following"] or q.is_matching or (q.matching_left and q.matching_right)) and (q.matching_left and q.matching_right):
            import random
            right_items = list(q.matching_right)
            if q.shuffle_right:
                seed = sum(ord(c) for c in (q.id or "matching_seed"))
                random.Random(seed).shuffle(right_items)

            col_w1 = (printable_width - 20.0) * 0.48
            col_w2 = (printable_width - 20.0) * 0.52
            table_rows = [
                [Paragraph("<b>Column A</b>", styles["MatchHdr"]), Paragraph("<b>Column B</b>", styles["MatchHdr"])]
            ]
            for l_item, r_item in zip(q.matching_left, right_items):
                table_rows.append([
                    Paragraph(sanitize_pdf_text(str(l_item)), styles["MatchTxt"]),
                    Paragraph(sanitize_pdf_text(str(r_item)), styles["MatchTxt"])
                ])

            m_table = Table(table_rows, colWidths=[col_w1, col_w2])
            m_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,0), (-1,-1), 2.5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
                ('LEFTPADDING', (0,0), (-1,-1), 4),
                ('RIGHTPADDING', (0,0), (-1,-1), 4),
                ('LINEBELOW', (0,0), (-1,0), 0.8, colors.HexColor("#cbd5e1")),
            ]))
            q_elements.append(Spacer(1, 3))
            q_elements.append(m_table)
            q_elements.append(Spacer(1, 4))

        # Image-Based Questions & Diagram Identification
        if q.image_base64:
            import io
            from .image_renderer import render_diagram_with_markers, get_image_display_dimensions, decode_base64_image
            try:
                if q.diagram_markers and len(q.diagram_markers) > 0:
                    png_bytes, orig_w, orig_h = render_diagram_with_markers(
                        q.image_base64,
                        q.diagram_mode or "numbered_markers",
                        q.diagram_markers
                    )
                else:
                    raw_img = decode_base64_image(q.image_base64)
                    orig_w, orig_h = raw_img.size
                    buf = io.BytesIO()
                    raw_img.convert("RGB").save(buf, format="PNG")
                    png_bytes = buf.getvalue()

                tmp_img_file = TEMP_BASE_DIR / f"qimg_{uuid.uuid4().hex}.png"
                with open(tmp_img_file, "wb") as f:
                    f.write(png_bytes)
                temp_files_to_clean.append(tmp_img_file)

                ratio = min(max(float(q.image_width_ratio or 0.65), 0.25), 0.95)
                max_w = printable_width * ratio
                max_h = 240.0
                dw, dh = get_image_display_dimensions(orig_w, orig_h, max_w, max_h)

                q_elements.append(Spacer(1, 4))
                q_elements.append(RLImage(str(tmp_img_file), width=dw, height=dh, hAlign='CENTER'))
                q_elements.append(Spacer(1, 2))

                if q.image_caption:
                    q_elements.append(Paragraph(f"<i>Figure: {sanitize_pdf_text(q.image_caption)}</i>", styles["ImageCaption"]))
                    q_elements.append(Spacer(1, 3))

                # Numbered markers response write-in blanks for student paper
                if q.diagram_markers and q.diagram_mode == "numbered_markers":
                    blank_cells = []
                    row = []
                    for m_idx, marker in enumerate(q.diagram_markers, 1):
                        m_num = getattr(marker, "number", marker.get("number", m_idx) if isinstance(marker, dict) else m_idx)
                        cell_p = Paragraph(f"<b>({m_num})</b> ______________________", styles["MatchTxt"])
                        row.append(cell_p)
                        if len(row) == 2:
                            blank_cells.append(row)
                            row = []
                    if row:
                        while len(row) < 2:
                            row.append(Paragraph("", styles["MatchTxt"]))
                        blank_cells.append(row)

                    if blank_cells:
                        blanks_tbl = Table(blank_cells, colWidths=[printable_width * 0.48, printable_width * 0.48])
                        blanks_tbl.setStyle(TableStyle([
                            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                            ('TOPPADDING', (0,0), (-1,-1), 3),
                            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                            ('LEFTPADDING', (0,0), (-1,-1), 10),
                        ]))
                        q_elements.append(Spacer(1, 3))
                        q_elements.append(blanks_tbl)
                        q_elements.append(Spacer(1, 3))

            except Exception as img_err:
                print(f"[pdf_generator] Failed to render question image: {img_err}")

        # Multiple Choice Options
        if q.options and len(q.options) > 0:
            joined_opts = "   ".join(sanitize_pdf_text(opt) for opt in q.options)
            q_elements.append(Spacer(1, 2))
            q_elements.append(Paragraph(joined_opts, styles["OptionsText"]))
            q_elements.append(Spacer(1, 4))
        else:
            q_elements.append(Spacer(1, 4))

        # Subquestions if any
        if q.subquestions:
            for sq in q.subquestions:
                sq_lbl = sanitize_pdf_text(sq.label)
                sq_txt = sanitize_pdf_text(sq.text)
                sq_marks = f"[{sq.marks:g}]" if sq.marks is not None else ""
                sq_line = f"<i>{sq_lbl}</i> {sq_txt} " + (f"<b>{sq_marks}</b>" if sq_marks else "")
                q_elements.append(Paragraph(sq_line, styles["SubQBody"]))
                q_elements.append(Spacer(1, 2))

        elements.append(KeepTogether(q_elements))

    return elements

def create_document_styles(reference_style: Optional[ReferenceAnalysis] = None, config: Optional[PaperConfig] = None):
    styles = getSampleStyleSheet()

    font_name = "Helvetica"
    font_size = 10.0
    heading_size = 12.0
    line_spacing = 14.0

    if reference_style:
        font_name = reference_style.primary_font
        font_size = reference_style.primary_font_size
        heading_size = reference_style.heading_font_size
        line_spacing = font_size + 3.5

    # Apply user interactive overrides if provided
    if config:
        if config.override_font_size:
            font_size = config.override_font_size
            line_spacing = font_size + 3.5
        if config.override_line_spacing:
            line_spacing = config.override_line_spacing

    bold_font = f"{font_name}-Bold" if font_name in ["Helvetica", "Times-Roman", "Courier"] else "Helvetica-Bold"
    oblique_font = f"{font_name}-Oblique" if font_name in ["Helvetica", "Times-Roman"] else "Helvetica-Oblique"

    # Worksheet Top Titles
    styles.add(ParagraphStyle(
        name="SchoolTitle",
        fontName=bold_font,
        fontSize=heading_size + 3.0,
        leading=heading_size + 6.0,
        alignment=1, # Center
        textColor=colors.black,
        spaceAfter=2
    ))

    styles.add(ParagraphStyle(
        name="GradeSub",
        fontName=font_name,
        fontSize=heading_size - 0.5,
        leading=heading_size + 2.5,
        alignment=1, # Center
        textColor=colors.black,
        spaceAfter=2
    ))

    styles.add(ParagraphStyle(
        name="WorksheetTitle",
        fontName=bold_font,
        fontSize=heading_size + 1.5,
        leading=heading_size + 4.5,
        alignment=1, # Center
        textColor=colors.black,
        spaceAfter=4
    ))

    # Section Titles
    styles.add(ParagraphStyle(
        name="WorksheetSectionTitle",
        fontName=bold_font,
        fontSize=heading_size - 0.5,
        leading=heading_size + 3.0,
        alignment=0, # Left-aligned for worksheets
        textColor=colors.black,
        spaceBefore=8,
        spaceAfter=4
    ))

    styles.add(ParagraphStyle(
        name="WorksheetSectionInstr",
        fontName=oblique_font,
        fontSize=font_size - 0.5,
        leading=font_size + 2.0,
        alignment=0,
        textColor=colors.HexColor("#374151")
    ))

    styles.add(ParagraphStyle(
        name="ExamSectionTitle",
        fontName=bold_font,
        fontSize=font_size + 1.0,
        leading=font_size + 4.0,
        alignment=1, # Center
        textColor=colors.HexColor("#0f172a")
    ))

    styles.add(ParagraphStyle(
        name="SectionInstr",
        fontName=oblique_font,
        fontSize=font_size - 1.0,
        leading=font_size + 2.0,
        alignment=1,
        textColor=colors.HexColor("#475569")
    ))

    # Questions & Options
    styles.add(ParagraphStyle(
        name="QuestionNum",
        fontName=bold_font,
        fontSize=font_size,
        leading=line_spacing,
        alignment=0,
        textColor=colors.black
    ))

    styles.add(ParagraphStyle(
        name="QuestionBody",
        fontName=font_name,
        fontSize=font_size,
        leading=line_spacing,
        textColor=colors.black
    ))

    styles.add(ParagraphStyle(
        name="OptionsText",
        fontName=font_name,
        fontSize=font_size - 0.5,
        leading=line_spacing - 1.0,
        leftIndent=14,
        textColor=colors.black
    ))

    styles.add(ParagraphStyle(
        name="SubQBody",
        fontName=font_name,
        fontSize=font_size - 0.5,
        leading=line_spacing - 1.0,
        leftIndent=14,
        textColor=colors.black
    ))

    styles.add(ParagraphStyle(
        name="MarksRight",
        fontName=bold_font,
        fontSize=font_size - 0.5,
        leading=line_spacing,
        alignment=2,
        textColor=colors.black
    ))

    # Matching columns
    styles.add(ParagraphStyle(
        name="MatchHdr",
        fontName=bold_font,
        fontSize=font_size,
        leading=line_spacing,
        textColor=colors.black
    ))

    styles.add(ParagraphStyle(
        name="MatchTxt",
        fontName=font_name,
        fontSize=font_size - 0.5,
        leading=line_spacing - 1.0,
        textColor=colors.black
    ))

    styles.add(ParagraphStyle(
        name="ImageCaption",
        fontName=oblique_font,
        fontSize=font_size - 1.0,
        leading=font_size + 1.0,
        alignment=1,
        textColor=colors.HexColor("#4b5563")
    ))

    # Traditional meta styles
    styles.add(ParagraphStyle(
        name="SubHeader",
        fontName=bold_font,
        fontSize=heading_size - 1.0,
        leading=heading_size + 2.0,
        alignment=1,
        textColor=colors.HexColor("#334155"),
        spaceAfter=2
    ))

    styles.add(ParagraphStyle(
        name="MetaText",
        fontName=font_name,
        fontSize=font_size - 1.0,
        leading=font_size + 2.0,
        textColor=colors.HexColor("#1e293b")
    ))

    styles.add(ParagraphStyle(
        name="MetaTextRight",
        fontName=font_name,
        fontSize=font_size - 1.0,
        leading=font_size + 2.0,
        alignment=2,
        textColor=colors.HexColor("#1e293b")
    ))

    styles.add(ParagraphStyle(
        name="InstrHeading",
        fontName=bold_font,
        fontSize=font_size - 0.5,
        leading=font_size + 2.0,
        textColor=colors.black,
        spaceBefore=2,
        spaceAfter=1
    ))

    styles.add(ParagraphStyle(
        name="InstrBody",
        fontName=font_name,
        fontSize=font_size - 1.0,
        leading=font_size + 2.0,
        textColor=colors.HexColor("#334155")
    ))

    return styles

def find_reference_pdf_path(reference_style: Optional[ReferenceAnalysis], config: PaperConfig) -> Optional[Path]:
    """
    Search for the original reference PDF to use as an exact template:
    1. Check reference_style.reference_id / reference_pdf_path
    2. Check config.reference_id / reference_pdf_path
    3. Check REFERENCES_DIR / "latest_reference.pdf"
    4. Fall back to fixtures only if testing or no upload was given
    """
    ref_id = (reference_style.reference_id if reference_style else None) or (config.reference_id if config else None)
    ref_path_str = (reference_style.reference_pdf_path if reference_style else None) or (getattr(config, "reference_pdf_path", None) if config else None)

    # 1. First priority: exact reference ID or exact path passed from client
    path = get_reference_path(reference_id=ref_id, reference_pdf_path=ref_path_str)
    if path and path.exists() and path.is_file():
        return path

    # 2. If a specific path or filename was requested, look up in test fixtures or workspace
    if ref_path_str:
        p = Path(ref_path_str)
        if p.exists() and p.is_file():
            return p
        ws_root = Path(__file__).resolve().parent.parent.parent.parent
        for candidate in [ws_root / "backend" / "test_fixtures" / p.name, ws_root / p.name]:
            if candidate.exists() and candidate.is_file() and candidate.stat().st_size > 100:
                return candidate

    # 3. If reference_style exists, check latest uploaded reference
    if reference_style is not None:
        latest = REFERENCES_DIR / "latest_reference.pdf"
        if latest.exists() and latest.is_file() and latest.stat().st_size > 100:
            return latest

    return None

def generate_pdf(
    sections: List[Section],
    config: PaperConfig,
    reference_style: Optional[ReferenceAnalysis] = None,
    include_overview: bool = False,
    is_overview_only: bool = False
) -> Tuple[Path, int]:
    file_id = uuid.uuid4().hex
    out_filename = f"paper_{file_id}.pdf"
    out_path = TEMP_BASE_DIR / out_filename
    temp_files_to_clean: List[Path] = []

    # Check if we should use exact template-preserving PyMuPDF modification
    # (Preserves template for both selectable-text and scanned documents)
    if not is_overview_only and reference_style is not None:
        ref_template_path = find_reference_pdf_path(reference_style, config)
        if ref_template_path is not None:
            try:
                from .pdf_template_modifier import modify_pdf_template
                return modify_pdf_template(
                    template_path=ref_template_path,
                    sections=sections,
                    config=config,
                    reference_style=reference_style,
                    out_path=out_path
                )
            except Exception as e:
                import traceback
                print(f"[PDF Generator] modify_pdf_template failed on template '{ref_template_path}': {e}")
                traceback.print_exc()
                raise RuntimeError(f"Template preservation failed on '{ref_template_path.name}': {str(e)}") from e


    # Margins and Page Size
    page_size = PAGE_SIZES.get(config.page_size, A4)
    page_w, page_h = page_size

    # Defaults
    left_m = 40.0
    right_m = 40.0
    top_m = 35.0
    bottom_m = 35.0

    if reference_style and reference_style.margins:
        rm = reference_style.margins
        left_m = max(float(rm.get("left", 40.0)), 28.0)
        right_m = max(float(rm.get("right", 40.0)), 28.0)
        top_m = max(float(rm.get("top", 35.0)), 28.0)
        bottom_m = max(float(rm.get("bottom", 35.0)), 28.0)

    # Interactive overrides
    if config.override_margins:
        om = config.override_margins
        left_m = float(om.get("left", left_m))
        right_m = float(om.get("right", right_m))
        top_m = float(om.get("top", top_m))
        bottom_m = float(om.get("bottom", bottom_m))

    printable_w = page_w - left_m - right_m

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=page_size,
        leftMargin=left_m,
        rightMargin=right_m,
        topMargin=top_m,
        bottomMargin=bottom_m
    )

    styles = create_document_styles(reference_style, config)
    story = []

    # Overview calculations if requested
    from .overview_service import compute_overview_data
    overview = compute_overview_data(sections, config)

    if is_overview_only:
        from .pdf_generator_helpers import build_overview_table_flowables
        story.extend(build_overview_table_flowables(overview, printable_w, styles))
    else:
        # Header banner
        story.extend(build_header_flowables(config, reference_style, printable_w, styles, temp_files_to_clean))

        # Sections and Questions
        for sec in sections:
            story.extend(build_section_flowables(sec, printable_w, styles, reference_style, config, temp_files_to_clean))

        if include_overview and config.overview_placement == "end_of_paper":
            from .pdf_generator_helpers import build_overview_table_flowables
            story.append(PageBreak())
            story.extend(build_overview_table_flowables(overview, printable_w, styles))

    # Canvas properties: Page border & footers
    has_border = reference_style.has_page_border if reference_style else False
    if config.override_page_border is not None:
        has_border = config.override_page_border

    NumberedBorderCanvas.has_page_border = has_border
    if reference_style:
        NumberedBorderCanvas.border_inset = reference_style.border_inset_pt
        NumberedBorderCanvas.border_width = reference_style.border_width_pt
        try:
            NumberedBorderCanvas.border_color = colors.HexColor(reference_style.border_color_hex)
        except Exception:
            NumberedBorderCanvas.border_color = colors.black

    NumberedBorderCanvas.show_page_numbers = config.show_page_numbers
    NumberedBorderCanvas.footer_has_line = reference_style.footer_has_line if reference_style else False
    NumberedBorderCanvas.custom_footer_text = config.subject_code if (config.subject_code and config.show_page_numbers) else ""

    try:
        doc.build(story, canvasmaker=NumberedBorderCanvas)
    finally:
        # Cleanup any temporary decoded logo files
        for tf in temp_files_to_clean:
            cleanup_file(tf)

    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    try:
        check_doc = fitz.open(out_path)
        actual_page_count = len(check_doc)
        check_doc.close()
    except Exception:
        actual_page_count = 1

    return out_path, actual_page_count
