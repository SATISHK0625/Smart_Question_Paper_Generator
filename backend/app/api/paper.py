from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from typing import Optional

from ..models.schemas import GeneratePaperRequest, OverviewData, Section
from ..services.pdf_generator import generate_pdf
from ..services.overview_service import compute_overview_data
from ..utils.file_utils import cleanup_file

router = APIRouter()

import base64
import io
from PIL import Image

def validate_base64_image(image_data: str, max_size_bytes: int = 5 * 1024 * 1024) -> tuple[bool, str]:
    if not image_data or not isinstance(image_data, str):
        return False, "Missing image data."
    raw_b64 = image_data.split(",", 1)[1] if "," in image_data else image_data
    try:
        data = base64.b64decode(raw_b64)
    except Exception:
        return False, "Invalid base64 image encoding."

    if len(data) > max_size_bytes:
        return False, f"Image size exceeds 5MB limit ({round(len(data) / (1024 * 1024), 2)}MB)."

    try:
        with Image.open(io.BytesIO(data)) as img:
            fmt = (img.format or "").upper()
            if fmt not in ["PNG", "JPEG", "JPG", "WEBP"]:
                return False, f"Unsupported image format '{fmt}'. Only PNG, JPEG, and WebP are allowed."
            w, h = img.size
            if w < 5 or h < 5:
                return False, "Image dimensions are too small."
            if w > 6000 or h > 6000:
                return False, "Image dimensions exceed 6000x6000px limit."
    except Exception as e:
        return False, f"Corrupt or unreadable image file: {str(e)}"

    return True, ""

def validate_paper_sections(sections: list[Section]):
    """
    Validates sections and questions submitted for paper generation.
    Returns a list of human-readable error descriptions.
    """
    errors = []
    if not sections:
        errors.append("At least one section is required to generate the question paper.")
        return errors

    for s_idx, sec in enumerate(sections, 1):
        if not sec.title or not sec.title.strip():
            errors.append(f"Section {s_idx}: Section title is required.")
        for q_idx, q in enumerate(sec.questions, 1):
            q_label = f"Question {q.number}" if q.number and q.number.strip() else f"Question #{q_idx}"
            if not q.text or not q.text.strip():
                errors.append(f"Section {s_idx} ({sec.title or 'Untitled'}), {q_label}: Question text cannot be empty.")
            
            effective_type = (q.question_type or sec.question_type or "").lower().replace(" ", "_").replace("-", "_")
            
            # MCQ validation
            if effective_type in ["mcq", "multiple_choice"]:
                valid_opts = [opt for opt in q.options if opt and str(opt).strip()]
                if len(valid_opts) < 2:
                    errors.append(f"Section {s_idx} ({sec.title or 'Untitled'}), {q_label}: Multiple Choice questions require at least 2 options.")

            # Match the following validation
            elif effective_type in ["matching", "match_the_following"] or q.is_matching:
                left_items = [item for item in q.matching_left if item and str(item).strip()]
                right_items = [item for item in q.matching_right if item and str(item).strip()]
                if len(left_items) < 2 or len(right_items) < 2:
                    errors.append(f"Section {s_idx} ({sec.title or 'Untitled'}), {q_label}: Match the Following requires at least 2 items in both Column A and Column B.")
                elif len(left_items) != len(right_items):
                    errors.append(f"Section {s_idx} ({sec.title or 'Untitled'}), {q_label}: Column A and Column B must have the same number of items (got {len(left_items)} and {len(right_items)}).")

            # Image-based question validation
            elif effective_type in ["image_based", "image"]:
                if not q.image_base64:
                    errors.append(f"Section {s_idx} ({sec.title or 'Untitled'}), {q_label}: Image-based questions require an uploaded image.")
                else:
                    is_valid, img_err = validate_base64_image(q.image_base64)
                    if not is_valid:
                        errors.append(f"Section {s_idx} ({sec.title or 'Untitled'}), {q_label}: {img_err}")

            # Diagram identification question validation
            elif effective_type in ["diagram_identify", "diagram", "identify_parts"]:
                if not q.image_base64:
                    errors.append(f"Section {s_idx} ({sec.title or 'Untitled'}), {q_label}: Diagram questions require an uploaded diagram.")
                else:
                    is_valid, img_err = validate_base64_image(q.image_base64)
                    if not is_valid:
                        errors.append(f"Section {s_idx} ({sec.title or 'Untitled'}), {q_label}: {img_err}")
                
                if not q.diagram_markers or len(q.diagram_markers) == 0:
                    errors.append(f"Section {s_idx} ({sec.title or 'Untitled'}), {q_label}: Diagram questions require at least one marker placed on the diagram.")
                else:
                    for m_idx, marker in enumerate(q.diagram_markers, 1):
                        m_x = getattr(marker, "x", marker.get("x", 0.0) if isinstance(marker, dict) else 0.0)
                        m_y = getattr(marker, "y", marker.get("y", 0.0) if isinstance(marker, dict) else 0.0)
                        if m_x < 0.0 or m_x > 1.0 or m_y < 0.0 or m_y > 1.0:
                            errors.append(f"Section {s_idx} ({sec.title or 'Untitled'}), {q_label}: Marker #{m_idx} coordinates must be between 0.0 and 1.0 (got x={m_x}, y={m_y}).")
    return errors

@router.post("/preview")
def preview_paper(payload: GeneratePaperRequest, background_tasks: BackgroundTasks):
    """
    Generate question paper preview PDF based on configuration, questions, and reference style.
    Returns previewable PDF file.
    """
    errors = validate_paper_sections(payload.sections)
    if errors:
        raise HTTPException(
            status_code=400,
            detail={"message": "Validation failed: " + "; ".join(errors), "validation_errors": errors}
        )

    try:
        include_ov = payload.config.overview_placement in ["start_of_paper", "end_of_paper"]
        pdf_path, _ = generate_pdf(
            sections=payload.sections,
            config=payload.config,
            reference_style=payload.reference_style,
            include_overview=include_ov,
            is_overview_only=False
        )
        background_tasks.add_task(cleanup_file, pdf_path)
        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            headers={"Content-Disposition": "inline; filename=preview.pdf"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate preview: {str(e)}")

@router.post("/generate")
def generate_paper_file(payload: GeneratePaperRequest, background_tasks: BackgroundTasks):
    """
    Generate finalized question-paper PDF.
    Enforces the Pre-Export Quality Assurance Gate.
    Returns downloadable PDF.
    """
    from ..services.quality_checker import run_pre_export_quality_check

    # Pre-generation quality check
    report = run_pre_export_quality_check(payload.sections, payload.config, payload.reference_style)
    if not report.can_export:
        err_msgs = [f.message for f in report.findings if f.severity == "error"]
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Quality Assurance Gate: Blocking errors must be resolved before export: " + "; ".join(err_msgs),
                "validation_errors": err_msgs,
                "quality_report": report.model_dump()
            }
        )

    try:
        include_ov = payload.config.overview_placement in ["start_of_paper", "end_of_paper"]
        pdf_path, _ = generate_pdf(
            sections=payload.sections,
            config=payload.config,
            reference_style=payload.reference_style,
            include_overview=include_ov,
            is_overview_only=False
        )
        background_tasks.add_task(cleanup_file, pdf_path)
        
        safe_subject = "".join(c for c in payload.config.subject_name if c.isalnum() or c in "._- ") or "Question_Paper"
        download_name = f"{safe_subject}.pdf"

        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename=download_name,
            headers={"Content-Disposition": f'attachment; filename="{download_name}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate question paper: {str(e)}")

@router.post("/quality-check")
def quality_check_paper(payload: GeneratePaperRequest, background_tasks: BackgroundTasks):
    """
    Feature 2: Pre-Export Quality Assurance Checker.
    Runs Pass 1 (structured content) and Pass 2 (generated PDF rendering).
    Returns QualityReport with findings, severity, and export eligibility.
    """
    from ..services.quality_checker import run_pre_export_quality_check
    try:
        pdf_path = None
        # If valid enough to generate preview, also run phase 2 checks on the rendered PDF
        errors = validate_paper_sections(payload.sections)
        if not errors:
            try:
                pdf_path, _ = generate_pdf(
                    sections=payload.sections,
                    config=payload.config,
                    reference_style=payload.reference_style,
                    include_overview=False,
                    is_overview_only=False
                )
                background_tasks.add_task(cleanup_file, pdf_path)
            except Exception:
                pdf_path = None

        report = run_pre_export_quality_check(
            sections=payload.sections,
            config=payload.config,
            reference_style=payload.reference_style,
            generated_pdf_path=pdf_path
        )
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quality check failed: {str(e)}")


@router.post("/overview")
def get_paper_overview(
    payload: GeneratePaperRequest,
    background_tasks: BackgroundTasks,
    download_pdf: bool = Query(False, description="If true, returns PDF overview report file")
):
    """
    Calculate section-wise statistics, marks distribution, and validation warnings.
    If download_pdf=true, exports standalone Overview PDF.
    """
    try:
        overview_data = compute_overview_data(
            sections=payload.sections,
            config=payload.config
        )

        if download_pdf:
            pdf_path, _ = generate_pdf(
                sections=payload.sections,
                config=payload.config,
                reference_style=payload.reference_style,
                include_overview=True,
                is_overview_only=True
            )
            background_tasks.add_task(cleanup_file, pdf_path)
            return FileResponse(
                path=str(pdf_path),
                media_type="application/pdf",
                filename="Question_Paper_Overview.pdf",
                headers={"Content-Disposition": 'attachment; filename="Question_Paper_Overview.pdf"'}
            )

        return overview_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute overview: {str(e)}")

@router.post("/review")
def review_generated_paper(payload: GeneratePaperRequest, background_tasks: BackgroundTasks):
    """
    Stage Three: Review the generated paper against the reference template.
    Returns fidelity score, passing checks, visual issues, and side-by-side comparison images.
    """
    from ..services.pdf_generator import find_reference_pdf_path
    from ..services.pdf_review_service import review_pdf_preservation

    try:
        ref_path = find_reference_pdf_path(payload.reference_style, payload.config)
        if not ref_path or not ref_path.exists():
            return {
                "status": "warning",
                "message": "No reference PDF uploaded for comparative visual review. Document generated using standard styling.",
                "fidelity_score": 100,
                "passes": ["Document generated successfully"],
                "issues": []
            }

        pdf_path, _ = generate_pdf(
            sections=payload.sections,
            config=payload.config,
            reference_style=payload.reference_style,
            include_overview=False,
            is_overview_only=False
        )
        background_tasks.add_task(cleanup_file, pdf_path)

        review_results = review_pdf_preservation(
            reference_pdf_path=ref_path,
            generated_pdf_path=pdf_path,
            sections=payload.sections,
            config=payload.config
        )
        return review_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to perform visual review: {str(e)}")

@router.post("/compare")
def compare_generated_paper(payload: GeneratePaperRequest, background_tasks: BackgroundTasks):
    """
    Feature 1: Visual PDF Comparison.
    Renders reference and generated PDF pages, generates Side-by-Side, Difference Overlay,
    and Difference Heatmap, and computes Mean Absolute Difference and similarity metrics.
    """
    from ..services.pdf_generator import find_reference_pdf_path
    from ..services.pdf_comparison_service import run_visual_pdf_comparison

    try:
        ref_path = find_reference_pdf_path(payload.reference_style, payload.config)
        if not ref_path or not ref_path.exists():
            return {
                "status": "warning",
                "message": "No reference PDF template found to compare against.",
                "reference_pages": 0,
                "generated_pages": 0,
                "pages": [],
                "summary": {"passed": 0, "needs_review": 0, "failed": 0, "total_pages": 0}
            }

        pdf_path, _ = generate_pdf(
            sections=payload.sections,
            config=payload.config,
            reference_style=payload.reference_style,
            include_overview=False,
            is_overview_only=False
        )
        background_tasks.add_task(cleanup_file, pdf_path)

        comparison_results = run_visual_pdf_comparison(
            reference_pdf_path=ref_path,
            generated_pdf_path=pdf_path
        )
        return comparison_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Visual comparison failed: {str(e)}")


# ----------------- TEACHER ANSWER KEY ENDPOINTS (FEATURE 5) -----------------

@router.post("/answer-key/summary")
def get_answer_key_summary(payload: GeneratePaperRequest):
    """
    Feature 5: Calculates Teacher Answer Key summary:
    - Questions with answers available
    - Questions missing answers
    - Questions with rubrics & key points
    - Total marks & consistency
    """
    from ..services.answer_key_service import extract_teacher_answer_metadata
    from ..services.quality_checker import validate_teacher_answer_key_metadata

    errors = validate_paper_sections(payload.sections)
    if errors:
        raise HTTPException(
            status_code=400,
            detail={"message": "Validation failed: " + "; ".join(errors), "validation_errors": errors}
        )

    try:
        items, summary = extract_teacher_answer_metadata(payload.sections)
        findings = validate_teacher_answer_key_metadata(payload.sections)
        return {
            "summary": summary.model_dump(),
            "findings": [f.model_dump() for f in findings]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract answer key summary: {str(e)}")


@router.post("/answer-key/preview")
def preview_teacher_answer_key(payload: GeneratePaperRequest, background_tasks: BackgroundTasks):
    """
    Feature 5: Generate Teacher Answer Key preview PDF.
    Separate from student question paper.
    Returns inline PDF stream.
    """
    from ..services.answer_key_service import generate_teacher_answer_key_pdf

    errors = validate_paper_sections(payload.sections)
    if errors:
        raise HTTPException(
            status_code=400,
            detail={"message": "Validation failed: " + "; ".join(errors), "validation_errors": errors}
        )

    try:
        pdf_path, page_count, summary = generate_teacher_answer_key_pdf(
            sections=payload.sections,
            config=payload.config,
            reference_style=payload.reference_style
        )
        background_tasks.add_task(cleanup_file, pdf_path)

        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            headers={"Content-Disposition": "inline; filename=teacher_answer_key_preview.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate answer key preview: {str(e)}")


@router.post("/answer-key/generate")
def generate_teacher_answer_key(payload: GeneratePaperRequest, background_tasks: BackgroundTasks):
    """
    Feature 5: Generate finalized downloadable Teacher Answer Key PDF.
    Returns separate downloadable teacher PDF file.
    """
    from ..services.answer_key_service import generate_teacher_answer_key_pdf

    errors = validate_paper_sections(payload.sections)
    if errors:
        raise HTTPException(
            status_code=400,
            detail={"message": "Validation failed: " + "; ".join(errors), "validation_errors": errors}
        )

    try:
        pdf_path, page_count, summary = generate_teacher_answer_key_pdf(
            sections=payload.sections,
            config=payload.config,
            reference_style=payload.reference_style
        )
        background_tasks.add_task(cleanup_file, pdf_path)

        safe_subject = "".join(c for c in payload.config.subject_name if c.isalnum() or c in "._- ") or "Exam"
        download_name = f"Teacher_Answer_Key_{safe_subject}.pdf"

        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename=download_name,
            headers={"Content-Disposition": f'attachment; filename="{download_name}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate answer key document: {str(e)}")




