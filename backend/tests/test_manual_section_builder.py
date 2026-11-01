import pytest
from pathlib import Path
try:
    import pymupdf as fitz
except ImportError:
    import fitz
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.schemas import Section, Question, SubQuestion, PaperConfig, GeneratePaperRequest
from backend.app.services.pdf_generator import generate_pdf
from backend.app.services.pdf_analyzer import analyze_reference_pdf
from backend.app.services.pdf_review_service import (
    verify_content_integrity,
    review_pdf_preservation,
    render_pdf_pages_to_images
)

client = TestClient(app)
FIXTURES_DIR = Path(__file__).parent.parent / "test_fixtures"

def test_manual_builder_data_structure_and_reordering():
    """
    Test 1: Tests adding, editing, deleting, and reordering sections and questions
    in the manual section builder data representation.
    """
    # 1. Start with 2 sections
    sec_a = Section(
        id="sec-a",
        title="SECTION A — OBJECTIVE",
        question_type="mcq",
        questions=[
            Question(id="q1", number="1", text="What is the speed of light?", marks=1.0, options=["a) 3x10^8 m/s", "b) 3x10^6 m/s"]),
            Question(id="q2", number="2", text="What is the SI unit of force?", marks=1.0, options=["a) Newton", "b) Joule"])
        ]
    )
    sec_b = Section(
        id="sec-b",
        title="SECTION B — THEORY",
        question_type="short_answer",
        questions=[
            Question(id="q3", number="3", text="Define inertia.", marks=2.0),
            Question(id="q4", number="4", text="State Newton's third law of motion.", marks=2.0)
        ]
    )

    sections = [sec_a, sec_b]
    assert len(sections) == 2
    assert sections[0].title == "SECTION A — OBJECTIVE"

    # 2. Add question to Section A
    new_q = Question(id="q5", number="5", text="Is energy conserved?", marks=1.0, question_type="true_false", options=["a) True", "b) False"])
    sections[0].questions.append(new_q)
    assert len(sections[0].questions) == 3

    # 3. Edit Section B title and question 3 text
    sections[1].title = "SECTION B — REVISED THEORY"
    sections[1].questions[0].text = "Define inertia of rest and inertia of motion."
    sections[1].questions[0].marks = 3.0
    assert sections[1].title == "SECTION B — REVISED THEORY"
    assert sections[1].questions[0].marks == 3.0

    # 4. Reorder questions in Section A (move last question to first)
    moved_q = sections[0].questions.pop(2)
    sections[0].questions.insert(0, moved_q)
    assert sections[0].questions[0].id == "q5"
    assert sections[0].questions[1].id == "q1"

    # 5. Delete a question
    sections[0].questions.pop(1) # delete q1
    assert len(sections[0].questions) == 2

    # 6. Reorder sections (swap Section A and Section B)
    sections = [sections[1], sections[0]]
    assert sections[0].id == "sec-b"
    assert sections[1].id == "sec-a"

    # 7. Add a new section
    sec_c = Section(
        id="sec-c",
        title="SECTION C — EXTENDED",
        question_type="long_answer",
        questions=[
            Question(id="q6", number="6", text="Derive the work-energy theorem for a variable force.", marks=5.0)
        ]
    )
    sections.append(sec_c)
    assert len(sections) == 3

    # Verify serialization through Pydantic
    payload = GeneratePaperRequest(
        sections=sections,
        config=PaperConfig(subject_name="Mechanics", institution_name="Test College", maximum_marks=12.0)
    )
    assert len(payload.sections) == 3
    assert payload.sections[0].question_type == "short_answer"
    assert payload.sections[1].question_type == "mcq"
    assert payload.sections[2].question_type == "long_answer"

def test_manual_builder_validation_errors():
    """
    Test 2: Test empty fields and invalid data in manual builder payload.
    Ensures clear validation error messages are returned rather than crashing or silent drops.
    """
    config = {"institution_name": "Test Academy", "subject_name": "Validation Test"}

    # 1. Empty sections list
    resp1 = client.post("/api/paper/preview", json={"sections": [], "config": config})
    assert resp1.status_code == 400
    assert "At least one section is required" in resp1.text

    # 2. Missing section title
    bad_section_title = [
        {
            "id": "s1",
            "title": "   ",
            "questions": [{"id": "q1", "number": "1", "text": "Valid question text.", "marks": 2.0}]
        }
    ]
    resp2 = client.post("/api/paper/preview", json={"sections": bad_section_title, "config": config})
    assert resp2.status_code == 400
    assert "Section title is required" in resp2.text

    # 3. Missing question text
    bad_q_text = [
        {
            "id": "s1",
            "title": "SECTION 1",
            "questions": [{"id": "q1", "number": "1", "text": "   ", "marks": 2.0}]
        }
    ]
    resp3 = client.post("/api/paper/preview", json={"sections": bad_q_text, "config": config})
    assert resp3.status_code == 400
    assert "Question text cannot be empty" in resp3.text

    # 4. MCQ with missing options (0 or 1 options)
    bad_mcq_opts = [
        {
            "id": "s1",
            "title": "SECTION 1",
            "question_type": "mcq",
            "questions": [
                {
                    "id": "q1",
                    "number": "1",
                    "text": "Which element is a noble gas?",
                    "marks": 1.0,
                    "question_type": "mcq",
                    "options": ["a) Helium"] # Only 1 option!
                }
            ]
        }
    ]
    resp4 = client.post("/api/paper/preview", json={"sections": bad_mcq_opts, "config": config})
    assert resp4.status_code == 400
    assert "Multiple Choice questions require at least 2 options" in resp4.text

def test_manual_builder_mcq_long_options_and_lengths():
    """
    Test 3: Test MCQs with long options and questions of varying lengths.
    Ensures text wrapping and measurement prevent omission.
    """
    ref_file = FIXTURES_DIR / "ref1_cbse_worksheet.pdf"
    assert ref_file.exists()
    analysis = analyze_reference_pdf(ref_file)

    long_question_text = (
        "In a classic molecular biology experiment designed to evaluate the rate of photosynthetic carbon "
        "fixation under varying monochromatic wavelength regimes, several plant specimens were subjected to "
        "calibrated radiometric illumination under controlled atmospheric conditions. Based on your understanding "
        "of light-dependent electron transport and RuBisCO enzymatic kinetics, evaluate the primary physiological bottleneck."
    )

    long_options = [
        "a) The rate-limiting phosphorylation of ribulose 1,5-bisphosphate due to localized ATP synthase saturation in the thylakoid lumen.",
        "b) The photoinhibition of Photosystem II reaction centers under excessive blue photon flux densities resulting in reactive oxygen species.",
        "c) The competitive binding affinity of atmospheric oxygen at the catalytic active site of ribulose-1,5-bisphosphate carboxylase-oxygenase.",
        "d) The depletion of stromal NADP+ acceptors leading to cyclical photophosphorylation decoupling and stomatal conductance arrest."
    ]

    short_question_text = "What is ATP?"
    short_options = ["a) Energy currency", "b) Nucleic acid", "c) Lipid molecule", "d) Amino acid"]

    sections = [
        Section(
            id="sec_mcq_long",
            title="SECTION A — ADVANCED MCQ",
            question_type="mcq",
            questions=[
                Question(id="q1", number="1", text=short_question_text, marks=1.0, options=short_options, question_type="mcq"),
                Question(id="q2", number="2", text=long_question_text, marks=2.0, options=long_options, question_type="mcq")
            ]
        )
    ]

    config = PaperConfig(
        subject_name="Cellular Biochemistry",
        institution_name="Advanced Research Institute",
        page_size="A4",
        use_reference_header=True
    )

    pdf_path, page_count = generate_pdf(sections=sections, config=config, reference_style=analysis)
    assert pdf_path.exists()
    assert page_count >= 1

    doc = fitz.open(pdf_path)
    expected_changes, content_errors, summary = verify_content_integrity(sections, doc)
    doc.close()

    assert summary["total_items"] == 2
    assert summary["items_not_found"] == 0, f"Expected 0 dropped items, got errors: {content_errors}"
    assert summary["items_fully_found"] == 2

def test_manual_builder_short_and_long_answer_sections():
    """
    Test 4: Test short-answer and long-answer sections with subquestions and Fill in the Blanks.
    """
    ref_file = FIXTURES_DIR / "ref1_cbse_worksheet.pdf"
    analysis = analyze_reference_pdf(ref_file)

    sec_short = Section(
        id="sec_short",
        title="SECTION A — SHORT CONCEPTUAL QUESTIONS",
        question_type="short_answer",
        instructions="Answer in 1–2 sentences.",
        questions=[
            Question(id="q1", number="1", text="Define electric flux through an arbitrary closed surface.", marks=2.0, question_type="short_answer"),
            Question(id="q2", number="2", text="State Lenz's law of electromagnetic induction.", marks=2.0, question_type="short_answer"),
            Question(id="q3", number="3", text="The SI unit of magnetic field strength is ________.", marks=1.0, question_type="fill_in_the_blanks")
        ]
    )

    sec_long = Section(
        id="sec_long",
        title="SECTION B — LONG PROBLEMS & DERIVATIONS",
        question_type="long_answer",
        instructions="Show complete mathematical working.",
        questions=[
            Question(
                id="q4",
                number="4",
                text="A parallel plate capacitor is connected across a variable DC voltage supply.",
                marks=5.0,
                question_type="long_answer",
                subquestions=[
                    SubQuestion(id="sq1", label="(a)", text="Derive the expression for electric field between the plates.", marks=2.5),
                    SubQuestion(id="sq2", label="(b)", text="Calculate the stored electrostatic energy if plate separation is doubled.", marks=2.5)
                ]
            ),
            Question(
                id="q5",
                number="5",
                text="State True or False: Superconductors exhibit perfect diamagnetism below critical temperature.",
                marks=1.0,
                question_type="true_false",
                options=["a) True", "b) False"]
            )
        ]
    )

    sections = [sec_short, sec_long]
    config = PaperConfig(
        subject_name="Electrodynamics",
        institution_name="National Engineering Institute",
        maximum_marks=11.0,
        page_size="A4",
        use_reference_header=True
    )

    pdf_path, page_count = generate_pdf(sections=sections, config=config, reference_style=analysis)
    assert pdf_path.exists()

    doc = fitz.open(pdf_path)
    expected_changes, content_errors, summary = verify_content_integrity(sections, doc)
    doc.close()

    assert summary["total_items"] == 5
    assert summary["items_not_found"] == 0, f"Dropped items found: {content_errors}"
    assert summary["items_fully_found"] == 5

def test_manual_builder_multiple_reference_layouts():
    """
    Test 5: Test manual section builder generation with multiple reference PDFs having different layouts:
    - ref1_cbse_worksheet.pdf (worksheet layout with border and logo)
    - ref2_university_exam.pdf (university layout with boxed headers)
    - ref3_medical_quiz.pdf (medical quiz layout)
    """
    reference_names = [
        "ref1_cbse_worksheet.pdf",
        "ref2_university_exam.pdf",
        "ref3_medical_quiz.pdf"
    ]

    builder_sections = [
        Section(
            id="s1",
            title="PART I: FUNDAMENTAL PRINCIPLES",
            question_type="mcq",
            questions=[
                Question(id="q1", number="1", text="Which organelle synthesizes ATP?", marks=1.0, options=["a) Mitochondria", "b) Ribosome", "c) Golgi", "d) Nucleus"]),
                Question(id="q2", number="2", text="DNA replication occurs during the S phase of interphase.", marks=1.0, options=["a) True", "b) False"])
            ]
        ),
        Section(
            id="s2",
            title="PART II: APPLICATION & ANALYSIS",
            question_type="short_answer",
            questions=[
                Question(id="q3", number="3", text="Explain the function of hemoglobin in erythrocyte gas transport.", marks=3.0),
                Question(id="q4", number="4", text="Enzymes lower the ________ energy of biochemical reactions.", marks=1.0)
            ]
        )
    ]

    for ref_name in reference_names:
        ref_path = FIXTURES_DIR / ref_name
        if not ref_path.exists():
            continue

        analysis = analyze_reference_pdf(ref_path)
        assert analysis.page_count >= 1

        config = PaperConfig(
            subject_name="Cellular & Human Physiology",
            institution_name="Health Sciences University",
            page_size=analysis.page_size if analysis.page_size in ["A4", "Letter"] else "A4",
            use_reference_header=True
        )

        pdf_path, pages = generate_pdf(sections=builder_sections, config=config, reference_style=analysis)
        assert pdf_path.exists()
        assert pages >= 1

        # Content preservation validation
        doc = fitz.open(pdf_path)
        expected_changes, content_errors, summary = verify_content_integrity(builder_sections, doc)
        doc.close()

        assert summary["items_not_found"] == 0, f"Reference '{ref_name}' failed with dropped content: {content_errors}"
        assert summary["items_fully_found"] == 4

        # Visual review & rendering comparison
        review_result = review_pdf_preservation(
            reference_pdf_path=ref_path,
            generated_pdf_path=pdf_path,
            sections=builder_sections,
            config=config
        )
        assert review_result["status"] in ["success", "warning"]
        assert review_result["validation_status"] in ["PASS", "WARNING"]
        assert review_result["fidelity_score"] >= 75
