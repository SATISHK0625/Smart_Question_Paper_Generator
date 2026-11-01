import pytest
from pathlib import Path
from fastapi.testclient import TestClient
import pymupdf as fitz

from app.main import app
from app.models.schemas import Section, Question, PaperConfig, DiagramMarker
from app.services.pdf_generator import generate_pdf
from app.services.answer_key_service import generate_teacher_answer_key_pdf, extract_teacher_answer_metadata
from app.services.quality_checker import run_pre_export_quality_check

client = TestClient(app)


def build_test_exam_paper():
    """Builds a rich examination paper covering all supported question types."""
    sec1 = Section(
        id="sec_1",
        title="Section A: Multiple Choice Questions",
        instructions="Choose the correct answer for each question.",
        question_type="mcq",
        questions=[
            Question(
                id="q_mcq_1",
                number="1",
                text="What is the chemical formula of Water?",
                marks=1.0,
                options=["a) CO2", "b) H2O", "c) NaCl", "d) CH4"],
                correct_answer="b) H2O",
                explanation="Water consists of two hydrogen atoms and one oxygen atom.",
                question_type="mcq"
            ),
            Question(
                id="q_mcq_2",
                number="2",
                text="Which planet is known as the Red Planet?",
                marks=1.0,
                options=["a) Venus", "b) Mars", "c) Jupiter", "d) Saturn"],
                correct_answer="b) Mars",
                explanation="Mars appears reddish due to iron oxide on its surface.",
                question_type="mcq"
            ),
            Question(
                id="q_mcq_no_ans",
                number="3",
                text="Sample question with no stored answer key.",
                marks=1.0,
                options=["a) Choice 1", "b) Choice 2"],
                correct_answer="", # No answer provided
                explanation="",
                question_type="mcq"
            )
        ]
    )

    sec2 = Section(
        id="sec_2",
        title="Section B: Match the Following & Fill in the Blanks",
        instructions="Answer the following questions:",
        question_type="mixed",
        questions=[
            Question(
                id="q_match_1",
                number="4",
                text="Match the organ with its primary function:",
                marks=3.0,
                question_type="matching",
                matching_left=["Heart", "Lungs", "Kidneys"],
                matching_right=["Pumps blood", "Gas exchange", "Filters waste"],
                matching_answers={"A": "Pumps blood", "B": "Gas exchange", "C": "Filters waste"}
            ),
            Question(
                id="q_fill_1",
                number="5",
                text="Plants perform photosynthesis using green pigment called ________.",
                marks=1.0,
                question_type="fill_in_the_blanks",
                correct_answer="Chlorophyll",
                alternative_answers=["chlorophyll-a", "chloroplast pigments"],
                explanation="Chlorophyll absorbs sunlight for photosynthesis."
            )
        ]
    )

    sec3 = Section(
        id="sec_3",
        title="Section C: Short and Long Answer Questions",
        instructions="Answer the questions clearly with diagrams where applicable.",
        question_type="mixed",
        questions=[
            Question(
                id="q_short_1",
                number="6",
                text="State Newton's Second Law of Motion.",
                marks=3.0,
                question_type="short_answer",
                correct_answer="Force is directly proportional to rate of change of momentum (F = ma).",
                rubric="1 mark for definition, 1 mark for formula F=ma, 1 mark for SI units (Newtons).",
                key_points=["Force equals mass times acceleration", "SI unit is Newton (N)"],
                explanation="Derived from momentum change delta p over delta t."
            ),
            Question(
                id="q_diagram_1",
                number="7",
                text="Identify the parts of the flower marked (1) and (2).",
                marks=2.0,
                question_type="diagram_identify",
                diagram_mode="numbered_markers",
                diagram_markers=[
                    DiagramMarker(id="m1", number=1, x=0.3, y=0.4, label="Anther"),
                    DiagramMarker(id="m2", number=2, x=0.7, y=0.6, label="Filament")
                ]
            )
        ]
    )

    config = PaperConfig(
        institution_name="Greenwood International Academy",
        exam_name="Annual Examination 2026",
        subject_name="General Science",
        semester_class="Class 9",
        duration="2 Hours",
        maximum_marks=12.0
    )

    return [sec1, sec2, sec3], config


def test_extract_teacher_answer_metadata():
    sections, config = build_test_exam_paper()
    items, summary = extract_teacher_answer_metadata(sections)

    assert summary.total_questions == 7
    assert summary.total_marks == 12.0
    # Q3 has no stored answer
    assert summary.questions_with_answers == 6
    assert summary.questions_missing_answers == 1

    q3_item = next(it for it in items if it.number == "3")
    assert q3_item.status == "not_provided"
    assert q3_item.has_answer is False

    q1_item = next(it for it in items if it.number == "1")
    assert q1_item.correct_answer == "b) H2O"
    assert q1_item.has_answer is True

    q4_item = next(it for it in items if it.number == "4")
    assert q4_item.matching_pairs is not None
    assert "Heart" in q4_item.matching_pairs

    q5_item = next(it for it in items if it.number == "5")
    assert "chlorophyll-a" in q5_item.alternative_answers

    q6_item = next(it for it in items if it.number == "6")
    assert "F=ma" in q6_item.rubric

    q7_item = next(it for it in items if it.number == "7")
    labels = [m.label for m in q7_item.diagram_markers]
    assert "Anther" in labels
    assert "Filament" in labels


def test_generate_teacher_answer_key_pdf():
    sections, config = build_test_exam_paper()
    pdf_path, page_count, summary = generate_teacher_answer_key_pdf(sections, config)

    assert pdf_path.exists()
    assert page_count >= 1

    # Inspect rendered PDF with PyMuPDF
    doc = fitz.open(pdf_path)
    full_text = " ".join(page.get_text() for page in doc)
    doc.close()
    pdf_path.unlink() # Cleanup

    # Verify teacher title and warnings
    assert "TEACHER ANSWER KEY & MARKING SCHEME" in full_text
    assert "CONFIDENTIAL" in full_text

    # Verify answers and rubrics are present in teacher answer key
    assert "b) H2O" in full_text
    assert "b) Mars" in full_text
    assert "Answer not provided" in full_text
    assert "F = ma" in full_text or "F=ma" in full_text
    assert "Anther" in full_text
    assert "Filament" in full_text
    assert "Chlorophyll" in full_text


def test_strict_isolation_student_vs_teacher_pdf():
    """
    CRITICAL SECURITY & PRIVACY REGRESSION TEST:
    Generate both student question paper and teacher answer key from the EXACT SAME paper draft.
    Verify:
    1. Teacher PDF contains answers, rubrics, and explanations.
    2. Student PDF strictly EXCLUDES answers, rubrics, and explanations.
    """
    sections, config = build_test_exam_paper()

    # 1. Generate Student Paper PDF
    student_pdf_path, _ = generate_pdf(
        sections=sections,
        config=config,
        include_overview=False
    )

    # 2. Generate Teacher Answer Key PDF
    teacher_pdf_path, _, _ = generate_teacher_answer_key_pdf(
        sections=sections,
        config=config
    )

    assert student_pdf_path.exists()
    assert teacher_pdf_path.exists()

    student_doc = fitz.open(student_pdf_path)
    student_text = " ".join(p.get_text() for p in student_doc)
    student_doc.close()

    teacher_doc = fitz.open(teacher_pdf_path)
    teacher_text = " ".join(p.get_text() for p in teacher_doc)
    teacher_doc.close()

    # Clean up test PDFs
    student_pdf_path.unlink()
    teacher_pdf_path.unlink()

    # Teacher Document assertions
    assert "TEACHER ANSWER KEY" in teacher_text
    assert "b) H2O" in teacher_text
    assert "b) Mars" in teacher_text
    assert "Chlorophyll" in teacher_text
    assert "Pumps blood" in teacher_text
    assert "Anther" in teacher_text
    assert "1 mark for definition" in teacher_text # Rubric

    # Student Document assertions: STRICT ABSENCE OF TEACHER-ONLY ANSWERS
    assert "TEACHER ANSWER KEY" not in student_text
    assert "CONFIDENTIAL" not in student_text
    assert "Correct Answer:" not in student_text
    assert "Marking Rubric" not in student_text
    assert "1 mark for definition" not in student_text
    assert "Anther" not in student_text # Diagram label must not leak on student paper
    assert "Filament" not in student_text # Diagram label must not leak on student paper
    assert "Answer not provided" not in student_text


def test_api_answer_key_endpoints():
    sections, config = build_test_exam_paper()
    payload = {
        "sections": [s.model_dump() for s in sections],
        "config": config.model_dump()
    }

    # 1. Summary endpoint
    sum_res = client.post("/api/paper/answer-key/summary", json=payload)
    assert sum_res.status_code == 200
    sum_data = sum_res.json()
    assert sum_data["summary"]["total_questions"] == 7
    assert sum_data["summary"]["total_marks"] == 12.0
    assert sum_data["summary"]["questions_with_answers"] == 6

    # 2. Preview endpoint
    prev_res = client.post("/api/paper/answer-key/preview", json=payload)
    assert prev_res.status_code == 200
    assert prev_res.headers["content-type"] == "application/pdf"
    assert len(prev_res.content) > 1000

    # 3. Generate download endpoint
    gen_res = client.post("/api/paper/answer-key/generate", json=payload)
    assert gen_res.status_code == 200
    assert gen_res.headers["content-type"] == "application/pdf"
    assert "attachment" in gen_res.headers["content-disposition"]
    assert len(gen_res.content) > 1000
