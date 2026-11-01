try:
    import pymupdf as fitz
except ImportError:
    import fitz
import base64
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from collections import Counter
import re
from ..models.schemas import ReferenceAnalysis, FontDetail, HeaderLine

PAGE_SIZES_PT = {
    "A4": (595.28, 841.89),
    "Letter": (612.0, 792.0),
    "Legal": (612.0, 1008.0),
    "A3": (841.89, 1190.55),
    "A5": (419.53, 595.28)
}

def identify_page_size_name(width: float, height: float) -> str:
    w, h = min(width, height), max(width, height)
    for name, (sw, sh) in PAGE_SIZES_PT.items():
        if abs(w - sw) < 15 and abs(h - sh) < 15:
            return name
    return f"Custom ({width:.1f}x{height:.1f} pt)"

SECTION_PATTERN = re.compile(
    r"^\s*(?:###\s*)?(?:(?:[A-Z]\.|\([A-Z]\)|(?:PART|SECTION|MODULE|UNIT|GROUP)\s+[A-Z0-9IVXLCDM]+))\s+([A-Z\s\-_/]+)$",
    re.IGNORECASE
)
section_pattern = SECTION_PATTERN


MCQ_INLINE_PATTERN = re.compile(
    r"(?:\b[a-d]\)|\([a-d]\))\s+.*?(?:\b[b-d]\)|\([b-d]\))",
    re.IGNORECASE
)

def analyze_reference_pdf(pdf_path: Path) -> ReferenceAnalysis:
    warnings: List[str] = []
    
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        warnings.append(f"Could not open PDF file: {str(e)}")
        return ReferenceAnalysis(warnings=warnings)

    page_count = len(doc)
    if page_count == 0:
        doc.close()
        return ReferenceAnalysis(page_count=0, warnings=["PDF has 0 pages."])

    first_page = doc[0]
    p_rect = first_page.rect
    width = float(p_rect.width)
    height = float(p_rect.height)
    page_size_name = identify_page_size_name(width, height)

    total_text_length = 0
    font_counter = Counter()
    font_size_counter = Counter()
    bold_counter = Counter()
    italic_counter = Counter()

    # Bounding box aggregates for margin estimation
    min_x0 = width
    min_y0 = height
    max_x1 = 0.0
    max_y1 = 0.0

    header_candidates: List[str] = []
    footer_candidates: List[str] = []
    has_page_numbers = False
    footer_has_line = False

    page_num_regex = re.compile(r"^\s*(page\s*)?[-–—]?\s*\d+(\s*(of|/)\s*\d+)?\s*[-–—]?\s*$", re.IGNORECASE)

    # 1. Detect Page Border
    has_page_border = False
    border_inset_pt = 25.0
    border_width_pt = 1.2
    border_color_hex = "#000000"

    drawings = first_page.get_drawings()
    for d in drawings:
        r = d.get("rect")
        if r:
            rx0, ry0, rx1, ry1 = r
            r_w = rx1 - rx0
            r_h = ry1 - ry0
            # Check if this drawing is an enclosing outer border
            if rx0 <= 45 and ry0 <= 45 and (width - rx1) <= 45 and (height - ry1) <= 45:
                if r_w > width * 0.8 and r_h > height * 0.8:
                    has_page_border = True
                    border_inset_pt = round(min(rx0, ry0), 1)
                    border_width_pt = max(round(d.get("width", 1.0), 1), 0.8)
                    stroke_c = d.get("color")
                    if stroke_c and len(stroke_c) == 3:
                        r_col, g_col, b_col = [int(c * 255) for c in stroke_c]
                        border_color_hex = f"#{r_col:02x}{g_col:02x}{b_col:02x}"
                    break

    # 2. Detect First Content Item and Horizontal Divider Rule below Header on Page 1
    p0_dict = first_page.get_text("dict")
    first_content_y = None
    for b in p0_dict.get("blocks", []):
        if b.get("type") == 0:
            bx0, by0, bx1, by1 = b.get("bbox", (0, 0, 0, 0))
            b_text = " ".join("".join(s.get("text", "") for s in l.get("spans", [])) for l in b.get("lines", [])).strip()
            if SECTION_PATTERN.match(b_text) or re.match(r"^\s*(?:[A-Z]\.|\d+[\.\)]|\([0-9a-zA-Z]+\)|Q\d+[:\.])\s+", b_text):
                if by0 > 40:
                    if first_content_y is None or by0 < first_content_y:
                        first_content_y = by0

    has_header_divider = False
    header_divider_y = height * 0.25
    for d in drawings:
        r = d.get("rect")
        if r:
            rx0, ry0, rx1, ry1 = r
            r_w = rx1 - rx0
            r_h = ry1 - ry0
            # Horizontal rule: wide width (> 50% page width), small height (<= 5pt), in top 38% of page
            if r_w > width * 0.50 and r_h <= 5.0 and (35.0 <= ry0 <= height * 0.38):
                has_header_divider = True
                header_divider_y = min(header_divider_y, ry0)
        for item in d.get("items", []):
            if item[0] == "l":
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) <= 2.5 and abs(p1.x - p2.x) > width * 0.50 and (35.0 <= p1.y <= height * 0.38):
                    has_header_divider = True
                    header_divider_y = min(header_divider_y, p1.y)

    # 3. Detect Header Logo Image on Page 1
    header_logo_base64 = None
    header_logo_w = 70.0
    header_logo_h = 40.0

    try:
        page1_images = first_page.get_images(full=True)
        if page1_images:
            for img_info in page1_images:
                xref = img_info[0]
                try:
                    img_rects = first_page.get_image_rects(xref)
                    for irect in img_rects:
                        # Check if near top center of page
                        if irect.y1 <= height * 0.25 and abs((irect.x0 + irect.x1) / 2 - width / 2) < 120:
                            pix = fitz.Pixmap(doc, xref)
                            if pix.n >= 5: # CMYK
                                pix = fitz.Pixmap(fitz.csRGB, pix)
                            img_png_bytes = pix.tobytes("png")
                            header_logo_base64 = base64.b64encode(img_png_bytes).decode("utf-8")
                            header_logo_w = min(max(round(irect.width, 1), 30.0), 180.0)
                            header_logo_h = min(max(round(irect.height, 1), 20.0), 100.0)
                            break
                    if header_logo_base64:
                        break
                except Exception:
                    pass
    except Exception:
        pass

    # 4. Extract Text blocks, Fonts, and Header Lines
    header_lines: List[HeaderLine] = []
    matching_columns_detected = False
    option_layout = "inline"
    has_metadata_box = False
    detected_sections = set()
    detected_q_count = 0

    # Collect header blocks before the first section or horizontal divider
    if has_header_divider and (first_content_y is None or header_divider_y <= first_content_y):
        header_max_y = header_divider_y - 2.0
    elif first_content_y is not None:
        header_max_y = first_content_y - 4.0
    else:
        header_max_y = header_divider_y if has_header_divider else (height * 0.20)

    for p_idx in range(page_count):
        page = doc[p_idx]
        text_page = page.get_text("dict")
        page_text = page.get_text("text").strip()
        total_text_length += len(page_text)

        blocks = text_page.get("blocks", [])
        for b in blocks:
            if b.get("type") == 0:  # text block
                bbox = b.get("bbox", (0, 0, 0, 0))
                bx0, by0, bx1, by1 = bbox
                
                block_lines_text = []
                for line in b.get("lines", []):
                    line_text = ""
                    lx0, ly0, lx1, ly1 = line.get("bbox", (0, 0, 0, 0))
                    max_span_size = 10.0
                    is_line_bold = False

                    for span in line.get("spans", []):
                        stext = span.get("text", "").strip()
                        if stext:
                            line_text += (" " if line_text else "") + stext
                            font_name = span.get("font", "Helvetica")
                            font_size = round(span.get("size", 10.0), 1)
                            max_span_size = max(max_span_size, font_size)
                            flags = span.get("flags", 0)
                            is_b = bool(flags & 2) or ("bold" in font_name.lower())
                            if is_b:
                                is_line_bold = True
                            is_i = bool(flags & 1) or ("italic" in font_name.lower() or "oblique" in font_name.lower())

                            clean_font_name = font_name.split("+")[-1]
                            font_counter[clean_font_name] += 1
                            font_size_counter[font_size] += 1
                            if is_b:
                                bold_counter[clean_font_name] += 1
                            if is_i:
                                italic_counter[clean_font_name] += 1

                    line_text = line_text.strip()
                    if line_text:
                        block_lines_text.append(line_text)

                        # Check if this line is in the header region of Page 1
                        is_sec = bool(SECTION_PATTERN.match(line_text))
                        is_q = bool(re.match(r"^\s*\d+[\.\)]", line_text))
                        if is_sec:
                            detected_sections.add(line_text)
                        if is_q:
                            detected_q_count += 1

                        if p_idx == 0 and ly1 <= header_max_y and not is_sec and not is_q:
                            line_mid = (lx0 + lx1) / 2
                            alignment = "center" if abs(line_mid - width / 2) < 55 else ("right" if lx0 > width * 0.55 else "left")
                            # Avoid duplicate consecutive header lines
                            if not any(hl.text == line_text for hl in header_lines):
                                header_lines.append(HeaderLine(
                                    text=line_text,
                                    font_size=max_span_size,
                                    is_bold=is_line_bold,
                                    alignment=alignment,
                                    y_offset=round(ly0, 1)
                                ))

                        # Check for matching columns
                        if "column a" in line_text.lower() and "column b" in line_text.lower():
                            matching_columns_detected = True

                        # Check for inline MCQs
                        if MCQ_INLINE_PATTERN.search(line_text):
                            option_layout = "inline"

                        # Check for metadata box tokens (Subject:, Semester:, Max Marks:)
                        if any(term in line_text.lower() for term in ["semester", "max marks", "maximum marks", "subject code"]):
                            has_metadata_box = True

                full_block_text = " ".join(block_lines_text).strip()
                if full_block_text:
                    if by0 > 20 and by1 < height - 20:
                        min_x0 = min(min_x0, max(bx0, 0))
                        min_y0 = min(min_y0, max(by0, 0))
                        max_x1 = max(max_x1, min(bx1, width))
                        max_y1 = max(max_y1, min(by1, height))

                    # Header candidate
                    if by1 <= height * 0.14 and len(full_block_text) > 3:
                        header_candidates.append(full_block_text)

                    # Footer candidate
                    if by0 >= height * 0.90 and len(full_block_text) > 0:
                        footer_candidates.append(full_block_text)
                        if page_num_regex.match(full_block_text):
                            has_page_numbers = True

    is_scanned = False
    text_density = total_text_length / max(page_count, 1)
    if text_density < 60:
        has_images = any(len(doc[p].get_images()) > 0 for p in range(min(page_count, 3)))
        if has_images or text_density < 20:
            is_scanned = True
            warnings.append(
                "This reference PDF appears to be a scanned document or image-based PDF. "
                "Template background preservation and OCR-guided layout alignment will be applied."
            )
            # Image-based outer border check using Pillow
            try:
                from PIL import Image
                import io
                pix = first_page.get_pixmap(dpi=72)
                img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
                iw, ih = img.size
                top_samples = [img.getpixel((x, int(ih * 0.04))) < 80 for x in range(int(iw * 0.2), int(iw * 0.8))]
                bot_samples = [img.getpixel((x, int(ih * 0.96))) < 80 for x in range(int(iw * 0.2), int(iw * 0.8))]
                if sum(top_samples) > len(top_samples) * 0.4 and sum(bot_samples) > len(bot_samples) * 0.4:
                    has_page_border = True
            except Exception:
                pass


    doc.close()

    # Margins
    if min_x0 < width and max_x1 > 0 and min_y0 < height and max_y1 > 0:
        # If page border exists, margin is distance inside the border
        left_margin = max(round(min_x0, 1), 35.0)
        right_margin = max(round(width - max_x1, 1), 35.0)
        top_margin = max(round(min_y0, 1), 30.0)
        bottom_margin = max(round(height - max_y1, 1), 30.0)
    else:
        left_margin, right_margin, top_margin, bottom_margin = 40.0, 40.0, 35.0, 35.0

    # Fonts
    detected_fonts_list: List[FontDetail] = []
    for fname, count in font_counter.most_common(5):
        is_b = bold_counter[fname] > (count * 0.25)
        is_i = italic_counter[fname] > (count * 0.25)
        detected_fonts_list.append(FontDetail(
            name=fname,
            size=10.0,
            is_bold=is_b,
            is_italic=is_i,
            count=count
        ))

    primary_font = "Helvetica"
    if font_counter:
        top_font = font_counter.most_common(1)[0][0]
        lower_top = top_font.lower()
        if "times" in lower_top or "roman" in lower_top:
            primary_font = "Times-Roman"
        elif "courier" in lower_top or "mono" in lower_top:
            primary_font = "Courier"
        elif "arial" in lower_top or "calibri" in lower_top or "helvetica" in lower_top or "sans" in lower_top:
            primary_font = "Helvetica"
        else:
            primary_font = "Helvetica"

    primary_font_size = 10.0
    heading_font_size = 11.5
    if font_size_counter:
        sizes = [s for s, _ in font_size_counter.most_common(10)]
        body_sizes = [s for s in sizes if 8.5 <= s <= 13.5]
        primary_font_size = float(body_sizes[0]) if body_sizes else float(sizes[0])
        primary_font_size = round(max(min(primary_font_size, 14.0), 9.0), 1)
        larger_sizes = [s for s in sizes if s > primary_font_size and s <= 18.0]
        heading_font_size = float(min(larger_sizes)) if larger_sizes else round(primary_font_size + 1.5, 1)

    # Determine document type (deterministic rule-based with optional AI classification)
    all_header_text = " ".join(hl.text for hl in header_lines).lower()
    if "worksheet" in all_header_text or "practice" in all_header_text or (not has_metadata_box and has_page_border):
        document_type = "worksheet"
    elif has_metadata_box:
        document_type = "exam_paper"
    else:
        document_type = "worksheet" if has_page_border else "standard"

    # Optional AI assistance for ambiguous document classification
    try:
        from .cloud_llm import ai_classify_document_header
        ai_res = ai_classify_document_header([hl.text for hl in header_lines])
        if ai_res and ai_res.get("document_type") in ("worksheet", "exam_paper"):
            document_type = ai_res["document_type"]
    except Exception:
        pass

    raw_summary = (
        f"Detected {page_count} page(s) ({page_size_name}) as '{document_type.upper()}'. "
        f"Page border: {'YES' if has_page_border else 'No'} (inset: {border_inset_pt}pt). "
        f"Header logo: {'YES' if header_logo_base64 else 'No'}. "
        f"Divider rule: {'YES' if has_header_divider else 'No'}. "
        f"Primary typography: {primary_font} ({primary_font_size}pt). "
        f"Header lines detected: {len(header_lines)}."
    )

    return ReferenceAnalysis(
        page_count=page_count,
        page_size=page_size_name,
        page_width_pt=round(width, 2),
        page_height_pt=round(height, 2),
        margins={
            "top": top_margin,
            "bottom": bottom_margin,
            "left": left_margin,
            "right": right_margin
        },
        detected_fonts=detected_fonts_list,
        primary_font=primary_font,
        primary_font_size=primary_font_size,
        heading_font_size=heading_font_size,
        has_header=bool(header_lines),
        header_text=header_lines[0].text if header_lines else None,
        has_footer=has_page_numbers,
        footer_text=None,
        has_page_numbers=has_page_numbers,
        is_scanned=is_scanned,
        text_density=round(text_density, 2),
        columns_detected=1,
        warnings=warnings,
        raw_summary=raw_summary,

        # Layout Engine Specifications
        document_type=document_type,
        has_page_border=has_page_border,
        border_inset_pt=border_inset_pt,
        border_width_pt=border_width_pt,
        border_color_hex=border_color_hex,
        header_lines=header_lines,
        has_header_divider=has_header_divider,
        header_logo_base64=header_logo_base64,
        header_logo_width=header_logo_w,
        header_logo_height=header_logo_h,
        has_metadata_box=has_metadata_box,
        section_style={
            "has_background": False if document_type == "worksheet" else True,
            "font_size": heading_font_size,
            "is_bold": True,
            "alignment": "left",
            "space_before": 8.0,
            "space_after": 4.0
        },
        question_style={
            "font_size": primary_font_size,
            "line_spacing": primary_font_size + 3.5,
            "option_layout": option_layout,
            "indent_pt": 0.0
        },
        matching_columns_detected=matching_columns_detected,
        footer_has_line=footer_has_line,
        reference_pdf_path=str(Path(pdf_path).resolve()) if pdf_path else None,
        structural_capacity={
            "estimated_question_slots": max(detected_q_count, page_count * 4),
            "reference_sections_count": max(len(detected_sections), 1),
            "has_fixed_answer_blocks": False,
            "recommended_mode": "extend_template",
            "reference_pages": page_count
        }
    )

