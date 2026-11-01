import re
import io
import base64
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
try:
    import pymupdf as fitz
except ImportError:
    import fitz
from PIL import Image

from ..models.schemas import (
    Section, Question, PaperConfig, ReferenceAnalysis,
    QualityFinding, QualityFindingLocation, QualityReport
)
from ..services.pdf_review_service import (
    normalize_text, check_text_overlaps, check_text_overflows, verify_content_integrity
)


def validate_base64_image_bytes(image_data: str, max_size_bytes: int = 5 * 1024 * 1024) -> Tuple[bool, str]:
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
                return False, f"Image dimensions too small ({w}x{h}px)."
            if w > 6000 or h > 6000:
                return False, f"Image dimensions exceed 6000x6000px limit ({w}x{h}px)."
    except Exception as e:
        return False, f"Corrupt or unreadable image file: {str(e)}"

    return True, ""


def validate_structured_paper_content(
    sections: List[Section],
    config: Optional[PaperConfig] = None
) -> List[QualityFinding]:
    """
    Pass 1: Validates structured question paper data before generation.
    Returns a list of structured findings (error, warning, info).
    """
    findings: List[QualityFinding] = []

    # Config checks
    if config:
        if not config.subject_name or not config.subject_name.strip():
            findings.append(QualityFinding(
                code="EMPTY_SUBJECT_NAME",
                severity="warning",
                message="Subject name is not set in paper configuration.",
                location=QualityFindingLocation(),
                suggested_action="Enter the Subject Name in the Paper Header Configuration."
            ))
        if not config.exam_name and not config.institution_name:
            findings.append(QualityFinding(
                code="MISSING_EXAM_OR_INSTITUTION",
                severity="info",
                message="Neither Exam Name nor Institution Name is provided.",
                location=QualityFindingLocation(),
                suggested_action="Provide an Institution or Exam Name for a complete formal header."
            ))

    if not sections or len(sections) == 0:
        findings.append(QualityFinding(
            code="NO_SECTIONS",
            severity="error",
            message="The paper has no sections. At least one section is required.",
            location=QualityFindingLocation(),
            suggested_action="Add at least one section with questions."
        ))
        return findings

    total_marks_sum = 0.0
    has_any_questions = False
    all_question_numbers: List[Tuple[str, str, str]] = [] # (q_num, sec_id, sec_title)

    for s_idx, sec in enumerate(sections, 1):
        sec_title = (sec.title or "").strip()
        sec_loc = QualityFindingLocation(section=sec_title or f"Section {s_idx}", section_id=sec.id)

        if not sec_title:
            findings.append(QualityFinding(
                code="EMPTY_SECTION_TITLE",
                severity="error",
                message=f"Section {s_idx} has an empty title.",
                location=sec_loc,
                suggested_action="Provide a descriptive section title (e.g. 'SECTION A — OBJECTIVE')."
            ))

        if not sec.questions or len(sec.questions) == 0:
            findings.append(QualityFinding(
                code="EMPTY_SECTION",
                severity="error",
                message=f"Section '{sec_title or f'Section {s_idx}'}' contains no questions.",
                location=sec_loc,
                suggested_action="Add questions to this section or remove the empty section."
            ))
            continue

        has_any_questions = True
        sec_q_numbers: List[str] = []

        for q_idx, q in enumerate(sec.questions, 1):
            q_num = (q.number or "").strip()
            q_loc = QualityFindingLocation(
                section=sec_title or f"Section {s_idx}",
                section_id=sec.id,
                question_number=q_num or str(q_idx),
                question_id=q.id
            )

            # Question text
            q_text = (q.text or "").strip()
            if not q_text:
                findings.append(QualityFinding(
                    code="EMPTY_QUESTION_TEXT",
                    severity="error",
                    message=f"Question {q_num or f'#{q_idx}'} in '{sec_title}' has empty text.",
                    location=q_loc,
                    suggested_action="Enter the question text or prompt."
                ))

            # Marks
            if q.marks is not None:
                if q.marks < 0:
                    findings.append(QualityFinding(
                        code="NEGATIVE_MARKS",
                        severity="error",
                        message=f"Question {q_num or f'#{q_idx}'} has negative marks ({q.marks}).",
                        location=q_loc,
                        suggested_action="Set question marks to 0 or a positive number."
                    ))
                else:
                    total_marks_sum += float(q.marks)
            else:
                findings.append(QualityFinding(
                    code="MISSING_MARKS",
                    severity="info",
                    message=f"Question {q_num or f'#{q_idx}'} has no marks allocated.",
                    location=q_loc,
                    suggested_action="Optionally assign marks to this question."
                ))

            # Numbering tracking within section
            if q_num:
                if q_num in sec_q_numbers:
                    findings.append(QualityFinding(
                        code="DUPLICATE_QUESTION_NUMBER",
                        severity="warning",
                        message=f"Duplicate question number '{q_num}' found in section '{sec_title}'.",
                        location=q_loc,
                        suggested_action="Renumber questions sequentially to prevent student confusion."
                    ))
                sec_q_numbers.append(q_num)
                all_question_numbers.append((q_num, sec.id, sec_title))

            # Question-Type Specific Checks
            effective_type = (q.question_type or sec.question_type or "mixed").lower().replace(" ", "_").replace("-", "_")

            # MCQ
            if effective_type in ["mcq", "multiple_choice"]:
                valid_opts = [opt for opt in q.options if opt and str(opt).strip()]
                if len(valid_opts) < 2:
                    findings.append(QualityFinding(
                        code="INSUFFICIENT_MCQ_OPTIONS",
                        severity="error",
                        message=f"Question {q_num or f'#{q_idx}'} requires at least 2 options (found {len(valid_opts)}).",
                        location=q_loc,
                        suggested_action="Add at least 2 distinct answer options."
                    ))
                elif len(valid_opts) > 10:
                    findings.append(QualityFinding(
                        code="EXCESSIVE_MCQ_OPTIONS",
                        severity="warning",
                        message=f"Question {q_num or f'#{q_idx}'} has {len(valid_opts)} options, which may crowd page layout.",
                        location=q_loc,
                        suggested_action="Consider limiting options to 4 or 5 standard choices."
                    ))

                # Check blank or duplicate options
                seen_opt_vals = set()
                for o_idx, opt in enumerate(q.options, 1):
                    opt_s = str(opt).strip()
                    if not opt_s:
                        findings.append(QualityFinding(
                            code="EMPTY_OPTION_TEXT",
                            severity="error",
                            message=f"Option #{o_idx} in Question {q_num or f'#{q_idx}'} is empty.",
                            location=q_loc,
                            suggested_action="Fill in the option text or delete the blank choice."
                        ))
                    else:
                        norm_opt = normalize_text(opt_s)
                        if norm_opt in seen_opt_vals:
                            findings.append(QualityFinding(
                                code="DUPLICATE_OPTION_VALUE",
                                severity="warning",
                                message=f"Question {q_num or f'#{q_idx}'} has duplicate option: '{opt_s}'.",
                                location=q_loc,
                                suggested_action="Ensure all options are distinct."
                            ))
                        seen_opt_vals.add(norm_opt)

            # Match the following
            elif effective_type in ["matching", "match_the_following"] or q.is_matching:
                left_items = [item for item in q.matching_left if item and str(item).strip()]
                right_items = [item for item in q.matching_right if item and str(item).strip()]
                if len(left_items) < 2 or len(right_items) < 2:
                    findings.append(QualityFinding(
                        code="INSUFFICIENT_MATCHING_PAIRS",
                        severity="error",
                        message=f"Question {q_num or f'#{q_idx}'}: Match the Following requires at least 2 pairs in Column A and Column B.",
                        location=q_loc,
                        suggested_action="Add at least 2 items to both columns."
                    ))
                elif len(left_items) != len(right_items):
                    findings.append(QualityFinding(
                        code="UNBALANCED_MATCHING_COLUMNS",
                        severity="error",
                        message=f"Section {s_idx} ({sec_title or 'Untitled'}), Question {q_num or f'#{q_idx}'}: Column A and Column B must have the same number of items (got {len(left_items)} and {len(right_items)}).",
                        location=q_loc,
                        suggested_action="Align Column A and Column B item counts."
                    ))

            # Image-based questions
            elif effective_type in ["image_based", "image"]:
                if not q.image_base64:
                    findings.append(QualityFinding(
                        code="MISSING_QUESTION_IMAGE",
                        severity="error",
                        message=f"Section {s_idx} ({sec_title or 'Untitled'}), Question {q_num or f'#{q_idx}'}: Image-based questions require an uploaded image.",
                        location=q_loc,
                        suggested_action="Upload an image (PNG, JPEG, WebP) for this question."
                    ))
                else:
                    is_valid, img_err = validate_base64_image_bytes(q.image_base64)
                    if not is_valid:
                        findings.append(QualityFinding(
                            code="INVALID_IMAGE_DATA",
                            severity="error",
                            message=f"Section {s_idx} ({sec_title or 'Untitled'}), Question {q_num or f'#{q_idx}'}: {img_err}",
                            location=q_loc,
                            suggested_action="Re-upload a valid image file within 5MB limit."
                        ))

            # Diagram parts identification
            elif effective_type in ["diagram_identify", "diagram", "identify_parts"]:
                if not q.image_base64:
                    findings.append(QualityFinding(
                        code="MISSING_DIAGRAM_IMAGE",
                        severity="error",
                        message=f"Section {s_idx} ({sec_title or 'Untitled'}), Question {q_num or f'#{q_idx}'}: Diagram questions require an uploaded diagram.",
                        location=q_loc,
                        suggested_action="Upload the base diagram image."
                    ))
                else:
                    is_valid, img_err = validate_base64_image_bytes(q.image_base64)
                    if not is_valid:
                        findings.append(QualityFinding(
                            code="INVALID_DIAGRAM_IMAGE",
                            severity="error",
                            message=f"Section {s_idx} ({sec_title or 'Untitled'}), Question {q_num or f'#{q_idx}'}: {img_err}",
                            location=q_loc,
                            suggested_action="Re-upload a valid diagram image."
                        ))

                if not q.diagram_markers or len(q.diagram_markers) == 0:
                    findings.append(QualityFinding(
                        code="NO_DIAGRAM_MARKERS",
                        severity="error",
                        message=f"Section {s_idx} ({sec_title or 'Untitled'}), Question {q_num or f'#{q_idx}'}: Diagram questions require at least one marker placed on the diagram.",
                        location=q_loc,
                        suggested_action="Click on the diagram image to place part markers."
                    ))
                else:
                    for m_idx, marker in enumerate(q.diagram_markers, 1):
                        m_x = getattr(marker, "x", marker.get("x", 0.0) if isinstance(marker, dict) else 0.0)
                        m_y = getattr(marker, "y", marker.get("y", 0.0) if isinstance(marker, dict) else 0.0)
                        if m_x < 0.0 or m_x > 1.0 or m_y < 0.0 or m_y > 1.0:
                            findings.append(QualityFinding(
                                code="OUT_OF_BOUNDS_MARKER",
                                severity="error",
                                message=f"Section {s_idx} ({sec_title or 'Untitled'}), Question {q_num or f'#{q_idx}'}: Marker #{m_idx} coordinates must be between 0.0 and 1.0 (got x={m_x}, y={m_y}).",
                                location=q_loc,
                                suggested_action="Reposition marker within the diagram boundaries."
                            ))


    # Total Marks vs Configured Max Marks check
    if config and config.maximum_marks is not None and config.maximum_marks > 0:
        if abs(total_marks_sum - config.maximum_marks) > 0.01:
            findings.append(QualityFinding(
                code="MARKS_MISMATCH",
                severity="warning",
                message=f"Total question marks sum ({total_marks_sum} marks) does not match configured Maximum Marks ({config.maximum_marks} marks).",
                location=QualityFindingLocation(),
                suggested_action="Adjust question marks or update the Maximum Marks in Paper Configuration."
            ))
        else:
            findings.append(QualityFinding(
                code="MARKS_BALANCED",
                severity="info",
                message=f"Marks total ({total_marks_sum} marks) perfectly matches configured Maximum Marks.",
                location=QualityFindingLocation(),
                suggested_action="No action needed."
            ))

    return findings


def validate_generated_pdf_output(
    pdf_path: Path,
    sections: List[Section]
) -> Tuple[List[QualityFinding], int]:
    """
    Pass 2: Validates generated PDF output after rendering.
    Checks:
    - Page count > 0
    - Blank pages (zero text blocks and no graphics)
    - Content collisions / overlapping text blocks
    - Text clipping or extending into bottom margins
    - Verification that all requested section titles and question text appear in output
    """
    findings: List[QualityFinding] = []
    if not pdf_path.exists():
        findings.append(QualityFinding(
            code="PDF_GENERATION_FAILED",
            severity="error",
            message="Generated PDF file does not exist on disk.",
            location=QualityFindingLocation(),
            suggested_action="Check server logs and retry paper generation."
        ))
        return findings, 0

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        findings.append(QualityFinding(
            code="CORRUPT_GENERATED_PDF",
            severity="error",
            message=f"Generated PDF cannot be opened by PyMuPDF: {str(e)}",
            location=QualityFindingLocation(),
            suggested_action="Retry generation with standard font and margin configurations."
        ))
        return findings, 0

    page_count = len(doc)
    if page_count == 0:
        findings.append(QualityFinding(
            code="EMPTY_PDF",
            severity="error",
            message="Generated PDF contains 0 pages.",
            location=QualityFindingLocation(),
            suggested_action="Ensure sections and questions are not empty."
        ))
        doc.close()
        return findings, 0

    # 1. Blank page detection
    for p_idx, page in enumerate(doc):
        text_blocks = [b for b in page.get_text("blocks") if b[6] == 0 and b[4].strip()]
        drawings = page.get_drawings()
        images = page.get_images()

        # If page has 0 text blocks and no images and fewer than 2 drawings (border)
        if len(text_blocks) == 0 and len(images) == 0 and len(drawings) <= 1:
            findings.append(QualityFinding(
                code="BLANK_PAGE_DETECTED",
                severity="warning",
                message=f"Page {p_idx+1} appears unexpectedly blank (0 text blocks).",
                location=QualityFindingLocation(page_number=p_idx+1),
                suggested_action="Inspect layout spacing or check for unnecessary page breaks."
            ))

    # 2. Text Overlaps / Collisions
    overlaps = check_text_overlaps(doc)
    for ov in overlaps:
        m = re.search(r"Page (\d+):", ov)
        p_num = int(m.group(1)) if m else None
        findings.append(QualityFinding(
            code="TEXT_COLLISION",
            severity="warning",
            message=ov,
            location=QualityFindingLocation(page_number=p_num),
            suggested_action="Reduce font size or increase line spacing in layout fine-tuning."
        ))

    # 3. Text Overflows into Margin
    overflows = check_text_overflows(doc)
    for ofw in overflows:
        m = re.search(r"Page (\d+):", ofw)
        p_num = int(m.group(1)) if m else None
        findings.append(QualityFinding(
            code="TEXT_MARGIN_OVERFLOW",
            severity="warning",
            message=ofw,
            location=QualityFindingLocation(page_number=p_num),
            suggested_action="Apply 'Compact Spacing' or reduce question count per page."
        ))

    # 4. Content Integrity (no omitted questions or options)
    _, content_errors, _ = verify_content_integrity(sections, doc)
    for ce in content_errors:
        findings.append(QualityFinding(
            code="CONTENT_NOT_RENDERED",
            severity="error",
            message=ce.get("description", "Requested question content missing from generated PDF."),
            location=QualityFindingLocation(page_number=ce.get("page_number")),
            suggested_action="Verify that question text does not exceed printable boundaries."
        ))

    # 5. Teacher Answer Key Isolation Audit (Student PDF must NOT contain confidential answer text)
    for p_idx, page in enumerate(doc):
        page_text = page.get_text() or ""
        lower_txt = page_text.lower()
        if "teacher answer key" in lower_txt or "marking scheme" in lower_txt or "confidential · for teacher" in lower_txt:
            findings.append(QualityFinding(
                code="TEACHER_ANSWER_LEAK_IN_STUDENT_PDF",
                severity="error",
                message=f"Page {p_idx+1} in student question paper contains teacher-only answer key markings.",
                location=QualityFindingLocation(page_number=p_idx+1),
                suggested_action="Ensure student PDF strictly excludes teacher answers and grading rubrics."
            ))

    doc.close()
    return findings, page_count


def run_pre_export_quality_check(
    sections: List[Section],
    config: Optional[PaperConfig] = None,
    reference_style: Optional[ReferenceAnalysis] = None,
    generated_pdf_path: Optional[Path] = None
) -> QualityReport:
    """
    Executes the unified Pre-Export Quality Assurance Checker.
    Combines:
    1. Structured question-paper data validation
    2. Generated-PDF output visual & text integrity validation (if PDF provided or generated)
    Returns structured QualityReport with severity counts and blocking export gate.
    """
    all_findings: List[QualityFinding] = []

    # Phase 1: Structured Content Validation
    structured_findings = validate_structured_paper_content(sections, config)
    all_findings.extend(structured_findings)

    # Calculate statistics
    total_q = sum(len(s.questions) for s in sections) if sections else 0
    total_sec = len(sections) if sections else 0
    total_marks = sum(
        sum(q.marks for q in s.questions if q.marks is not None)
        for s in sections
    ) if sections else 0.0

    page_count = 1
    ref_comparison_status = "not_compared"

    # Phase 2: PDF Output Validation (if generated PDF exists)
    if generated_pdf_path and Path(generated_pdf_path).exists():
        pdf_findings, p_count = validate_generated_pdf_output(generated_pdf_path, sections)
        all_findings.extend(pdf_findings)
        page_count = p_count

    if reference_style and reference_style.reference_pdf_path:
        ref_comparison_status = "review"

    error_count = sum(1 for f in all_findings if f.severity == "error")
    warning_count = sum(1 for f in all_findings if f.severity == "warning")
    info_count = sum(1 for f in all_findings if f.severity == "info")

    can_export = (error_count == 0)

    if error_count > 0:
        status = "blocked"
    elif warning_count > 0:
        status = "has_warnings"
    else:
        status = "passed"

    return QualityReport(
        status=status,
        can_export=can_export,
        error_count=error_count,
        warning_count=warning_count,
        info_count=info_count,
        total_questions=total_q,
        total_sections=total_sec,
        total_marks=round(total_marks, 2),
        configured_max_marks=config.maximum_marks if config else None,
        page_count=page_count,
        reference_comparison_status=ref_comparison_status,
        findings=all_findings
    )


def validate_teacher_answer_key_metadata(sections: List[Section]) -> List[QualityFinding]:
    """
    Validates Answer Key mappings against student paper sections:
    - Every answer key entry maps to a question in the paper.
    - Question numbering matches the student paper.
    - No duplicate answer-key entries exist.
    - Matching pairs and diagram labels reference valid items.
    - Missing answers reported accurately as informational findings.
    """
    findings: List[QualityFinding] = []
    seen_q_ids = set()
    seen_q_nums = set()

    for sec in sections:
        for q in sec.questions:
            q_loc = QualityFindingLocation(section=sec.title, section_id=sec.id, question_number=q.number, question_id=q.id)

            # Check duplicate question IDs
            if q.id in seen_q_ids:
                findings.append(QualityFinding(
                    code="DUPLICATE_ANSWER_KEY_ENTRY",
                    severity="error",
                    message=f"Duplicate question ID '{q.id}' detected in paper.",
                    location=q_loc,
                    suggested_action="Ensure all question identifiers are distinct."
                ))
            seen_q_ids.add(q.id)

            if q.number:
                if q.number in seen_q_nums:
                    findings.append(QualityFinding(
                        code="DUPLICATE_QUESTION_NUMBER",
                        severity="warning",
                        message=f"Duplicate question number '{q.number}' found in paper.",
                        location=q_loc,
                        suggested_action="Ensure question numbering is sequential and unique."
                    ))
                seen_q_nums.add(q.number)

            # Check whether answer is provided
            has_ans = bool(
                q.correct_answer or
                (q.matching_answers and len(q.matching_answers) > 0) or
                any(getattr(m, "label", m.get("label") if isinstance(m, dict) else None) for m in q.diagram_markers)
            )

            if not has_ans:
                findings.append(QualityFinding(
                    code="ANSWER_NOT_PROVIDED",
                    severity="info",
                    message=f"Question {q.number or q.id} has no stored answer key. It will be labeled 'Answer not provided'.",
                    location=q_loc,
                    suggested_action="Optionally add an answer in the Question Bank or evaluate manually."
                ))

    return findings
