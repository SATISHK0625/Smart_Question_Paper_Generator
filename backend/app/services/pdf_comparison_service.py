import os
import io
import math
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
try:
    import pymupdf as fitz
except ImportError:
    import fitz
from PIL import Image, ImageChops, ImageDraw, ImageFont

from ..utils.file_utils import TEMP_BASE_DIR

COMPARISONS_DIR = TEMP_BASE_DIR / "comparisons"
COMPARISONS_DIR.mkdir(parents=True, exist_ok=True)


def image_to_base64_data_url(img_or_path) -> str:
    if isinstance(img_or_path, (str, Path)):
        if not Path(img_or_path).exists():
            return ""
        with open(str(img_or_path), "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/png;base64,{b64}"
    elif isinstance(img_or_path, Image.Image):
        buf = io.BytesIO()
        img_or_path.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    return ""


def build_heatmap_palette() -> List[int]:
    """
    Builds a 256-entry (768 integers) thermal gradient palette:
    0: Deep dark slate / navy (no difference)
    1-40: Cool cyan / blue (minor rendering / antialiasing differences)
    41-120: Green to Yellow (moderate differences)
    121-255: Orange to Hot Magenta / Red (high difference / layout shifts)
    """
    palette: List[int] = []
    for i in range(256):
        if i == 0:
            r, g, b = 15, 23, 42
        elif i < 40:
            # Dark navy to cyan
            t = i / 40.0
            r = int(15 + (0 - 15) * t)
            g = int(23 + (180 - 23) * t)
            b = int(42 + (240 - 42) * t)
        elif i < 110:
            # Cyan to yellow
            t = (i - 40) / 70.0
            r = int(0 + 250 * t)
            g = int(180 + 40 * t)
            b = int(240 * (1.0 - t))
        elif i < 180:
            # Yellow to orange/red
            t = (i - 110) / 70.0
            r = int(250 + 5 * t)
            g = int(220 * (1.0 - t * 0.7))
            b = int(20 * t)
        else:
            # Hot Red to Magenta
            t = (i - 180) / 75.0
            r = int(255)
            g = int(66 * (1.0 - t))
            b = int(20 + 200 * t)
        palette.extend([max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))])
    return palette

HEATMAP_PALETTE = build_heatmap_palette()


def render_pdf_pages_to_images(pdf_path: Path, prefix: str, dpi: int = 150) -> List[Path]:
    """Renders all pages of a PDF to PNG images at consistent DPI."""
    doc = fitz.open(str(pdf_path))
    paths = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        img_path = COMPARISONS_DIR / f"{prefix}_page_{i+1}.png"
        pix.save(str(img_path))
        paths.append(img_path)
    doc.close()
    return paths


def calculate_image_difference_metrics(
    im1: Image.Image,
    im2: Image.Image,
    diff_threshold: int = 30,
    content_y_ratio_top: float = 0.22,
    content_y_ratio_bottom: float = 0.90
) -> Dict[str, Any]:
    """
    Computes rigorous pixel difference metrics between two normalized images:
    - Mean absolute pixel difference (MAD) (0.0 to 255.0)
    - Overall difference percentage (pixels with diff > diff_threshold)
    - Layout difference percentage (pixels outside content zone: headers, borders, footers)
    - Content difference percentage (pixels inside content zone)
    - Diagnostic similarity score (0.0 to 100.0%)
    """
    w, h = im1.size
    diff_rgb = ImageChops.difference(im1, im2)
    diff_gray = diff_rgb.convert("L")
    pixels = diff_gray.load()

    total_pixels = w * h
    content_top_px = int(h * content_y_ratio_top)
    content_bottom_px = int(h * content_y_ratio_bottom)

    layout_pixels_total = 0
    layout_diff_count = 0
    content_pixels_total = 0
    content_diff_count = 0
    sum_diff = 0
    total_diff_count = 0

    step = 2  # Sample every 2nd pixel for computational efficiency & consistency
    for y in range(0, h, step):
        in_content_zone = (content_top_px <= y <= content_bottom_px)
        for x in range(0, w, step):
            d_val = pixels[x, y]
            sum_diff += d_val
            if d_val > diff_threshold:
                total_diff_count += 1
                if in_content_zone:
                    content_diff_count += 1
                else:
                    layout_diff_count += 1

            if in_content_zone:
                content_pixels_total += 1
            else:
                layout_pixels_total += 1

    sampled_total = layout_pixels_total + content_pixels_total
    mean_abs_diff = round(sum_diff / max(1, sampled_total), 2)
    diff_pct = round((total_diff_count / max(1, sampled_total)) * 100.0, 2)
    layout_diff_pct = round((layout_diff_count / max(1, layout_pixels_total)) * 100.0, 2)
    content_diff_pct = round((content_diff_count / max(1, content_pixels_total)) * 100.0, 2)

    # Diagnostic similarity score (penalizing layout differences much more heavily than content changes)
    # A paper with different question text will have ~15-25% content diff, but layout diff should be < 5%.
    layout_penalty = layout_diff_pct * 3.5
    content_penalty = content_diff_pct * 0.4
    similarity_score = max(0.0, min(100.0, round(100.0 - (layout_penalty + content_penalty), 1)))

    return {
        "mean_absolute_difference": mean_abs_diff,
        "difference_percentage": diff_pct,
        "layout_difference_percentage": layout_diff_pct,
        "content_difference_percentage": content_diff_pct,
        "similarity_score": similarity_score,
        "total_pixels_compared": total_pixels
    }


def generate_difference_heatmap(
    ref_img_path: Path,
    gen_img_path: Path,
    out_path: Path
) -> Path:
    """
    Renders a thermal heatmap image of pixel differences:
    - 0-30: Navy / No difference
    - 30-100: Cyan to Green
    - 100-180: Yellow to Orange
    - 180-255: Hot Red / Magenta
    Includes top legend banner and overlay on semi-transparent background.
    """
    im1 = Image.open(ref_img_path).convert("RGB")
    im2 = Image.open(gen_img_path).convert("RGB")

    w = max(im1.width, im2.width)
    h = max(im1.height, im2.height)
    if im1.size != (w, h):
        im1 = im1.resize((w, h), Image.Resampling.LANCZOS)
    if im2.size != (w, h):
        im2 = im2.resize((w, h), Image.Resampling.LANCZOS)

    diff_gray = ImageChops.difference(im1, im2).convert("L")

    # Apply thermal palette
    paletted = diff_gray.copy()
    paletted.putpalette(HEATMAP_PALETTE)
    heatmap_rgb = paletted.convert("RGB")

    # Subtle blend with generated page grayscale for spatial context
    im2_gray = im2.convert("L").convert("RGB")
    blended = Image.blend(im2_gray, heatmap_rgb, 0.70)

    # Add legend bar
    banner_h = 36
    legend_bar = Image.new("RGB", (w, banner_h), (15, 23, 42))
    draw = ImageDraw.Draw(legend_bar)

    # Color swatches
    draw.rectangle([16, 12, 32, 24], fill=(15, 23, 42), outline=(100, 116, 139), width=1)
    draw.text((38, 11), "No Diff", fill=(203, 213, 225))

    draw.rectangle([110, 12, 126, 24], fill=(0, 180, 240))
    draw.text((132, 11), "Minor Text", fill=(203, 213, 225))

    draw.rectangle([230, 12, 246, 24], fill=(250, 220, 0))
    draw.text((252, 11), "Moderate Shift", fill=(203, 213, 225))

    draw.rectangle([380, 12, 396, 24], fill=(236, 72, 153))
    draw.text((402, 11), "High Layout / Structure Difference", fill=(203, 213, 225))

    final_img = Image.new("RGB", (w, h + banner_h))
    final_img.paste(legend_bar, (0, 0))
    final_img.paste(blended, (0, banner_h))
    final_img.save(str(out_path), "PNG")
    return out_path


def generate_side_by_side_comparison(ref_img: Path, gen_img: Path, out_path: Path) -> Path:
    """Generates clean side-by-side comparison with labeled banners."""
    im1 = Image.open(ref_img).convert("RGB")
    im2 = Image.open(gen_img).convert("RGB")

    w1, h1 = im1.size
    w2, h2 = im2.size
    banner_h = 36
    max_h = max(h1, h2) + banner_h
    gutter = 24
    tot_w = w1 + w2 + gutter

    combined = Image.new("RGB", (tot_w, max_h), (241, 245, 249))
    draw = ImageDraw.Draw(combined)

    # Top banners
    draw.rectangle([0, 0, w1, banner_h], fill=(30, 41, 59))
    draw.rectangle([w1 + gutter, 0, tot_w, banner_h], fill=(79, 70, 229))

    draw.text((w1 // 2 - 75, 11), "REFERENCE TEMPLATE", fill=(255, 255, 255))
    draw.text((w1 + gutter + (w2 // 2) - 85, 11), "GENERATED QUESTION PAPER", fill=(255, 255, 255))

    combined.paste(im1, (0, banner_h))
    combined.paste(im2, (w1 + gutter, banner_h))
    draw.line([(w1 + gutter // 2, 0), (w1 + gutter // 2, max_h)], fill=(203, 213, 225), width=2)

    combined.save(str(out_path), "PNG")
    return out_path


def generate_visual_diff_overlay(
    ref_img_path: Path,
    gen_img_path: Path,
    out_path: Path,
    content_y_ratio: float = 0.22
) -> Tuple[Path, float]:
    """Produces visual diff overlay distinguishing layout shifts from expected content changes."""
    im1 = Image.open(ref_img_path).convert("RGB")
    im2 = Image.open(gen_img_path).convert("RGB")

    w = max(im1.width, im2.width)
    h = max(im1.height, im2.height)
    if im1.size != (w, h):
        im1 = im1.resize((w, h), Image.Resampling.LANCZOS)
    if im2.size != (w, h):
        im2 = im2.resize((w, h), Image.Resampling.LANCZOS)

    base = Image.blend(im2, Image.new("RGB", (w, h), (255, 255, 255)), 0.25)
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay, "RGBA")

    diff = ImageChops.difference(im1, im2).convert("L")
    content_top_px = int(h * content_y_ratio)
    content_bottom_px = int(h * 0.90)

    diff_pixels = diff.load()
    layout_diff_count = 0
    total_layout_pixels = max(1, (w * h) - (w * (content_bottom_px - content_top_px)))

    # Mark expected content zone
    overlay_draw.rectangle(
        [int(w * 0.04), content_top_px, int(w * 0.96), content_bottom_px],
        outline=(59, 130, 246, 110),
        width=2
    )

    step = 2
    for y in range(0, h, step):
        in_content_zone = (content_top_px <= y <= content_bottom_px)
        for x in range(0, w, step):
            d_val = diff_pixels[x, y]
            if d_val > 35:
                if not in_content_zone:
                    layout_diff_count += 1
                    overlay_draw.rectangle([x, y, x + step, y + step], fill=(236, 72, 153, 190))
                else:
                    overlay_draw.rectangle([x, y, x + step, y + step], fill=(56, 189, 248, 70))

    base.paste(overlay, (0, 0), overlay)

    legend_bar = Image.new("RGB", (w, 32), (15, 23, 42))
    l_draw = ImageDraw.Draw(legend_bar)
    l_draw.rectangle([16, 10, 28, 22], fill=(236, 72, 153))
    l_draw.text((34, 9), "Layout Shift (Header / Margins / Border)", fill=(241, 245, 249))
    l_draw.rectangle([340, 10, 352, 22], fill=(56, 189, 248))
    l_draw.text((358, 9), "Expected Content Changes (Question Text)", fill=(241, 245, 249))

    final_diff_img = Image.new("RGB", (w, h + 32))
    final_diff_img.paste(legend_bar, (0, 0))
    final_diff_img.paste(base, (0, 32))
    final_diff_img.save(str(out_path), "PNG")

    layout_diff_pct = round((layout_diff_count / (total_layout_pixels / (step * step))) * 100, 2)
    return out_path, layout_diff_pct


def run_visual_pdf_comparison(
    reference_pdf_path: Path,
    generated_pdf_path: Path
) -> Dict[str, Any]:
    """
    Comprehensive visual comparison service between reference and generated PDFs:
    1. Validates file existence and readability
    2. Compares page counts, page dimensions, orientation
    3. Renders pages at 150 DPI
    4. Computes Mean Absolute Pixel Difference, percentage above threshold, and similarity score
    5. Produces Side-by-Side, Difference Overlay, and Thermal Difference Heatmap
    6. Identifies missing/extra pages and layout shifts
    7. Returns structured comparison report per page and overall summary
    """
    if not reference_pdf_path or not Path(reference_pdf_path).exists():
        return {
            "status": "error",
            "message": "Reference PDF not found or missing from filesystem."
        }
    if not generated_pdf_path or not Path(generated_pdf_path).exists():
        return {
            "status": "error",
            "message": "Generated PDF not found or generation failed."
        }

    try:
        ref_doc = fitz.open(str(reference_pdf_path))
    except Exception as e:
        return {"status": "error", "message": f"Could not open reference PDF: {str(e)}"}

    try:
        gen_doc = fitz.open(str(generated_pdf_path))
    except Exception as e:
        ref_doc.close()
        return {"status": "error", "message": f"Could not open generated PDF: {str(e)}"}

    ref_page_count = len(ref_doc)
    gen_page_count = len(gen_doc)

    if ref_page_count == 0 or gen_page_count == 0:
        ref_doc.close()
        gen_doc.close()
        return {
            "status": "error",
            "message": f"PDF has zero pages (ref={ref_page_count}, gen={gen_page_count})."
        }

    comp_id = f"cmp_{Path(generated_pdf_path).stem}"
    ref_imgs = render_pdf_pages_to_images(reference_pdf_path, f"{comp_id}_ref", dpi=150)
    gen_imgs = render_pdf_pages_to_images(generated_pdf_path, f"{comp_id}_gen", dpi=150)

    pages_result: List[Dict[str, Any]] = []
    passed_count = 0
    review_count = 0
    mismatch_count = 0

    max_pages = max(ref_page_count, gen_page_count)

    for idx in range(max_pages):
        page_num = idx + 1
        has_ref = idx < ref_page_count
        has_gen = idx < gen_page_count

        if not has_ref:
            # Extra generated page (content flowed onto an additional page)
            gen_img = gen_imgs[idx]
            pages_result.append({
                "page_number": page_num,
                "status": "extra_page",
                "status_label": "Extra Generated Page (Content Extension)",
                "dimensions_match": True,
                "difference_percentage": 100.0,
                "similarity_score": 75.0,
                "mean_abs_difference": 0.0,
                "layout_difference_percentage": 0.0,
                "content_difference_percentage": 100.0,
                "reference_image": None,
                "generated_image": image_to_base64_data_url(gen_img),
                "side_by_side_image": image_to_base64_data_url(gen_img),
                "difference_image": None,
                "heatmap_image": None,
                "notes": f"Generated paper has {gen_page_count} pages while reference template had {ref_page_count}."
            })
            review_count += 1
            continue

        if not has_gen:
            # Missing page (paper generated fewer pages than template)
            ref_img = ref_imgs[idx]
            pages_result.append({
                "page_number": page_num,
                "status": "missing_page",
                "status_label": "Template Page Not Present in Generated Output",
                "dimensions_match": False,
                "difference_percentage": 100.0,
                "similarity_score": 0.0,
                "mean_abs_difference": 0.0,
                "layout_difference_percentage": 100.0,
                "content_difference_percentage": 100.0,
                "reference_image": image_to_base64_data_url(ref_img),
                "generated_image": None,
                "side_by_side_image": None,
                "difference_image": None,
                "heatmap_image": None,
                "notes": f"Reference template contains Page {page_num}, but generated document only has {gen_page_count} pages."
            })
            mismatch_count += 1
            continue

        ref_page = ref_doc[idx]
        gen_page = gen_doc[idx]
        ref_w, ref_h = ref_page.rect.width, ref_page.rect.height
        gen_w, gen_h = gen_page.rect.width, gen_page.rect.height
        dims_match = (abs(ref_w - gen_w) < 3.0) and (abs(ref_h - gen_h) < 3.0)

        ref_img_p = ref_imgs[idx]
        gen_img_p = gen_imgs[idx]

        im_ref = Image.open(ref_img_p).convert("RGB")
        im_gen = Image.open(gen_img_p).convert("RGB")

        # Normalize dimensions for image comparison if slight rounding difference
        w_max = max(im_ref.width, im_gen.width)
        h_max = max(im_ref.height, im_gen.height)
        if im_ref.size != (w_max, h_max):
            im_ref_norm = im_ref.resize((w_max, h_max), Image.Resampling.LANCZOS)
        else:
            im_ref_norm = im_ref
        if im_gen.size != (w_max, h_max):
            im_gen_norm = im_gen.resize((w_max, h_max), Image.Resampling.LANCZOS)
        else:
            im_gen_norm = im_gen

        # Compute metrics
        metrics = calculate_image_difference_metrics(im_ref_norm, im_gen_norm)

        # Side-by-side
        sbs_path = COMPARISONS_DIR / f"{comp_id}_sbs_p{page_num}.png"
        generate_side_by_side_comparison(ref_img_p, gen_img_p, sbs_path)

        # Difference overlay
        overlay_path = COMPARISONS_DIR / f"{comp_id}_overlay_p{page_num}.png"
        generate_visual_diff_overlay(ref_img_p, gen_img_p, overlay_path)

        # Heatmap
        heatmap_path = COMPARISONS_DIR / f"{comp_id}_heatmap_p{page_num}.png"
        generate_difference_heatmap(ref_img_p, gen_img_p, heatmap_path)

        # Evaluate page status:
        # A page is 'passed' if layout differences are minimal (< 8%) and dimensions match.
        # It needs 'review' if layout differences are moderate (8% - 20%).
        # It is 'mismatch' if layout difference > 20% or dimensions mismatch.
        notes = []
        if not dims_match:
            notes.append(f"Dimension mismatch: Ref {ref_w:.1f}x{ref_h:.1f} pt vs Gen {gen_w:.1f}x{gen_h:.1f} pt")
        if metrics["layout_difference_percentage"] > 15.0:
            notes.append(f"Header/margin layout variance is high ({metrics['layout_difference_percentage']}%)")
        elif metrics["content_difference_percentage"] > 0:
            notes.append(f"Content successfully substituted with new question text ({metrics['content_difference_percentage']}% text difference)")

        if not dims_match or metrics["layout_difference_percentage"] > 22.0:
            page_status = "mismatch"
            status_label = "Layout Mismatch Detected"
            mismatch_count += 1
        elif metrics["layout_difference_percentage"] > 8.0:
            page_status = "review"
            status_label = "Needs Layout Review"
            review_count += 1
        else:
            page_status = "passed"
            status_label = "Template Faithful"
            passed_count += 1

        pages_result.append({
            "page_number": page_num,
            "status": page_status,
            "status_label": status_label,
            "dimensions_match": dims_match,
            "ref_dimensions": f"{ref_w:.1f} x {ref_h:.1f} pt",
            "gen_dimensions": f"{gen_w:.1f} x {gen_h:.1f} pt",
            "difference_percentage": metrics["difference_percentage"],
            "layout_difference_percentage": metrics["layout_difference_percentage"],
            "content_difference_percentage": metrics["content_difference_percentage"],
            "mean_abs_difference": metrics["mean_absolute_difference"],
            "similarity_score": metrics["similarity_score"],
            "reference_image": image_to_base64_data_url(ref_img_p),
            "generated_image": image_to_base64_data_url(gen_img_p),
            "side_by_side_image": image_to_base64_data_url(sbs_path),
            "difference_image": image_to_base64_data_url(overlay_path),
            "heatmap_image": image_to_base64_data_url(heatmap_path),
            "notes": "; ".join(notes) if notes else "Header, margins, and borders align with reference template."
        })

    ref_doc.close()
    gen_doc.close()

    overall_status = "passed"
    if mismatch_count > 0:
        overall_status = "failed"
    elif review_count > 0:
        overall_status = "needs_review"

    avg_similarity = round(
        sum(p.get("similarity_score", 0.0) for p in pages_result) / max(1, len(pages_result)), 1
    )

    return {
        "status": "completed",
        "overall_status": overall_status,
        "reference_pages": ref_page_count,
        "generated_pages": gen_page_count,
        "average_similarity_score": avg_similarity,
        "pages": pages_result,
        "summary": {
            "passed": passed_count,
            "needs_review": review_count,
            "failed": mismatch_count,
            "total_pages": len(pages_result)
        }
    }
