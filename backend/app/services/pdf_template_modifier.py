import os
import re
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
try:
    import pymupdf as fitz
except ImportError:
    import fitz

from ..models.schemas import Section, Question, PaperConfig, ReferenceAnalysis

SECTION_PATTERN = re.compile(
    r"^\s*(?:###\s*)?(?:(?:[A-Z]\.|\([A-Z]\)|(?:PART|SECTION|MODULE|UNIT|GROUP)\s+[A-Z0-9IVXLCDM]+))\s+([A-Z\s\-_/]+)$",
    re.IGNORECASE
)
section_pattern = SECTION_PATTERN


def get_font_params(family: str = "helv", is_bold: bool = False, is_italic: bool = False) -> Dict[str, Any]:
    """
    Resolve font arguments for PyMuPDF text insertion using standard PDF Base-14 fonts.
    This guarantees clean standard ASCII space encoding, crisp glyph rendering,
    and cross-platform consistency.
    """
    fam = family.lower()
    if any(term in fam for term in ["times", "times-roman", "serif", "roman", "georgia"]):
        if is_bold and is_italic:
            return {"fontname": "tibi"}
        elif is_bold:
            return {"fontname": "tibo"}
        elif is_italic:
            return {"fontname": "tiit"}
        return {"fontname": "times-roman"}
    elif any(term in fam for term in ["courier", "mono", "typewriter"]):
        if is_bold and is_italic:
            return {"fontname": "cobi"}
        elif is_bold:
            return {"fontname": "cobo"}
        elif is_italic:
            return {"fontname": "coit"}
        return {"fontname": "courier"}

    # Default to standard sans-serif (Helvetica / Arial / Calibri)
    if is_bold and is_italic:
        return {"fontname": "hebi"}
    elif is_bold:
        return {"fontname": "hebo"}
    elif is_italic:
        return {"fontname": "heit"}
    return {"fontname": "helv"}

def clean_section_title(title: str) -> str:
    """
    Normalizes section title like '(B) CHOOSE THE CORRECT ANSWER' or '### A. FILL IN THE BLANKS'
    to 'B. CHOOSE THE CORRECT ANSWER'.
    """
    t = title.strip()
    t = re.sub(r"^#+\s*", "", t)
    m = re.match(r"^\(([A-Z0-9]+)\)\s*(?:[:\.\-]\s*)?(.*)$", t, re.IGNORECASE)
    if m:
        return f"{m.group(1).upper()}. {m.group(2).strip()}"
    return t

def analyze_template_geometry(doc: fitz.Document, reference_style: Optional[ReferenceAnalysis] = None) -> Dict[str, Any]:
    """
    Dynamically inspects any uploaded reference template PDF to extract exact geometry:
    - Page dimensions (A4, Letter, Custom)
    - Outer rectangular border (if present)
    - Header divider rule and first content position
    - Margins and content boundaries on Page 0 vs subsequent pages
    - Running header / footer boundaries on subsequent pages
    """
    p0 = doc[0]
    page_w = float(p0.rect.width)
    page_h = float(p0.rect.height)

    # 1. Detect Outer Rectangular Border
    has_border = False
    border_inset_left = 30.0
    border_inset_right = 30.0
    border_inset_top = 30.0
    border_inset_bottom = 30.0
    border_color = (0, 0, 0)
    border_width = 1.0

    drawings = p0.get_drawings()
    for d in drawings:
        r = d.get("rect")
        if r:
            rx0, ry0, rx1, ry1 = r
            rw = rx1 - rx0
            rh = ry1 - ry0
            # Outer border enclosing >= 75% of page
            if rx0 <= 55 and ry0 <= 55 and (page_w - rx1) <= 55 and (page_h - ry1) <= 55:
                if rw > page_w * 0.75 and rh > page_h * 0.75:
                    has_border = True
                    border_inset_left = rx0
                    border_inset_top = ry0
                    border_inset_right = page_w - rx1
                    border_inset_bottom = page_h - ry1
                    if d.get("color"):
                        border_color = d.get("color")
                    if d.get("width"):
                        border_width = d.get("width")
                    break

    # If reference_style already analyzed border, reconcile
    if reference_style and reference_style.has_page_border:
        has_border = True
        border_inset_left = border_inset_right = reference_style.border_inset_pt
        border_inset_top = border_inset_bottom = reference_style.border_inset_pt

    # 2. Detect Horizontal Divider Rule below Header on Page 0
    header_divider_y = page_h * 0.25
    has_divider = False
    for d in drawings:
        r = d.get("rect")
        if r:
            rx0, ry0, rx1, ry1 = r
            rw = rx1 - rx0
            rh = ry1 - ry0
            if rw > page_w * 0.50 and rh <= 5.0 and (35.0 <= ry0 <= page_h * 0.38):
                header_divider_y = ry0
                has_divider = True
                break
        for item in d.get("items", []):
            if item[0] == "l":
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) <= 2.5 and abs(p1.x - p2.x) > page_w * 0.50 and (35.0 <= p1.y <= page_h * 0.38):
                    header_divider_y = p1.y
                    has_divider = True
                    break

    # 3. Detect First Content Item on Page 0 (Topmost section title or question)
    p0_blocks = p0.get_text("blocks")
    first_content_y = None
    for b in p0_blocks:
        x0, y0, x1, y1, text, bno, btype = b
        cleaned = text.strip()
        if btype == 0 and cleaned and y0 > 35.0:
            is_sec = bool(SECTION_PATTERN.match(cleaned))
            is_q = bool(re.match(r"^\s*(?:[A-Z]\.|\d+[\.\)]|\([0-9a-zA-Z]+\)|Q\d+[:\.])\s+", cleaned))
            if is_sec or is_q:
                if first_content_y is None or y0 < first_content_y:
                    first_content_y = y0

    # Determine Header Bottom Boundary on Page 0
    if has_divider and (first_content_y is None or header_divider_y <= first_content_y):
        header_bottom_y = header_divider_y
    elif first_content_y is not None:
        header_bottom_y = first_content_y - 6.0
    else:
        header_bottom_y = header_divider_y if has_divider else (page_h * 0.22)

    # 4. Margins & Content Bounds
    if has_border:
        content_left = max(border_inset_left + 12.0, 32.0)
        content_right = min(page_w - border_inset_right - 12.0, page_w - 32.0)
        content_bottom = min(page_h - border_inset_bottom - 12.0, page_h - 35.0)
    else:
        if reference_style and reference_style.margins:
            content_left = max(float(reference_style.margins.get("left", 40.0)), 28.0)
            content_right = min(page_w - float(reference_style.margins.get("right", 40.0)), page_w - 28.0)
            content_bottom = min(page_h - float(reference_style.margins.get("bottom", 35.0)), page_h - 30.0)
        else:
            content_left = 40.0
            content_right = page_w - 40.0
            content_bottom = page_h - 40.0

    p0_content_top = header_bottom_y + (16.0 if has_divider else 12.0)

    # 5. Running Headers & Footers on Subsequent Pages
    other_pages_content_top = max(border_inset_top + 16.0 if has_border else 38.0, 38.0)
    running_header_text = None
    running_header_font_size = 9.0
    has_running_header_line = False
    running_header_line_y = 34.0
    running_header_line_color = (0.8, 0.83, 0.88)
    has_running_footer_line = False
    running_footer_line_y = page_h - 32.0

    if len(doc) > 1:
        p1 = doc[1]
        # Check drawings for horizontal rule in top or bottom margin
        for d in p1.get_drawings():
            for item in d.get("items", []):
                if item[0] == "l":
                    p1_pt, p2_pt = item[1], item[2]
                    if abs(p1_pt.y - p2_pt.y) <= 2.0 and abs(p1_pt.x - p2_pt.x) > page_w * 0.40 and p1_pt.y <= 45.0:
                        other_pages_content_top = max(other_pages_content_top, p1_pt.y + 10.0)
                        has_running_header_line = True
                        running_header_line_y = p1_pt.y
                        if d.get("color"):
                            running_header_line_color = d.get("color")
                    elif abs(p1_pt.y - p2_pt.y) <= 2.0 and abs(p1_pt.x - p2_pt.x) > page_w * 0.40 and p1_pt.y >= page_h - 45.0:
                        has_running_footer_line = True
                        running_footer_line_y = p1_pt.y

        for b in p1.get_text("blocks"):
            x0, y0, x1, y1, text, bno, btype = b
            cleaned = text.strip()
            if btype == 0 and cleaned:
                is_sec = bool(SECTION_PATTERN.match(cleaned))
                is_q = bool(re.match(r"^\s*(?:[A-Z]\.|\d+[\.\)]|\([0-9a-zA-Z]+\)|Q\d+[:\.])\s+", cleaned))
                # Running header at top must NOT be a section or question, and must be in top margin band (y1 <= 42.0)
                if not is_sec and not is_q and y1 <= 42.0:
                    other_pages_content_top = max(other_pages_content_top, y1 + 10.0)
                    running_header_text = cleaned
                    running_header_font_size = min(max(round(y1 - y0, 1), 7.5), 11.0)
                # Running footer at bottom
                if y0 >= page_h * 0.90:
                    content_bottom = min(content_bottom, y0 - 10.0)

    return {
        "page_width": page_w,
        "page_height": page_h,
        "has_border": has_border,
        "border_inset_left": border_inset_left,
        "border_inset_top": border_inset_top,
        "border_inset_right": border_inset_right,
        "border_inset_bottom": border_inset_bottom,
        "border_color": border_color,
        "border_width": border_width,
        "has_divider": has_divider,
        "header_divider_y": header_divider_y,
        "header_bottom_y": header_bottom_y,
        "content_left": content_left,
        "content_right": content_right,
        "content_width": content_right - content_left,
        "p0_content_top": p0_content_top,
        "other_pages_content_top": other_pages_content_top,
        "content_bottom": content_bottom,
        "running_header_text": running_header_text,
        "running_header_font_size": running_header_font_size,
        "has_running_header_line": has_running_header_line,
        "running_header_line_y": running_header_line_y,
        "running_header_line_color": running_header_line_color,
        "has_running_footer_line": has_running_footer_line,
        "running_footer_line_y": running_footer_line_y,
    }


def modify_pdf_template(
    template_path: Path,
    sections: List[Section],
    config: PaperConfig,
    reference_style: Optional[ReferenceAnalysis],
    out_path: Path
) -> Tuple[Path, int]:
    """
    Modifies the uploaded reference PDF directly in-place:
    1. Preserves all vector graphics (outer rectangular border, divider rules, backgrounds).
    2. Preserves images (school/institution logo emblem in its exact location).
    3. Retains header typography and alignment (only updating customized subject/school fields).
    4. Redacts only the questions and sections within the detected content area.
    5. Dynamically renders new sections and questions matching the reference typography and geometry.
    6. Trims unused trailing pages or dynamically appends new pages that preserve template borders.
    """
    doc = fitz.open(str(template_path))
    initial_page_count = len(doc)
    if initial_page_count == 0:
        raise ValueError(f"Reference template PDF '{template_path}' contains 0 pages.")

    geom = analyze_template_geometry(doc, reference_style)
    p0 = doc[0]
    page_w = geom["page_width"]
    page_h = geom["page_height"]
    header_bottom_y = geom["header_bottom_y"]

    # 1. Header Line Updates (Only if user explicitly provided customized school or subject/class)
    p0_blocks = p0.get_text("blocks")
    grade_subject_pattern = re.compile(r"^\s*(grade|class|standard|std)\s*\d+.*$", re.IGNORECASE)

    new_class_str = config.semester_class.strip() if config.semester_class else ""
    new_subj_str = config.subject_name.strip() if config.subject_name else ""

    for b in p0_blocks:
        x0, y0, x1, y1, text, bno, btype = b
        cleaned_text = text.strip()

        # Grade / Subject heading replacement
        if y0 < header_bottom_y and (new_class_str or new_subj_str):
            if grade_subject_pattern.match(cleaned_text):
                parts = []
                if new_class_str:
                    parts.append(new_class_str)
                if new_subj_str:
                    parts.append(new_subj_str.upper())
                replacement_line = " · ".join(parts)
                if replacement_line.lower() != cleaned_text.lower():
                    # Redact only this specific line's bounding box
                    p0.add_redact_annot(fitz.Rect(x0 - 2, y0 - 1, x1 + 2, y1 + 1))
                    p0.apply_redactions()
                    # Reinsert line centered with bold
                    font_params = get_font_params("helv", is_bold=True)
                    line_font_sz = max(min(round(y1 - y0, 1) - 2.0, 16.0), 11.0)
                    p0.insert_textbox(
                        fitz.Rect(geom["content_left"], y0 - 2, geom["content_right"], y1 + 10),
                        replacement_line,
                        fontsize=line_font_sz,
                        color=(0, 0, 0),
                        align=fitz.TEXT_ALIGN_CENTER,
                        **font_params
                    )

        # Institution Name replacement if explicitly changed by user
        if y0 < header_bottom_y and config.institution_name:
            if any(term in cleaned_text.lower() for term in ["school", "college", "institution", "university"]):
                if config.institution_name.strip().lower() != cleaned_text.lower():
                    p0.add_redact_annot(fitz.Rect(x0 - 2, y0 - 1, x1 + 2, y1 + 1))
                    p0.apply_redactions()
                    font_params = get_font_params("helv", is_bold=True)
                    line_font_sz = max(min(round(y1 - y0, 1) - 2.0, 17.0), 12.0)
                    p0.insert_textbox(
                        fitz.Rect(geom["content_left"], y0 - 2, geom["content_right"], y1 + 10),
                        config.institution_name.strip().upper(),
                        fontsize=line_font_sz,
                        color=(0, 0, 0),
                        align=fitz.TEXT_ALIGN_CENTER,
                        **font_params
                    )

    # 2. Redact content text blocks on Page 0 (strictly below header bottom boundary)
    p0_blocks = [b for b in p0.get_text("blocks") if b[6] == 0]
    if (reference_style and reference_style.is_scanned) or len(p0_blocks) == 0:
        # Scanned page / raster content: clean white redaction over content bounding box
        p0.add_redact_annot(
            fitz.Rect(geom["content_left"] - 4, geom["p0_content_top"] - 4, geom["content_right"] + 4, geom["content_bottom"] + 4),
            fill=(1, 1, 1)
        )
    else:
        for b in p0_blocks:
            x0, y0, x1, y1, text, bno, btype = b
            if text.strip() and y0 >= (header_bottom_y - 2.0) and y1 <= (geom["content_bottom"] + 15.0):
                p0.add_redact_annot(fitz.Rect(x0 - 1, y0 - 1, x1 + 1, y1 + 1))
    p0.apply_redactions()

    # Redact content text blocks on subsequent pages (between running header and running footer)
    for pno in range(1, len(doc)):
        page = doc[pno]
        page_blocks = [b for b in page.get_text("blocks") if b[6] == 0]
        if (reference_style and reference_style.is_scanned) or len(page_blocks) == 0:
            page.add_redact_annot(
                fitz.Rect(geom["content_left"] - 4, geom["other_pages_content_top"] - 4, geom["content_right"] + 4, geom["content_bottom"] + 4),
                fill=(1, 1, 1)
            )
        else:
            for b in page_blocks:
                x0, y0, x1, y1, text, bno, btype = b
                cleaned = text.strip()
                if cleaned:
                    is_running_header = (y1 <= 42.0 and not SECTION_PATTERN.match(cleaned) and not re.match(r"^\s*\d+[\.\)]", cleaned))
                    is_running_footer = (y0 >= geom["content_bottom"] + 5.0)
                    if not is_running_header and not is_running_footer:
                        page.add_redact_annot(fitz.Rect(x0 - 1, y0 - 1, x1 + 1, y1 + 1))
        page.apply_redactions()


    # 3. Geometry & Typography Configurations
    left_x = geom["content_left"]
    right_x = geom["content_right"]
    content_w = geom["content_width"]
    max_y = geom["content_bottom"]

    font_family = "helv"
    if reference_style and reference_style.primary_font:
        ref_f = reference_style.primary_font.lower()
        if any(term in ref_f for term in ["times", "serif", "roman", "georgia"]):
            font_family = "times"
        elif any(term in ref_f for term in ["courier", "mono", "typewriter"]):
            font_family = "courier"

    font_bold = get_font_params(font_family, is_bold=True)
    font_reg = get_font_params(font_family, is_bold=False)
    font_it = get_font_params(font_family, is_bold=False, is_italic=True)

    # Body font size
    if config.override_font_size:
        primary_font_sz = float(config.override_font_size)
    elif reference_style and reference_style.primary_font_size:
        primary_font_sz = max(min(float(reference_style.primary_font_size), 14.0), 9.0)
    else:
        primary_font_sz = 10.5

    # Heading font size
    if config.override_font_size:
        heading_font_sz = primary_font_sz + 1.5
    elif reference_style and reference_style.heading_font_size:
        heading_font_sz = max(min(float(reference_style.heading_font_size), 16.0), primary_font_sz + 1.0)
    else:
        heading_font_sz = primary_font_sz + 1.5

    # Section Alignment
    sec_align = fitz.TEXT_ALIGN_LEFT
    if reference_style and reference_style.section_style.get("alignment") == "center":
        sec_align = fitz.TEXT_ALIGN_CENTER

    line_h = config.override_line_spacing or max(primary_font_sz * 1.35, 14.0)

    # 4. Dynamic Question & Section placement logic
    match_section_to_page = (len(sections) == initial_page_count and initial_page_count > 1)
    current_page_idx = 0
    current_y = geom["p0_content_top"]

    def ensure_page_space(needed_h: float) -> Tuple[int, float]:
        nonlocal current_page_idx, current_y
        if current_y + needed_h > max_y:
            current_page_idx += 1
            if current_page_idx >= len(doc):
                _add_page_with_template_border(doc, geom)
            current_y = geom["other_pages_content_top"]
        return current_page_idx, current_y

    for sec_idx, sec in enumerate(sections):
        sec_title = clean_section_title(sec.title)
        title_h = heading_font_sz * 1.35 + 8.0
        instr_h = (line_h + 4.0) if sec.instructions else 0.0
        total_sec_hdr_h = title_h + instr_h

        if match_section_to_page and current_page_idx < sec_idx:
            current_page_idx = sec_idx
            while current_page_idx >= len(doc):
                _add_page_with_template_border(doc, geom)
            current_y = geom["other_pages_content_top"] if current_page_idx > 0 else geom["p0_content_top"]
        else:
            # If starting a new section and page is almost full, start section on next page
            if sec_idx > 0 and (current_y + total_sec_hdr_h + 50.0 > max_y):
                current_page_idx += 1
                if current_page_idx >= len(doc):
                    _add_page_with_template_border(doc, geom)
                current_y = geom["other_pages_content_top"]
            else:
                ensure_page_space(total_sec_hdr_h + 20.0)

        page = doc[current_page_idx]

        # Draw Section Title (Bold, unshaded, black)
        title_rect = fitz.Rect(left_x, current_y, right_x, current_y + title_h)
        rc_title = page.insert_textbox(
            title_rect,
            sec_title,
            fontsize=heading_font_sz,
            color=(0, 0, 0),
            align=sec_align,
            **font_bold
        )
        if rc_title < 0:
            title_h += abs(rc_title) + 6.0
            title_rect = fitz.Rect(left_x, current_y, right_x, current_y + title_h)
            page.insert_textbox(
                title_rect,
                sec_title,
                fontsize=heading_font_sz,
                color=(0, 0, 0),
                align=sec_align,
                **font_bold
            )
        current_y += title_h + 4.0

        # Section Instructions (if present)
        if sec.instructions:
            instr_str = sec.instructions.strip()
            if not instr_str.startswith("("):
                instr_str = f"({instr_str})"
            instr_rect = fitz.Rect(left_x, current_y, right_x, current_y + instr_h)
            rc_instr = page.insert_textbox(
                instr_rect,
                instr_str,
                fontsize=max(primary_font_sz - 0.5, 8.5),
                color=(0, 0, 0),
                align=fitz.TEXT_ALIGN_LEFT,
                **font_it
            )
            if rc_instr < 0:
                instr_h += abs(rc_instr) + 6.0
                instr_rect = fitz.Rect(left_x, current_y, right_x, current_y + instr_h)
                page.insert_textbox(
                    instr_rect,
                    instr_str,
                    fontsize=max(primary_font_sz - 0.5, 8.5),
                    color=(0, 0, 0),
                    align=fitz.TEXT_ALIGN_LEFT,
                    **font_it
                )
            current_y += instr_h + 4.0

        # Dynamic spacing calculation based on question count
        q_count = len(sec.questions)
        available_h = max_y - current_y
        if q_count > 0:
            avg_slot = available_h / q_count
            gap = min(max(avg_slot - 32.0, 4.0), 18.0)
        else:
            gap = 8.0

        for q in sec.questions:
            q_num = q.number.strip() if q.number else ""
            clean_text = q.text.strip()
            if q_num and not clean_text.startswith(f"{q_num}."):
                q_text = f"{q_num}. {clean_text}"
            else:
                q_text = clean_text

            # Append marks to question text if present and not already formatted
            if q.marks is not None and not re.search(r"\[\s*\d+[\.\d]*\s*(?:marks?|m)?\s*\]|\(\s*\d+[\.\d]*\s*(?:marks?|m)?\s*\)$", q_text, re.IGNORECASE):
                marks_str = f" [{q.marks:g} marks]" if q.marks != 1 else " [1 mark]"
                q_text = f"{q_text}{marks_str}"

            # Check if matching question with two columns
            if (q.question_type in ["matching", "match_the_following"] or (q.matching_left and q.matching_right)) and (q.matching_left and q.matching_right):
                import random
                approx_chars_per_line = max(int(content_w / (primary_font_sz * 0.52)), 40)
                q_lines = max(1, (len(q_text) + approx_chars_per_line - 1) // approx_chars_per_line)
                q_h = max(q_lines * line_h, line_h + 2.0)
                ensure_page_space(q_h + 30.0)
                page = doc[current_page_idx]
                q_rect = fitz.Rect(left_x, current_y, right_x, current_y + q_h)
                page.insert_textbox(q_rect, q_text, fontsize=primary_font_sz, color=(0, 0, 0), **font_reg)
                current_y += q_h + 4.0

                right_items = list(q.matching_right)
                if q.shuffle_right:
                    seed = sum(ord(c) for c in (q.id or "matching_seed"))
                    random.Random(seed).shuffle(right_items)

                col_w = (content_w - 20.0) / 2.0
                hdr_h = line_h + 4.0
                ensure_page_space(hdr_h)
                page = doc[current_page_idx]
                page.insert_textbox(
                    fitz.Rect(left_x + 10.0, current_y, left_x + 10.0 + col_w, current_y + hdr_h),
                    "Column A",
                    fontsize=primary_font_sz,
                    color=(0, 0, 0),
                    **font_bold
                )
                page.insert_textbox(
                    fitz.Rect(left_x + 20.0 + col_w, current_y, right_x - 10.0, current_y + hdr_h),
                    "Column B",
                    fontsize=primary_font_sz,
                    color=(0, 0, 0),
                    **font_bold
                )
                current_y += hdr_h + 2.0

                for l_item, r_item in zip(q.matching_left, right_items):
                    l_str = str(l_item).strip()
                    r_str = str(r_item).strip()
                    row_lines = max(
                        (len(l_str) + 30) // 30,
                        (len(r_str) + 30) // 30,
                        1
                    )
                    row_h = max(row_lines * line_h + 2.0, 18.0)
                    ensure_page_space(row_h)
                    page = doc[current_page_idx]

                    page.insert_textbox(
                        fitz.Rect(left_x + 10.0, current_y, left_x + 10.0 + col_w, current_y + row_h),
                        l_str,
                        fontsize=primary_font_sz,
                        color=(0, 0, 0),
                        **font_reg
                    )
                    page.insert_textbox(
                        fitz.Rect(left_x + 20.0 + col_w, current_y, right_x - 10.0, current_y + row_h),
                        r_str,
                        fontsize=primary_font_sz,
                        color=(0, 0, 0),
                        **font_reg
                    )
                    current_y += row_h + 2.0

                current_y += gap * 0.35
                continue

            elif q.is_matching or (q.matching_col_a and q.matching_col_b):
                row_h = max(line_h + 4.0, 20.0)
                ensure_page_space(row_h)
                page = doc[current_page_idx]

                col_w = content_w / 2.0
                col_a_text = f"{q_num}. {q.matching_col_a or q.text}".strip()
                page.insert_textbox(
                    fitz.Rect(left_x + 14.0, current_y, left_x + col_w - 8.0, current_y + row_h),
                    col_a_text,
                    fontsize=primary_font_sz,
                    color=(0, 0, 0),
                    **font_reg
                )
                col_b_text = str(q.matching_col_b or "").strip()
                page.insert_textbox(
                    fitz.Rect(left_x + col_w + 8.0, current_y, right_x - 14.0, current_y + row_h),
                    col_b_text,
                    fontsize=primary_font_sz,
                    color=(0, 0, 0),
                    **font_reg
                )
                current_y += row_h + (gap * 0.35)
                continue

            # Estimate question text lines and height
            approx_chars_per_line = max(int(content_w / (primary_font_sz * 0.52)), 40)
            q_lines = max(1, (len(q_text) + approx_chars_per_line - 1) // approx_chars_per_line)
            q_h = max(q_lines * line_h, line_h + 2.0)

            # Estimate options height and formatting
            opt_h = 0.0
            options_str = ""
            if q.options:
                single_line_candidate = "    ".join(q.options)
                # Check if all options fit on a single line
                if len("    " + single_line_candidate) <= int(approx_chars_per_line * 0.92):
                    options_str = "    " + single_line_candidate
                    opt_h = max(line_h * 1.35, 20.0)
                else:
                    # Check if 2 columns (2 options per line) fits
                    max_opt_len = max(len(o) for o in q.options)
                    col_capacity = approx_chars_per_line // 2
                    if max_opt_len <= col_capacity - 4:
                        pairs = []
                        for i in range(0, len(q.options), 2):
                            row_opts = q.options[i:i+2]
                            if len(row_opts) == 2:
                                pairs.append(f"    {row_opts[0]:<{col_capacity}} {row_opts[1]}")
                            else:
                                pairs.append(f"    {row_opts[0]}")
                        options_str = "\n".join(pairs)
                        opt_lines = len(pairs)
                        opt_h = max(opt_lines * line_h + 6.0, 22.0)
                    else:
                        # Stacked 1 option per line with line-wrapping estimation
                        opt_lines = 0
                        opt_lines_list = []
                        for o in q.options:
                            o_lines = max(1, (len(o) + approx_chars_per_line - 5) // approx_chars_per_line)
                            opt_lines += o_lines
                            opt_lines_list.append("    " + o)
                        options_str = "\n".join(opt_lines_list)
                        opt_h = max(opt_lines * line_h + 8.0, 22.0)

            total_item_h = q_h + opt_h

            ensure_page_space(total_item_h)
            page = doc[current_page_idx]

            q_rect = fitz.Rect(left_x, current_y, right_x, current_y + q_h)
            rc = page.insert_textbox(q_rect, q_text, fontsize=primary_font_sz, color=(0, 0, 0), **font_reg)
            if rc < 0:
                extra_h = abs(rc) + 6.0
                q_h += extra_h
                q_rect = fitz.Rect(left_x, current_y, right_x, current_y + q_h)
                page.insert_textbox(q_rect, q_text, fontsize=primary_font_sz, color=(0, 0, 0), **font_reg)

            current_y += q_h

            # Draw options safely without clipping
            if options_str:
                ensure_page_space(opt_h)
                page = doc[current_page_idx]
                opt_rect = fitz.Rect(left_x, current_y, right_x, current_y + opt_h)
                rc_opt = page.insert_textbox(opt_rect, options_str, fontsize=primary_font_sz, color=(0, 0, 0), **font_reg)
                if rc_opt < 0:
                    extra_h = abs(rc_opt) + 8.0
                    opt_h += extra_h
                    opt_rect = fitz.Rect(left_x, current_y, right_x, current_y + opt_h)
                    page.insert_textbox(opt_rect, options_str, fontsize=primary_font_sz, color=(0, 0, 0), **font_reg)
                current_y += opt_h

            # Draw subquestions if present
            if q.subquestions:
                for sq in q.subquestions:
                    sq_lbl = (sq.label or "").strip()
                    sq_txt = (sq.text or "").strip()
                    sq_line = f"    {sq_lbl} {sq_txt}"
                    if sq.marks is not None and not re.search(r"\[\s*\d+[\.\d]*\s*(?:marks?|m)?\s*\]|\(\s*\d+[\.\d]*\s*(?:marks?|m)?\s*\)$", sq_line, re.IGNORECASE):
                        sq_line += f" [{sq.marks:g} marks]" if sq.marks != 1 else " [1 mark]"

                    sq_lines = max(1, (len(sq_line) + approx_chars_per_line - 1) // approx_chars_per_line)
                    sq_h = max(sq_lines * line_h + 4.0, 18.0)

                    ensure_page_space(sq_h)
                    page = doc[current_page_idx]
                    sq_rect = fitz.Rect(left_x, current_y, right_x, current_y + sq_h)
                    rc_sq = page.insert_textbox(sq_rect, sq_line, fontsize=primary_font_sz, color=(0, 0, 0), **font_reg)
                    if rc_sq < 0:
                        sq_h += abs(rc_sq) + 6.0
                        sq_rect = fitz.Rect(left_x, current_y, right_x, current_y + sq_h)
                        page.insert_textbox(sq_rect, sq_line, fontsize=primary_font_sz, color=(0, 0, 0), **font_reg)
                    current_y += sq_h + 2.0

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

                    ratio = min(max(float(q.image_width_ratio or 0.65), 0.25), 0.95)
                    max_w = content_w * ratio
                    max_h = 240.0
                    dw, dh = get_image_display_dimensions(orig_w, orig_h, max_w, max_h)

                    ensure_page_space(dh + 15.0)
                    page = doc[current_page_idx]
                    img_x0 = left_x + (content_w - dw) / 2.0
                    page.insert_image(
                        fitz.Rect(img_x0, current_y, img_x0 + dw, current_y + dh),
                        stream=png_bytes
                    )
                    current_y += dh + 4.0

                    if q.image_caption:
                        cap_h = line_h + 2.0
                        ensure_page_space(cap_h)
                        page = doc[current_page_idx]
                        page.insert_textbox(
                            fitz.Rect(left_x, current_y, right_x, current_y + cap_h),
                            f"Figure: {q.image_caption}",
                            fontsize=max(primary_font_sz - 1.0, 8.0),
                            color=(0.2, 0.2, 0.2),
                            align=fitz.TEXT_ALIGN_CENTER,
                            **font_it
                        )
                        current_y += cap_h + 2.0

                    if q.diagram_markers and q.diagram_mode == "numbered_markers":
                        blank_lines_count = (len(q.diagram_markers) + 1) // 2
                        blank_h = blank_lines_count * (line_h + 4.0) + 6.0
                        ensure_page_space(blank_h)
                        page = doc[current_page_idx]
                        half_w = (content_w - 20.0) / 2.0
                        for m_idx, marker in enumerate(q.diagram_markers, 1):
                            m_num = getattr(marker, "number", marker.get("number", m_idx) if isinstance(marker, dict) else m_idx)
                            r_idx = (m_idx - 1) // 2
                            c_idx = (m_idx - 1) % 2
                            bx0 = left_x + 10.0 if c_idx == 0 else left_x + 20.0 + half_w
                            by0 = current_y + r_idx * (line_h + 4.0)
                            page.insert_textbox(
                                fitz.Rect(bx0, by0, bx0 + half_w, by0 + line_h + 2.0),
                                f"({m_num}) ______________________",
                                fontsize=primary_font_sz,
                                color=(0, 0, 0),
                                **font_reg
                            )
                        current_y += blank_h + 4.0
                except Exception as img_err:
                    print(f"[PDF Template Modifier] Warning: failed to insert image for question: {img_err}")

            current_y += gap

    # Trim unused trailing pages if replacement content took fewer pages than original template
    while len(doc) > current_page_idx + 1:
        doc.delete_page(len(doc) - 1)

    # Ensure parent output directory exists
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    final_page_count = len(doc)
    doc.close()

    return out_path, final_page_count

def _add_page_with_template_border(doc: fitz.Document, geom: Dict[str, Any]):
    """
    Adds a new page to the document that replicates the identical page dimensions
    and outer border of the reference template.
    """
    page_w = geom["page_width"]
    page_h = geom["page_height"]
    new_page = doc.new_page(width=page_w, height=page_h)

    # Draw border rectangle only if template actually has an outer border
    if geom.get("has_border"):
        inset_l = geom.get("border_inset_left", 25.0)
        inset_t = geom.get("border_inset_top", 25.0)
        inset_r = geom.get("border_inset_right", 25.0)
        inset_b = geom.get("border_inset_bottom", 25.0)
        b_rect = fitz.Rect(inset_l, inset_t, page_w - inset_r, page_h - inset_b)
        color = geom.get("border_color", (0, 0, 0))
        width = geom.get("border_width", 1.0)
        new_page.draw_rect(b_rect, color=color, width=width)

    # Draw running header text if present
    if geom.get("running_header_text"):
        font_params = get_font_params("helv", is_bold=False)
        hdr_rect = fitz.Rect(geom["content_left"], 18.0, geom["content_right"], geom["other_pages_content_top"] - 4.0)
        new_page.insert_textbox(
            hdr_rect,
            geom["running_header_text"],
            fontsize=geom.get("running_header_font_size", 9.0),
            color=(0.28, 0.33, 0.41),
            **font_params
        )

    # Draw running header horizontal line if present
    if geom.get("has_running_header_line"):
        line_y = geom.get("running_header_line_y", 34.0)
        p1 = fitz.Point(geom["content_left"], line_y)
        p2 = fitz.Point(geom["content_right"], line_y)
        new_page.draw_line(p1, p2, color=geom.get("running_header_line_color", (0.8, 0.83, 0.88)), width=0.6)

    # Draw running footer line if present
    if geom.get("has_running_footer_line"):
        footer_line_y = geom.get("running_footer_line_y", page_h - 32.0)
        p1 = fitz.Point(geom["content_left"], footer_line_y)
        p2 = fitz.Point(geom["content_right"], footer_line_y)
        new_page.draw_line(p1, p2, color=(0.8, 0.83, 0.88), width=0.5)

