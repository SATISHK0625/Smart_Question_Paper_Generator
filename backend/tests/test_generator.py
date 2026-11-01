import pytest
from pathlib import Path
try:
    import pymupdf as fitz
except ImportError:
    import fitz
from backend.app.models.schemas import Section, Question, SubQuestion, PaperConfig, ReferenceAnalysis
from backend.app.services.pdf_generator import generate_pdf
from backend.app.utils.file_utils import cleanup_file

def test_generate_pdf_standard():
    config = PaperConfig(
        institution_name="National University of Technology",
        department="Department of Computer Science & Engineering",
        exam_name="End Semester Examination - Autumn 2026",
        subject_name="Data Structures and Algorithms",
        subject_code="CS301",
        semester_class="Semester 5",
        duration="3 Hours",
        maximum_marks=50.0,
        general_instructions=["Answer all questions.", "Scientific calculators are permitted."],
        page_size="A4",
        header_style="boxed",
        show_page_numbers=True,
        overview_placement="separate"
    )

    sec1 = Section(
        id="sec-1",
        title="SECTION A",
        instructions="Answer all questions. Each carries 5 marks.",
        questions=[
            Question(id="q1", number="1", text="Define Big-O notation with an example.", marks=5.0),
            Question(id="q2", number="2", text="What is a double-ended queue?", marks=5.0)
        ]
    )

    pdf_path, page_count = generate_pdf([sec1], config)
    try:
        assert pdf_path.exists()
        assert page_count >= 1
        
        # Verify with fitz
        doc = fitz.open(pdf_path)
        assert len(doc) == page_count
        first_page_text = doc[0].get_text("text")
        assert "NATIONAL UNIVERSITY" in first_page_text
        assert "Data Structures" in first_page_text
        assert "Big-O notation" in first_page_text
        doc.close()
    finally:
        cleanup_file(pdf_path)

def test_generate_overview_pdf():
    config = PaperConfig(
        institution_name="State College",
        exam_name="Mid-Term Test",
        subject_name="Physics",
        maximum_marks=20.0
    )
    sec = Section(
        id="s1",
        title="SECTION A",
        questions=[
            Question(id="q1", number="1", text="State Coulomb's Law.", marks=10.0),
            Question(id="q2", number="2", text="State Gauss's Law.", marks=10.0),
        ]
    )
    pdf_path, page_count = generate_pdf([sec], config, is_overview_only=True)
    try:
        assert pdf_path.exists()
        doc = fitz.open(pdf_path)
        text = doc[0].get_text("text")
        assert "OVERVIEW" in text
        assert "Total Questions" in text
        doc.close()
    finally:
        cleanup_file(pdf_path)
