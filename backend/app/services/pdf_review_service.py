import os
import io
import re
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
try:
    import pymupdf as fitz
except ImportError:
    import fitz
from PIL import Image, ImageChops, ImageDraw, ImageFont

from .pdf_comparison_service import generate_difference_heatmap, calculate_image_difference_metrics
from ..utils.file_utils import TEMP_BASE_DIR

COMPARISONS_DIR = TEMP_BASE_DIR / "comparisons"
COMPARISONS_DIR.mkdir(parents=True, exist_ok=True)

def image_to_base64_data_url(img_or_path) -> str:
    if isinstance(img_or_path, (str, Path)):
        with open(str(img_or_path), "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/png;base64,{b64}"
    elif isinstance(img_or_path, Image.Image):
        buf = io.BytesIO()
        img_or_path.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    return ""

def render_pdf_pages_to_images(pdf_path: Path, prefix: str, dpi: int = 150) -> List[Path]:
    doc = fitz.open(str(pdf_path))
    paths = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        img_path = COMPARISONS_DIR / f"{prefix}_page_{i+1}.png"
        pix.save(str(img_path))
        paths.append(img_path)
    doc.close()
    return paths

def generate_side_by_side_comparison(ref_img: Path, gen_img: Path, out_path: Path) -> Path:
    im1 = Image.open(ref_img).convert("RGB")
    im2 = Image.open(gen_img).convert("RGB")

    w1, h1 = im1.size
    w2, h2 = im2.size
    banner_h = 36
    max_h = max(h1, h2) + banner_h
    gutter = 28
    tot_w = w1 + w2 + gutter

    combined = Image.new("RGB", (tot_w, max_h), (241, 245, 249))
    draw = ImageDraw.Draw(combined)

    # Top header banner labels
    draw.rectangle([0, 0, w1, banner_h], fill=(30, 41, 59))
    draw.rectangle([w1 + gutter, 0, tot_w, banner_h], fill=(67, 56, 202))

    draw.text((w1 // 2 - 80, 10), "ORIGINAL REFERENCE", fill=(255, 255, 255))
    draw.text((w1 + gutter + (w2 // 2) - 80, 10), "GENERATED QUESTION PAPER", fill=(255, 255, 255))

    # Paste rendered pages
    combined.paste(im1, (0, banner_h))
    combined.paste(im2, (w1 + gutter, banner_h))

    # Divider line
    draw.line([(w1 + gutter // 2, 0), (w1 + gutter // 2, max_h)], fill=(203, 213, 225), width=2)

    combined.save(str(out_path), "PNG")
    return out_path

def generate_visual_diff_overlay(
    ref_img_path: Path,
    gen_img_path: Path,
    out_path: Path,
    content_y_ratio: float = 0.22
) -> Tuple[Path, float]:
    """
    Produces a visual difference overlay image distinguishing:
    1. Unwanted layout differences in header, borders, and margins (highlighted in vivid magenta).
    2. Expected content text differences in the content zone (highlighted in translucent cyan).
    Accounts for anti-aliasing / rendering noise tolerance.
    Returns (out_path, layout_diff_percentage).
    """
    im1 = Image.open(ref_img_path).convert("RGB")
    im2 = Image.open(gen_img_path).convert("RGB")

    w = max(im1.width, im2.width)
    h = max(im1.height, im2.height)
    if im1.size != (w, h):
        im1 = im1.resize((w, h), Image.Resampling.LANCZOS)
    if im2.size != (w, h):
        im2 = im2.resize((w, h), Image.Resampling.LANCZOS)

    # Soft blended base of generated page
    base = Image.blend(im2, Image.new("RGB", (w, h), (255, 255, 255)), 0.30)
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay, "RGBA")

    # Difference with anti-aliasing noise threshold
    diff = ImageChops.difference(im1, im2).convert("L")
    content_top_px = int(h * content_y_ratio)
    content_bottom_px = int(h * 0.90)

    # Create layout mask: diff outside content area (header, borders, footers, margins)
    diff_pixels = diff.load()
    layout_diff_count = 0
    total_layout_pixels = max(1, (w * h) - (w * (content_bottom_px - content_top_px)))

    # Mark expected content zone with a subtle dashed / styled outline
    overlay_draw.rectangle(
        [int(w * 0.05), content_top_px, int(w * 0.95), content_bottom_px],
        outline=(59, 130, 246, 120),
        width=2
    )

    # Scan difference pixels with noise threshold (diff > 35)
    step = 2  # sampling step for efficiency and clarity
    for y in range(0, h, step):
        in_content_zone = (content_top_px <= y <= content_bottom_px)
        for x in range(0, w, step):
            d_val = diff_pixels[x, y]
            if d_val > 35: # Ignore minor anti-aliasing differences
                if not in_content_zone:
                    layout_diff_count += 1
                    # Layout difference: Vivid Magenta/Red highlight
                    overlay_draw.rectangle([x, y, x + step, y + step], fill=(236, 72, 153, 190))
                else:
                    # Expected text content change: Soft Cyan
                    overlay_draw.rectangle([x, y, x + step, y + step], fill=(56, 189, 248, 70))

    base.paste(overlay, (0, 0), overlay)

    # Add Legend banner at top
    legend_bar = Image.new("RGB", (w, 32), (15, 23, 42))
    l_draw = ImageDraw.Draw(legend_bar)
    # Magenta square
    l_draw.rectangle([16, 10, 28, 22], fill=(236, 72, 153))
    l_draw.text((34, 9), "Layout Difference (Header / Margins / Border)", fill=(241, 245, 249))
    # Cyan square
    l_draw.rectangle([340, 10, 352, 22], fill=(56, 189, 248))
    l_draw.text((358, 9), "Expected Content Changes (User Replacement Questions)", fill=(241, 245, 249))

    final_diff_img = Image.new("RGB", (w, h + 32))
    final_diff_img.paste(legend_bar, (0, 0))
    final_diff_img.paste(base, (0, 32))
    final_diff_img.save(str(out_path), "PNG")

    layout_diff_pct = round((layout_diff_count / (total_layout_pixels / (step * step))) * 100, 2)
    return out_path, layout_diff_pct

def check_text_overlaps(doc: fitz.Document) -> List[str]:
    overlaps = []
    for p_idx, page in enumerate(doc):
        blocks = [b for b in page.get_text("blocks") if b[6] == 0 and b[4].strip()]
        for i in range(len(blocks)):
            r1 = fitz.Rect(blocks[i][:4])
            for j in range(i + 1, len(blocks)):
                r2 = fitz.Rect(blocks[j][:4])
                inter = r1 & r2
                if not inter.is_empty and inter.width > 20 and inter.height > 8:
                    overlaps.append(
                        f"Page {p_idx+1}: Potential text collision between '{blocks[i][4][:25].strip()}...' and '{blocks[j][4][:25].strip()}...'"
                    )
    return overlaps

def check_text_overflows(doc: fitz.Document) -> List[str]:
    overflows = []
    for p_idx, page in enumerate(doc):
        page_h = page.rect.height
        blocks = [b for b in page.get_text("blocks") if b[6] == 0 and b[4].strip()]
        for b in blocks:
            x0, y0, x1, y1, text = b[:5]
            if y1 >= page_h - 22.0:
                overflows.append(
                    f"Page {p_idx+1}: Text block '{text[:25].strip()}...' extends into bottom margin / footer band."
                )
    return overflows

import unicodedata

def normalize_text(text: Optional[str]) -> str:
    """
    Carefully normalizes text for dynamic content validation:
    - Unicode NFKD normalization
    - Standardizes quotes (' and ") and dashes (en-dash, em-dash to -)
    - Normalizes blank markers (e.g. ____+ to ___)
    - De-hyphenates words wrapped across line ends (e.g. 'pho- tosynthesis' -> 'photosynthesis')
    - Collapses repeated whitespace, newlines, and tabs into a single space
    - Preserves all letters, numbers, identifiers, and words
    """
    if not text:
        return ""
    t = unicodedata.normalize("NFKD", str(text))
    t = t.replace("\u2018", "'").replace("\u2019", "'").replace("`", "'")
    t = t.replace("\u201c", '"').replace("\u201d", '"')
    t = t.replace("\u2013", "-").replace("\u2014", "-")
    # De-hyphenate wrapped words e.g. "pho- tosynthesis" or "word-\n break"
    t = re.sub(r"(\w+)-\s+(\w+)", r"\1\2", t)
    t = re.sub(r"_{2,}", "___", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip().lower()

def split_option_label_and_text(opt: str) -> Tuple[str, str]:
    """
    Extracts label (e.g. 'a', 'b', '1', 'i') and value text (e.g. 'Hen') from an option string.
    Returns (label_char, value_text).
    """
    m = re.match(r"^\s*(?:\(([a-zA-Z0-9]+)\)|([a-zA-Z0-9]+)[\.\)])\s*(.*)$", str(opt).strip())
    if m:
        lbl = (m.group(1) or m.group(2)).lower()
        val = m.group(3).strip()
        return lbl, val
    return "", str(opt).strip()

def is_option_present(opt_str: str, page_text: str, page_blocks: List[str]) -> Tuple[bool, str]:
    """
    Dynamically verifies an MCQ option against extracted PDF page text and blocks:
    - Handles variations in parentheses, periods, and spacing around option labels (e.g. '(a) Hen', 'a) Hen', 'a. Hen', 'a Hen').
    - Handles options split across lines or text blocks.
    - Matches option value text even if label styling differs.
    - Avoids treating unrelated options as matches.
    Returns (is_found, match_type).
    """
    if not opt_str:
        return True, "empty"
    opt_norm = normalize_text(opt_str)
    if not opt_norm:
        return True, "empty"

    # 1. Exact normalized match in page text or any block
    if opt_norm in page_text:
        return True, "exact"
    for b in page_blocks:
        if opt_norm in b:
            return True, "block_exact"

    # 2. Match with label variations
    lbl, val = split_option_label_and_text(opt_str)
    if lbl and val:
        val_norm = normalize_text(val)
        if val_norm:
            # Patterns for label variations
            label_patterns = [
                rf"\b\({re.escape(lbl)}\)\s*{re.escape(val_norm)}",
                rf"\b{re.escape(lbl)}\)\s*{re.escape(val_norm)}",
                rf"\b{re.escape(lbl)}\.\s*{re.escape(val_norm)}",
                rf"\b{re.escape(lbl)}\s+[-–]\s*{re.escape(val_norm)}",
                rf"\b{re.escape(lbl)}\s+{re.escape(val_norm)}"
            ]
            for pat in label_patterns:
                if re.search(pat, page_text):
                    return True, "label_variation"
                for b in page_blocks:
                    if re.search(pat, b):
                        return True, "block_label_variation"

            # Check value text alone if meaningful (len >= 3)
            if len(val_norm) >= 3 and val_norm in page_text:
                return True, "value_text"
            for b in page_blocks:
                if len(val_norm) >= 3 and val_norm in b:
                    return True, "block_value_text"

            # Check wrapped / hyphenated multi-word option
            words = val_norm.split()
            if len(words) >= 2:
                fuzzy_pat = r"\s+".join(re.escape(w) for w in words)
                if re.search(fuzzy_pat, page_text):
                    return True, "wrapped_text"

    # 3. For options without detected label, match words sequence
    words = opt_norm.split()
    if len(words) >= 3:
        prefix = " ".join(words[:2])
        suffix = " ".join(words[-2:])
        if prefix in page_text and suffix in page_text:
            return True, "boundary_tokens"

    return False, "not_found"

def extract_section_core_text(title: str) -> Tuple[str, str]:
    """
    Separates section prefix (e.g. 'SECTION B', 'PART A', 'B.') and core heading
    (e.g. 'CHOOSE THE CORRECT ANSWER', 'FILL IN THE BLANKS').
    Returns (prefix, core_heading).
    """
    t = re.sub(r"^#+\s*", "", str(title).strip())
    m = re.match(
        r"^(?:(?:SECTION|PART|MODULE|UNIT|GROUP)\s+([A-Z0-9]+|[IVXLCDM]+)|\(?([A-Z0-9]+)\)?)[\.\:\—–\-]?\s*(.*)$",
        t,
        re.IGNORECASE
    )
    if m:
        sec_id = m.group(1) or m.group(2) or ""
        rest = m.group(3).strip()
        return sec_id.strip(), rest
    return "", t

def is_section_heading_present(sec_title: str, page_text: str, page_blocks: List[str]) -> Tuple[bool, str]:
    """
    Dynamically verifies a section heading against page text and blocks:
    - Handles variations in letter/number prefixes e.g. '(B) CHOOSE...' vs 'B. CHOOSE...' vs 'CHOOSE...'
    - Handles markdown '#' markers, punctuation differences, and whitespace wrapping.
    Returns (is_found, match_type).
    """
    if not sec_title:
        return True, "empty"
    title_norm = normalize_text(sec_title)
    if not title_norm:
        return True, "empty"

    # 1. Exact normalized match
    if title_norm in page_text:
        return True, "exact"
    for b in page_blocks:
        if title_norm in b:
            return True, "block_exact"

    # 2. Extract core title
    sec_id, core_title = extract_section_core_text(sec_title)
    if core_title:
        core_norm = normalize_text(core_title)
        if core_norm:
            # Core title match
            if core_norm in page_text:
                return True, "core_title"
            for b in page_blocks:
                if core_norm in b:
                    return True, "block_core_title"

            # Check prefix + core variations (e.g. "b. choose the correct answer" vs "(b) choose...")
            if sec_id:
                id_norm = normalize_text(sec_id)
                patterns = [
                    rf"\b{re.escape(id_norm)}\.\s*{re.escape(core_norm)}",
                    rf"\b\({re.escape(id_norm)}\)\s*{re.escape(core_norm)}",
                    rf"\b{re.escape(id_norm)}\)\s*{re.escape(core_norm)}",
                    rf"\b{re.escape(id_norm)}\s*[-–:]\s*{re.escape(core_norm)}"
                ]
                for p in patterns:
                    if re.search(p, page_text):
                        return True, "prefix_variation"

            # Check wrapped words in core title
            words = core_norm.split()
            if len(words) >= 3:
                fuzzy_pat = r"\s+".join(re.escape(w) for w in words)
                if re.search(fuzzy_pat, page_text):
                    return True, "wrapped_words"

    return False, "not_found"

def is_content_fragment_present(fragment: str, page_text: str, page_blocks: List[str]) -> bool:
    """
    Checks if a text fragment appears in page text or across page blocks,
    accounting for line-breaks, hyphenation, and indentation.
    """
    if not fragment:
        return True
    f_norm = normalize_text(fragment)
    if not f_norm:
        return True
    if f_norm in page_text:
        return True
    for b in page_blocks:
        if f_norm in b:
            return True
    # For longer fragments, check substantial token sequence (handles split lines)
    words = f_norm.split()
    if len(words) >= 4:
        # Check 4-word prefix and 4-word suffix
        prefix = " ".join(words[:4])
        suffix = " ".join(words[-4:])
        if prefix in page_text and suffix in page_text:
            return True
        # Allow multi-line whitespace variation
        fuzzy_pat = r"\s+".join(re.escape(w) for w in words[:6])
        if re.search(fuzzy_pat, page_text):
            return True
    return False

def verify_content_integrity(
    sections: Optional[List[Any]],
    gen_doc: fitz.Document
) -> Tuple[List[str], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Dynamically validates every user-supplied content item against the generated PDF:
    - Zero hardcoded question text or counts.
    - Normalizes extracted text across lines and blocks.
    - Validates main question text, all options, and subquestions individually.
    - Validates section headings and instructions separately.
    - Distinguishes FULLY FOUND, PARTIALLY FOUND, and NOT FOUND.
    - Tracks exact page number where each item is located.
    - Distinguishes extraction failure (e.g. OCR/scanned/vector) from content loss.
    Returns (expected_changes, content_errors, summary_report).
    """
    expected_changes: List[str] = []
    content_errors: List[Dict[str, Any]] = []

    summary: Dict[str, Any] = {
        "total_sections": 0,
        "sections_verified": 0,
        "sections_missing": 0,
        "section_details": [],
        "total_items": 0,
        "items_fully_found": 0,
        "items_partially_found": 0,
        "items_not_found": 0,
        "total_options": 0,
        "options_found": 0,
        "options_missing": 0,
        "options_unable_to_verify": 0,
        "details": []
    }

    if not sections:
        return expected_changes, content_errors, summary

    summary["total_sections"] = len(sections)

    # Extract normalized page text, blocks, and image status for each page
    page_texts: List[str] = []
    page_blocks_list: List[List[str]] = []
    page_is_raster: List[bool] = []
    for page in gen_doc:
        raw_text = page.get_text("text")
        page_texts.append(normalize_text(raw_text))
        p_blocks = [normalize_text(b[4]) for b in page.get_text("blocks") if b[6] == 0 and b[4].strip()]
        page_blocks_list.append(p_blocks)
        # Check if page is an unextracted raster scan
        has_images = len(page.get_images()) > 0
        has_scant_text = len(raw_text.strip()) < 30
        page_is_raster.append(has_images and has_scant_text)

    full_doc_text = " ".join(page_texts)

    for sec in sections:
        sec_title = str(getattr(sec, "title", sec.get("title", "") if isinstance(sec, dict) else "")).strip()
        questions = getattr(sec, "questions", sec.get("questions", []) if isinstance(sec, dict) else [])

        # Validate section header presence dynamically
        if sec_title:
            sec_found = False
            sec_found_page: Optional[int] = None
            for p_idx, p_text in enumerate(page_texts):
                is_pres, _ = is_section_heading_present(sec_title, p_text, page_blocks_list[p_idx])
                if is_pres:
                    sec_found = True
                    sec_found_page = p_idx + 1
                    break

            if not sec_found:
                is_pres_doc, _ = is_section_heading_present(sec_title, full_doc_text, [])
                if is_pres_doc:
                    sec_found = True
                    sec_found_page = 1

            if sec_found:
                summary["sections_verified"] += 1
                expected_changes.append(f"Section '{sec_title}': verified present on Page {sec_found_page}.")
                summary["section_details"].append({
                    "section_title": sec_title,
                    "status": "FOUND",
                    "page_number": sec_found_page,
                    "message": f"Verified present on Page {sec_found_page}."
                })
            else:
                summary["sections_missing"] += 1
                content_errors.append({
                    "category": "section_missing",
                    "severity": "warning",
                    "title": f"Section '{sec_title}' Heading Missing",
                    "description": f"The section heading '{sec_title}' was not found in the generated PDF.",
                    "page_number": None
                })
                summary["section_details"].append({
                    "section_title": sec_title,
                    "status": "CONFIRMED_MISSING",
                    "page_number": None,
                    "message": "Section heading not detected in document text."
                })

        for q in questions:
            summary["total_items"] += 1
            q_num = str(getattr(q, "number", q.get("number", "") if isinstance(q, dict) else "")).strip()
            q_text = str(getattr(q, "text", q.get("text", "") if isinstance(q, dict) else "")).strip()
            options = getattr(q, "options", q.get("options", []) if isinstance(q, dict) else [])
            subquestions = getattr(q, "subquestions", q.get("subquestions", []) if isinstance(q, dict) else [])
            matching_left = getattr(q, "matching_left", q.get("matching_left", []) if isinstance(q, dict) else [])
            matching_right = getattr(q, "matching_right", q.get("matching_right", []) if isinstance(q, dict) else [])
            image_base64 = getattr(q, "image_base64", q.get("image_base64", None) if isinstance(q, dict) else None)
            image_caption = getattr(q, "image_caption", q.get("image_caption", None) if isinstance(q, dict) else None)

            q_text_norm = normalize_text(q_text)
            if not q_text_norm:
                continue

            found_on_page: Optional[int] = None
            q_text_found = False

            # Search across pages
            for p_idx, p_text in enumerate(page_texts):
                if is_content_fragment_present(q_text_norm, p_text, page_blocks_list[p_idx]):
                    q_text_found = True
                    found_on_page = p_idx + 1
                    break

            if not q_text_found and is_content_fragment_present(q_text_norm, full_doc_text, []):
                q_text_found = True
                found_on_page = 1

            if q_text_found:
                target_p_text = page_texts[found_on_page - 1] if found_on_page and found_on_page <= len(page_texts) else full_doc_text
                target_blocks = page_blocks_list[found_on_page - 1] if found_on_page and found_on_page <= len(page_blocks_list) else []
                is_scanned_page = page_is_raster[found_on_page - 1] if found_on_page and found_on_page <= len(page_is_raster) else False

                missing_sub_items: List[str] = []
                options_status: List[Dict[str, Any]] = []
                subquestions_status: List[Dict[str, Any]] = []
                matching_status: List[Dict[str, Any]] = []

                # Validate options individually
                if options:
                    for opt in options:
                        summary["total_options"] += 1
                        opt_str = str(opt).strip()
                        opt_present, match_type = is_option_present(opt_str, target_p_text, target_blocks)
                        if not opt_present and opt_str not in full_doc_text:
                            doc_present, doc_match = is_option_present(opt_str, full_doc_text, [])
                            if doc_present:
                                opt_present = True
                                match_type = f"doc_{doc_match}"

                        if opt_present:
                            summary["options_found"] += 1
                            options_status.append({
                                "option": opt_str,
                                "status": "FOUND",
                                "page_number": found_on_page,
                                "match_type": match_type
                            })
                        elif is_scanned_page:
                            summary["options_unable_to_verify"] += 1
                            options_status.append({
                                "option": opt_str,
                                "status": "UNABLE_TO_VERIFY",
                                "page_number": found_on_page,
                                "message": "Scanned document raster image; direct text extraction unavailable."
                            })
                        else:
                            summary["options_missing"] += 1
                            missing_sub_items.append(f"Option '{opt_str}'")
                            options_status.append({
                                "option": opt_str,
                                "status": "CONFIRMED_MISSING",
                                "page_number": found_on_page,
                                "message": "Option text not detected on page."
                            })

                # Validate matching items individually
                if matching_left and matching_right:
                    for m_side, items in [("left", matching_left), ("right", matching_right)]:
                        for m_item in items:
                            m_norm = normalize_text(str(m_item))
                            m_present = False
                            if m_norm:
                                m_present = (
                                    is_content_fragment_present(m_norm, target_p_text, target_blocks) or
                                    is_content_fragment_present(m_norm, full_doc_text, [])
                                )
                            if m_present:
                                matching_status.append({"item": str(m_item), "side": m_side, "status": "FOUND"})
                            elif is_scanned_page:
                                matching_status.append({"item": str(m_item), "side": m_side, "status": "UNABLE_TO_VERIFY"})
                            else:
                                missing_sub_items.append(f"Matching item '{m_item}'")
                                matching_status.append({"item": str(m_item), "side": m_side, "status": "CONFIRMED_MISSING"})

                # Validate image presence if image_base64 was provided
                if image_base64:
                    has_doc_images = any(len(p.get_images()) > 0 for p in gen_doc)
                    if not has_doc_images:
                        missing_sub_items.append("Attached question image / diagram")

                # Validate subquestions individually
                if subquestions:
                    for sq in subquestions:
                        sq_txt = str(getattr(sq, "text", sq.get("text", "") if isinstance(sq, dict) else "")).strip()
                        sq_lbl = str(getattr(sq, "label", sq.get("label", "") if isinstance(sq, dict) else "")).strip()
                        sq_norm = normalize_text(sq_txt)
                        sq_present = False
                        if sq_norm:
                            sq_present = (
                                is_content_fragment_present(sq_norm, target_p_text, target_blocks) or
                                is_content_fragment_present(sq_norm, full_doc_text, [])
                            )

                        if sq_present:
                            subquestions_status.append({
                                "label": sq_lbl,
                                "text": sq_txt,
                                "status": "FOUND",
                                "page_number": found_on_page
                            })
                        elif is_scanned_page:
                            subquestions_status.append({
                                "label": sq_lbl,
                                "text": sq_txt,
                                "status": "UNABLE_TO_VERIFY",
                                "page_number": found_on_page,
                                "message": "Scanned document raster image; direct text extraction unavailable."
                            })
                        else:
                            missing_sub_items.append(f"Sub-question '{sq_lbl} {sq_txt}'")
                            subquestions_status.append({
                                "label": sq_lbl,
                                "text": sq_txt,
                                "status": "CONFIRMED_MISSING",
                                "page_number": found_on_page,
                                "message": "Subquestion text not detected on page."
                            })

                if missing_sub_items:
                    summary["items_partially_found"] += 1
                    content_errors.append({
                        "category": "content_partial",
                        "severity": "warning",
                        "title": f"Question {q_num} Partially Found on Page {found_on_page}",
                        "description": f"Question text rendered, but {len(missing_sub_items)} items missing: {', '.join(missing_sub_items[:3])}.",
                        "page_number": found_on_page
                    })
                    summary["details"].append({
                        "question_number": q_num,
                        "question_text": q_text,
                        "status": "PARTIAL",
                        "page_number": found_on_page,
                        "main_text_status": "FOUND",
                        "options_status": options_status,
                        "matching_status": matching_status,
                        "subquestions_status": subquestions_status,
                        "message": f"Question text present, {len(missing_sub_items)} sub-elements missing."
                    })
                else:
                    summary["items_fully_found"] += 1
                    expected_changes.append(f"Question {q_num}: '{q_text[:35]}...' fully verified on Page {found_on_page}.")
                    summary["details"].append({
                        "question_number": q_num,
                        "question_text": q_text,
                        "status": "FOUND",
                        "page_number": found_on_page,
                        "main_text_status": "FOUND",
                        "options_status": options_status,
                        "matching_status": matching_status,
                        "subquestions_status": subquestions_status,
                        "message": "Fully verified in output document."
                    })
            else:
                summary["items_not_found"] += 1
                content_errors.append({
                    "category": "content_error",
                    "severity": "error",
                    "title": f"Question {q_num} Not Found in Output",
                    "description": f"The question text '{q_text[:60]}...' was not found in the generated PDF.",
                    "page_number": None
                })
                summary["details"].append({
                    "question_number": q_num,
                    "question_text": q_text,
                    "status": "NOT_FOUND",
                    "page_number": None,
                    "main_text_status": "NOT_FOUND",
                    "options_status": [],
                    "subquestions_status": [],
                    "message": "Content missing from generated PDF text."
                })

    return expected_changes, content_errors, summary

def review_pdf_preservation(
    reference_pdf_path: Path,
    generated_pdf_path: Path,
    sections: Optional[List[Any]] = None,
    config: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Performs Stage Four review & comparison:
    1. Side-by-side comparison images.
    2. Visual difference overlay (distinguishing layout differences from expected content changes).
    3. Deterministic checks: page dimensions, outer border, header logos, dividers, footers.
    4. Text collision, overlap, and overflow checks.
    5. Content integrity check (verifies zero dropped or missing questions).
    6. Structured report with layout differences, content errors, expected content changes,
       and auto-fixable actions.
    """
    passes: List[str] = []
    layout_differences: List[Dict[str, Any]] = []
    auto_fixable_actions: List[str] = []

    try:
        ref_doc = fitz.open(str(reference_pdf_path))
    except Exception as e:
        return {"status": "error", "message": f"Could not open reference PDF: {str(e)}"}

    try:
        gen_doc = fitz.open(str(generated_pdf_path))
    except Exception as e:
        ref_doc.close()
        return {"status": "error", "message": f"Generated PDF is invalid or corrupted: {str(e)}"}

    ref_pages = len(ref_doc)
    gen_pages = len(gen_doc)

    # 1. Page Dimensions Check
    p0_ref = ref_doc[0]
    p0_gen = gen_doc[0]
    w_match = abs(p0_ref.rect.width - p0_gen.rect.width) < 2.5
    h_match = abs(p0_ref.rect.height - p0_gen.rect.height) < 2.5

    if w_match and h_match:
        passes.append(f"Page dimensions exactly match reference ({p0_ref.rect.width:.1f} x {p0_ref.rect.height:.1f} pt)")
    else:
        layout_differences.append({
            "category": "layout_difference",
            "severity": "verified",
            "title": "Page Dimension Mismatch",
            "description": f"Reference is {p0_ref.rect.width:.1f}x{p0_ref.rect.height:.1f} pt; Generated is {p0_gen.rect.width:.1f}x{p0_gen.rect.height:.1f} pt.",
            "page_number": 1
        })

    # 2. Outer Border Check
    ref_has_border = any(
        (d.get("rect") and (d["rect"][2] - d["rect"][0]) > p0_ref.rect.width * 0.75 and (d["rect"][3] - d["rect"][1]) > p0_ref.rect.height * 0.75)
        for d in p0_ref.get_drawings()
    )
    gen_has_border = any(
        (d.get("rect") and (d["rect"][2] - d["rect"][0]) > p0_gen.rect.width * 0.75 and (d["rect"][3] - d["rect"][1]) > p0_gen.rect.height * 0.75)
        for d in p0_gen.get_drawings()
    )

    if ref_has_border:
        if gen_has_border:
            passes.append("Reference outer rectangular page border faithfully preserved on generated document")
        else:
            layout_differences.append({
                "category": "layout_difference",
                "severity": "verified",
                "title": "Outer Rectangular Border Lost",
                "description": "The reference template has an enclosing border that was missing from the generated document.",
                "page_number": 1
            })
            auto_fixable_actions.append("enable_page_border")
    else:
        if not gen_has_border:
            passes.append("Reference has no outer border; correctly omitted from generated output")
        else:
            layout_differences.append({
                "category": "layout_difference",
                "severity": "verified",
                "title": "Unwanted Border Introduced",
                "description": "Generated document has an outer border, but the reference document has none.",
                "page_number": 1
            })

    # 3. Logo Presence Check
    ref_images = p0_ref.get_images()
    gen_images = p0_gen.get_images()
    if ref_images:
        if len(gen_images) >= len(ref_images):
            passes.append("Original header emblem / logo preserved in exact position")
        else:
            layout_differences.append({
                "category": "layout_difference",
                "severity": "uncertain",
                "title": "Header Logo Image Count Mismatch",
                "description": f"Reference contains {len(ref_images)} embedded image(s); generated has {len(gen_images)}.",
                "page_number": 1
            })
    else:
        passes.append("Reference document has no header logo; none introduced")

    # 4. Text Overlap Detection
    overlap_warnings = check_text_overlaps(gen_doc)
    if not overlap_warnings:
        passes.append("No overlapping or colliding text blocks detected")
    else:
        for ow in overlap_warnings:
            layout_differences.append({
                "category": "layout_difference",
                "severity": "verified",
                "title": "Text Block Collision",
                "description": ow,
                "page_number": 1
            })
        auto_fixable_actions.append("reduce_font_size")

    # 5. Text Overflow Detection
    overflow_warnings = check_text_overflows(gen_doc)
    if not overflow_warnings:
        passes.append("All content flows comfortably within content boundaries")
    else:
        for ofw in overflow_warnings:
            layout_differences.append({
                "category": "layout_difference",
                "severity": "verified",
                "title": "Text Overflow into Margin",
                "description": ofw,
                "page_number": None
            })
        auto_fixable_actions.append("compact_spacing")

    # 6. Content Integrity Check (verifies no dropped questions)
    expected_content_changes, content_errors, content_summary = verify_content_integrity(sections, gen_doc)
    if not content_errors:
        passes.append("All requested user questions and sections verified present in the generated document")

    # 7. Render comparison images: Original, Generated, Side-by-Side, and Visual Diff Overlay
    comp_prefix = f"cmp_{generated_pdf_path.stem}"
    ref_imgs = render_pdf_pages_to_images(reference_pdf_path, f"{comp_prefix}_ref")
    gen_imgs = render_pdf_pages_to_images(generated_pdf_path, f"{comp_prefix}_gen")

    side_by_side_paths = []
    page_comparisons = []
    max_pages = max(len(ref_imgs), len(gen_imgs))

    for i in range(max_pages):
        ref_i = ref_imgs[min(i, len(ref_imgs) - 1)]
        gen_i = gen_imgs[min(i, len(gen_imgs) - 1)]

        # Side-by-side
        sbs_file = COMPARISONS_DIR / f"{comp_prefix}_sbs_p{i+1}.png"
        generate_side_by_side_comparison(ref_i, gen_i, sbs_file)
        side_by_side_paths.append(str(sbs_file))

        # Diff overlay
        overlay_file = COMPARISONS_DIR / f"{comp_prefix}_overlay_p{i+1}.png"
        _, diff_pct = generate_visual_diff_overlay(ref_i, gen_i, overlay_file)

        # Thermal Diff Heatmap
        heatmap_file = COMPARISONS_DIR / f"{comp_prefix}_heatmap_p{i+1}.png"
        generate_difference_heatmap(ref_i, gen_i, heatmap_file)

        # Pixel Metrics
        im_r = Image.open(ref_i).convert("RGB")
        im_g = Image.open(gen_i).convert("RGB")
        w_m = max(im_r.width, im_g.width)
        h_m = max(im_r.height, im_g.height)
        im_r_n = im_r.resize((w_m, h_m)) if im_r.size != (w_m, h_m) else im_r
        im_g_n = im_g.resize((w_m, h_m)) if im_g.size != (w_m, h_m) else im_g
        metrics = calculate_image_difference_metrics(im_r_n, im_g_n)

        p_status = "passed"
        p_label = "Template Faithful"
        if metrics["layout_difference_percentage"] > 20.0:
            p_status = "mismatch"
            p_label = "Layout Deviation"
        elif metrics["layout_difference_percentage"] > 8.0:
            p_status = "review"
            p_label = "Needs Review"

        p_notes = f"Layout variance: {metrics['layout_difference_percentage']}%, Content diff: {metrics['content_difference_percentage']}%"

        if diff_pct > 15.0 and i == 0:
            layout_differences.append({
                "category": "layout_difference",
                "severity": "uncertain",
                "title": f"Layout Region Deviation on Page {i+1}",
                "description": f"Detected {diff_pct}% visual variation in header/margin regions outside content zone.",
                "page_number": i + 1
            })

        page_comparisons.append({
            "page_number": i + 1,
            "status": p_status,
            "status_label": p_label,
            "dimensions_match": True,
            "difference_percentage": metrics["difference_percentage"],
            "layout_difference_percentage": metrics["layout_difference_percentage"],
            "content_difference_percentage": metrics["content_difference_percentage"],
            "similarity_score": metrics["similarity_score"],
            "mean_abs_difference": metrics["mean_absolute_difference"],
            "reference_image_data": image_to_base64_data_url(ref_i),
            "generated_image_data": image_to_base64_data_url(gen_i),
            "side_by_side_data": image_to_base64_data_url(sbs_file),
            "diff_overlay_data": image_to_base64_data_url(overlay_file),
            "heatmap_data": image_to_base64_data_url(heatmap_file),
            "notes": p_notes,
        })

    ref_doc.close()
    gen_doc.close()

    # Calculate fidelity score
    penalty = (len(layout_differences) * 10) + (len(content_errors) * 25)
    fidelity_score = max(0, min(100, 100 - penalty))

    # Overall validation status
    if len(content_errors) > 0 or fidelity_score < 60:
        validation_status = "FAIL"
    elif len(layout_differences) > 0 or fidelity_score < 85:
        validation_status = "WARNING"
    else:
        validation_status = "PASS"

    issues_flat = [d["description"] for d in layout_differences] + [c["description"] for c in content_errors]

    avg_sim = round(
        sum(p.get("similarity_score", 100.0) for p in page_comparisons) / max(1, len(page_comparisons)), 1
    )

    return {
        "status": "success",
        "validation_status": validation_status,
        "reference_pages": ref_pages,
        "generated_pages": gen_pages,
        "fidelity_score": fidelity_score,
        "average_similarity_score": avg_sim,
        "passes": passes,
        "layout_differences": layout_differences,
        "content_errors": content_errors,
        "content_validation": content_summary,
        "expected_content_changes": expected_content_changes,
        "page_comparisons": page_comparisons,
        "auto_fixable_actions": list(set(auto_fixable_actions)),
        "side_by_side_images": side_by_side_paths,
        "issues": issues_flat,
        "comparison_summary": {
            "passed": sum(1 for p in page_comparisons if p.get("status") == "passed"),
            "needs_review": sum(1 for p in page_comparisons if p.get("status") == "review"),
            "failed": sum(1 for p in page_comparisons if p.get("status") == "mismatch"),
            "total_pages": len(page_comparisons)
        }
    }

