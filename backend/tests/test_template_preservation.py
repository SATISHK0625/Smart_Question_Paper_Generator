import pytest
from pathlib import Path
try:
    import pymupdf as fitz
except ImportError:
    import fitz

from backend.app.services.pdf_analyzer import analyze_reference_pdf
from backend.app.services.question_parser import parse_questions_text
from backend.app.services.pdf_generator import generate_pdf
from backend.app.models.schemas import PaperConfig
from backend.app.utils.file_utils import cleanup_file

FIXTURES_DIR = Path(__file__).parent.parent / "test_fixtures"

def test_template_preservation_elements():
    ref_pdf = FIXTURES_DIR / "Class 4 - WORK SHEET 7.pdf"
    assert ref_pdf.exists(), "Reference PDF must exist"

    # Analyze reference
    analysis = analyze_reference_pdf(ref_pdf)
    assert analysis.document_type == "worksheet"
    assert analysis.has_page_border is True
    assert analysis.has_header_divider is True
    assert len(analysis.header_lines) >= 3

    # Input text with new questions
    animal_text_path = FIXTURES_DIR / "animal_life_input.txt"
    raw_text = animal_text_path.read_text(encoding="utf-8")
    parsed = parse_questions_text(raw_text)
    assert len(parsed.sections) == 3

    config = PaperConfig(
        subject_name="Science",
        semester_class="Class 5",
        page_size="A4",
        use_reference_header=True,
        show_page_numbers=False
    )

    gen_pdf, page_count = generate_pdf(
        sections=parsed.sections,
        config=config,
        reference_style=analysis
    )

    try:
        assert gen_pdf.exists()
        assert page_count in (2, 3), f"Expected 2 or 3 pages matching worksheet content, got {page_count}"

        doc = fitz.open(gen_pdf)

        # 1. Verify original logo is retained on page 1
        p0 = doc[0]
        images = p0.get_images()
        assert len(images) >= 1, "Original school logo image must be present on page 1"
        logo_rects = p0.get_image_rects(images[0][0])
        assert len(logo_rects) >= 1, "Logo rect must be located on page 1"
        logo_rect = logo_rects[0]
        assert logo_rect.y0 < p0.rect.height * 0.2, "Logo must remain in original top header position"

        # 2. Verify complete rectangular page border on every page
        for pno, page in enumerate(doc):
            drawings = page.get_drawings()
            # Rectangular border is a rect drawing covering >=80% of page width and height
            has_border = any(
                (d.get("rect") and (d["rect"][2] - d["rect"][0]) > page.rect.width * 0.8 and (d["rect"][3] - d["rect"][1]) > page.rect.height * 0.8)
                for d in drawings
            )
            assert has_border, f"Page {pno+1} must retain the complete rectangular page border"

        # 3. Verify horizontal divider rule beneath header on page 1
        p0_drawings = p0.get_drawings()
        has_divider = False
        for d in p0_drawings:
            r = d.get("rect")
            if r:
                rw = r[2] - r[0]
                rh = r[3] - r[1]
                if rw > p0.rect.width * 0.55 and rh <= 4.0 and (45.0 <= r[1] <= p0.rect.height * 0.28):
                    has_divider = True
                    break
        assert has_divider, "Horizontal divider beneath header must be preserved"

        # 4. Verify text content: School Name, Class 5 Science, WORKSHEET title
        p0_text = p0.get_text("text")
        assert "SRC GLOBAL CBSE SCHOOL" in p0_text, "School name must be present and preserved"
        assert "Class 5" in p0_text or "SCIENCE" in p0_text, "Subject/Grade heading must be present"
        assert "WORKSHEET" in p0_text, "WORKSHEET title must be present"

        # 5. Verify new question content replaces old content
        assert "A. FILL IN THE BLANKS" in p0_text, "Section A heading must be replaced with new section title"
        assert "Animals that give birth to babies" in p0_text, "New question 1 text must be present"
        assert "king of jungle" in p0_text, "New question 8 text must be present"

        # 6. Verify Section B, options, and Section C are present in document
        all_text = "".join(page.get_text("text") for page in doc)
        assert "B. CHOOSE THE CORRECT ANSWER" in all_text, "Section B must be present"
        assert "Which animal" in all_text, "Section B question must be present"
        assert "Cow" in all_text or "Hen" in all_text or "Dog" in all_text, "Options must be present"

        # 7. Verify Section C
        assert "C. NAME THE FOLLOWING" in all_text, "Section C must be present"
        assert "animals" in all_text, "Section C questions must be present"

        # 8. Verify no unwanted college exam metadata was introduced
        for page in doc:
            p_text = page.get_text("text")
            assert "CS402" not in p_text, "No CS402 code"
            assert "Semester 4" not in p_text, "No Semester 4 code"
            assert "Maximum Marks: 30" not in p_text, "No invented maximum marks metadata"
            assert "SECTION A" not in p_text, "No generic SECTION A banner"

        doc.close()
    finally:
        cleanup_file(gen_pdf)

def test_fallback_when_no_reference():
    """Ensure ReportLab fallback still works when no reference PDF is supplied."""
    parsed = parse_questions_text("1. What is photosynthesis?\n2. What is respiration?")
    config = PaperConfig(
        subject_name="Biology",
        exam_name="Midterm Examination",
        page_size="A4"
    )
    gen_pdf, page_count = generate_pdf(
        sections=parsed.sections,
        config=config,
        reference_style=None
    )
    try:
        assert gen_pdf.exists()
        assert page_count >= 1
        doc = fitz.open(gen_pdf)
        txt = doc[0].get_text("text")
        assert "Biology" in txt or "Midterm" in txt
        assert "photosynthesis" in txt
        doc.close()
    finally:
        cleanup_file(gen_pdf)
