import pytest
from pathlib import Path
try:
    import pymupdf as fitz
except ImportError:
    import fitz

from backend.app.services.question_parser import parse_questions_text
from backend.app.services.pdf_generator import generate_pdf
from backend.app.services.pdf_analyzer import analyze_reference_pdf
from backend.app.services.pdf_review_service import (
    normalize_text,
    verify_content_integrity,
    review_pdf_preservation
)
from backend.app.models.schemas import PaperConfig, Section, Question, SubQuestion

FIXTURES_DIR = Path(__file__).parent.parent / "test_fixtures"

def test_text_normalization_rules():
    """
    Test text normalization handling:
    - Smart quotes and dashes
    - Repeated whitespace and line breaks
    - Variable blank representations (e.g. ____ -> ___)
    - Unicode decomposition
    """
    sample_text = "‘Photosynthesis’—in   plant’s   cells:   water & CO2 ______.\n\t(100% natural)"
    norm = normalize_text(sample_text)
    assert "'" in norm
    assert "-" in norm
    assert "___" in norm
    assert "  " not in norm
    assert "\n" not in norm
    assert "photosynthesis" in norm

@pytest.mark.parametrize("scenario,questions_input,expected_min_items", [
    (
        "single_section_mcq",
        """
A. MULTIPLE CHOICE QUESTIONS
1. What is the unit of electric current?
(a) Volt   (b) Ampere   (c) Ohm   (d) Watt
2. Which planet is closest to the Sun?
(a) Venus   (b) Mars   (c) Mercury   (d) Jupiter
""",
        2
    ),
    (
        "multi_section_with_subquestions",
        """
SECTION I: SHORT ANSWER
1. State Newton's second law of motion. (2 marks)
2. Define acceleration due to gravity. (2 marks)

SECTION II: DETAILED QUESTIONS
3. Answer the following:
(a) Derive the kinematic equation v^2 = u^2 + 2as. (5 marks)
(b) Calculate the stopping distance of a vehicle with initial velocity 20 m/s. (5 marks)
""",
        3
    ),
    (
        "fill_in_the_blanks_and_blanks",
        """
PART A — FILL IN THE BLANKS
1. The chemical formula of ozone is ________.
2. Plants store excess glucose in the form of ________.
3. The speed of light in vacuum is approximately ________ m/s.
""",
        3
    )
])
def test_dynamic_generation_and_content_validation(scenario, questions_input, expected_min_items):
    """
    Verifies that arbitrary user-provided content with different section counts,
    question formats, subquestions, and MCQs are:
    1. Fully parsed dynamically from user input.
    2. Generated without content omission or dropped questions.
    3. Successfully validated by the dynamic content validation engine.
    """
    ref_file = FIXTURES_DIR / "ref1_cbse_worksheet.pdf"
    assert ref_file.exists()

    analysis = analyze_reference_pdf(ref_file)
    parsed = parse_questions_text(questions_input)
    assert len(parsed.sections) >= 1
    total_q = sum(len(s.questions) for s in parsed.sections)
    assert total_q >= expected_min_items

    config = PaperConfig(
        subject_name="Physics & General Science",
        page_size="A4",
        use_reference_header=True
    )

    gen_pdf, page_count = generate_pdf(
        sections=parsed.sections,
        config=config,
        reference_style=analysis
    )
    assert gen_pdf.exists()
    assert page_count >= 1

    doc = fitz.open(gen_pdf)
    expected_changes, content_errors, summary = verify_content_integrity(parsed.sections, doc)

    # All items must be validated without hardcoding expected strings
    assert summary["total_items"] == total_q
    assert summary["items_not_found"] == 0, f"Expected zero dropped questions, got {content_errors}"
    assert summary["items_fully_found"] >= expected_min_items
    doc.close()

def test_negative_validation_detects_omitted_content():
    """
    Negative test: If an expected question is NOT present in the PDF,
    the dynamic validation engine must accurately report it as NOT_FOUND.
    """
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(fitz.Point(50, 50), "1. What is gravity?\n2. What is mass?")

    # Sections asking for Question 3 which was never drawn
    missing_sections = [
        Section(
            id="sec1",
            title="SECTION A",
            questions=[
                Question(id="q1", number="1", text="What is gravity?"),
                Question(id="q2", number="2", text="What is mass?"),
                Question(id="q3", number="3", text="Explain quantum entanglement in superconductors.")
            ]
        )
    ]

    expected_changes, content_errors, summary = verify_content_integrity(missing_sections, doc)
    assert summary["total_items"] == 3
    assert summary["items_fully_found"] == 2
    assert summary["items_not_found"] == 1
    assert any(err["title"] == "Question 3 Not Found in Output" for err in content_errors)
    doc.close()

def test_dynamic_regression_varying_options_and_headings():
    """
    Dynamic regression test with:
    - Varying numbers of questions across 3 sections.
    - Varying numbers of options per question (2, 4, 5 options).
    - Varied option labels and punctuation styles: (a), a), a., A.
    - Long options that wrap onto multiple lines.
    - Multiple sections with diverse heading styles.
    """
    ref_file = FIXTURES_DIR / "ref1_cbse_worksheet.pdf"
    analysis = analyze_reference_pdf(ref_file)

    dynamic_text = """
(A) CHOOSE THE BEST ANSWER
1. Which of the following organisms can perform photosynthesis at ocean depths?
(a) Brown algae   (b) Red algae   (c) Green algae   (d) Blue-green bacteria   (e) Diatoms
2. What is the primary function of stomata in plant leaves during transpiration?
a. Transpiration pull regulation
b. Gaseous exchange of carbon dioxide and oxygen
c. Storage of carbohydrates and minerals
d. Water absorption from atmospheric humidity
3. A simple two-choice question:
(a) True   (b) False

PART B — DETAILED REASONING
4. Explain how gravitational force varies with altitude and depth from Earth's surface. (5 marks)
(a) Derive the expression for g at height h above the surface. (3 marks)
(b) Derive the expression for g at depth d below the surface. (2 marks)

SECTION C: SHORT QUESTIONS
5. Define the following physical quantities:
a) Moment of inertia
b) Angular momentum
"""
    parsed = parse_questions_text(dynamic_text)
    assert len(parsed.sections) == 3

    config = PaperConfig(
        subject_name="Advanced Biology & Physics",
        page_size="A4",
        use_reference_header=True
    )

    gen_pdf, page_count = generate_pdf(
        sections=parsed.sections,
        config=config,
        reference_style=analysis
    )
    assert gen_pdf.exists()
    assert page_count >= 1

    doc = fitz.open(gen_pdf)
    expected_changes, content_errors, summary = verify_content_integrity(parsed.sections, doc)

    # 1. Total items match
    total_q = sum(len(s.questions) for s in parsed.sections)
    assert summary["total_items"] == total_q

    # 2. Zero dropped questions
    assert summary["items_not_found"] == 0, f"Expected 0 dropped questions, got errors: {content_errors}"

    # 3. All options detected dynamically without hardcoding
    assert summary["total_options"] >= 11
    assert summary["options_missing"] == 0, f"Options missing: {content_errors}"

    # 4. All 3 sections verified
    assert summary["sections_missing"] == 0, f"Section missing: {content_errors}"

    # 5. Diagnostic details present
    for d in summary["details"]:
        assert d["status"] == "FOUND"
        assert d["page_number"] is not None

    doc.close()

def test_dynamic_validation_genuinely_absent_options():
    """
    Negative test: When options are genuinely omitted from PDF text,
    the validator accurately flags the question as PARTIAL and confirms missing options.
    """
    doc = fitz.open()
    page = doc.new_page()
    # Question 1 text is rendered, but only options a and b are inserted; c and d are omitted
    page.insert_text(fitz.Point(50, 50), "1. Which planet has rings?\n(a) Saturn   (b) Jupiter")

    sections = [
        Section(
            id="sec1",
            title="SECTION A",
            questions=[
                Question(
                    id="q1",
                    number="1",
                    text="Which planet has rings?",
                    options=["(a) Saturn", "(b) Jupiter", "(c) Uranus", "(d) Mars"]
                )
            ]
        )
    ]

    expected_changes, content_errors, summary = verify_content_integrity(sections, doc)
    assert summary["total_items"] == 1
    assert summary["items_partially_found"] == 1
    assert summary["items_fully_found"] == 0
    assert summary["options_missing"] == 2
    assert any("Option '(c) Uranus'" in err["description"] for err in content_errors)
    doc.close()

def test_dynamic_validation_whitespace_and_punctuation_variations():
    """
    Tests that dynamic text matching correctly handles whitespace, line breaks,
    punctuation variations, and label styles without false negatives.
    """
    doc = fitz.open()
    page = doc.new_page()
    # In PDF, text has varying parentheses, multiple spaces, line wraps
    page.insert_text(
        fitz.Point(50, 50),
        "B. CHOOSE THE CORRECT ANSWER\n"
        "1. Which animal gives birth to babies?\n"
        "   a) Hen     b. Duck     (c) Cow     d- Sparrow"
    )

    sections = [
        Section(
            id="sec1",
            title="(B) CHOOSE THE CORRECT ANSWER",  # Input has (B) while PDF has B.
            questions=[
                Question(
                    id="q1",
                    number="1",
                    text="Which animal gives birth to babies?",
                    options=["(a) Hen", "b) Duck", "c. Cow", "(d) Sparrow"]
                )
            ]
        )
    ]

    expected_changes, content_errors, summary = verify_content_integrity(sections, doc)
    assert summary["sections_missing"] == 0
    assert summary["items_fully_found"] == 1
    assert summary["items_partially_found"] == 0
    assert summary["items_not_found"] == 0
    assert summary["options_missing"] == 0
    doc.close()

