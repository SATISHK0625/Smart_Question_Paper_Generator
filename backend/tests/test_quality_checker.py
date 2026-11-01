import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import Section, Question, PaperConfig
from app.services.quality_checker import (
    validate_structured_paper_content,
    run_pre_export_quality_check
)
from app.services.pdf_generator import generate_pdf

client = TestClient(app)


def test_quality_checker_detects_empty_question_and_section():
    # Empty question text and empty section title
    sec = Section(
        id="s1",
        title="",
        questions=[
            Question(id="q1", number="1", text="", marks=1.0)
        ]
    )
    findings = validate_structured_paper_content([sec])
    error_codes = [f.code for f in findings if f.severity == "error"]
    assert "EMPTY_SECTION_TITLE" in error_codes
    assert "EMPTY_QUESTION_TEXT" in error_codes


def test_quality_checker_mcq_option_rules():
    sec = Section(
        id="s1",
        title="SECTION A",
        questions=[
            Question(
                id="q1",
                number="1",
                text="Choose the correct answer:",
                question_type="mcq",
                options=["Only One Option"]
            ),
            Question(
                id="q2",
                number="2",
                text="Which of these are fruits?",
                question_type="mcq",
                options=["Apple", "Apple", "Banana"]
            )
        ]
    )
    findings = validate_structured_paper_content([sec])
    codes = [f.code for f in findings]
    assert "INSUFFICIENT_MCQ_OPTIONS" in codes
    assert "DUPLICATE_OPTION_VALUE" in codes


def test_quality_checker_matching_rules():
    sec = Section(
        id="s1",
        title="MATCHING SECTION",
        questions=[
            Question(
                id="q1",
                number="1",
                text="Match Column A with Column B",
                question_type="matching",
                matching_left=["Item A1"],
                matching_right=["Item B1"]
            ),
            Question(
                id="q2",
                number="2",
                text="Match items",
                question_type="matching",
                matching_left=["A", "B", "C"],
                matching_right=["1", "2"]
            )
        ]
    )
    findings = validate_structured_paper_content([sec])
    codes = [f.code for f in findings]
    assert "INSUFFICIENT_MATCHING_PAIRS" in codes
    assert "UNBALANCED_MATCHING_COLUMNS" in codes


def test_quality_checker_marks_and_blueprint():
    sec = Section(
        id="s1",
        title="SECTION A",
        questions=[
            Question(id="q1", number="1", text="Question 1", marks=5.0),
            Question(id="q2", number="2", text="Question 2", marks=10.0),
        ]
    )
    cfg = PaperConfig(subject_name="Physics", maximum_marks=20.0) # Sum is 15, expected 20
    findings = validate_structured_paper_content([sec], cfg)
    codes = [f.code for f in findings]
    assert "MARKS_MISMATCH" in codes


def test_quality_checker_blocks_export_on_errors():
    invalid_sec = Section(
        id="s1",
        title="SECTION A",
        questions=[
            Question(id="q1", number="1", text="", marks=1.0) # Empty text
        ]
    )
    report = run_pre_export_quality_check([invalid_sec])
    assert report.can_export is False
    assert report.status == "blocked"
    assert report.error_count > 0


def test_api_generate_enforces_quality_gate():
    # Calling /api/paper/generate with empty question text must return 400
    payload = {
        "sections": [
            {
                "id": "s1",
                "title": "SECTION A",
                "questions": [
                    {
                        "id": "q1",
                        "number": "1",
                        "text": "",
                        "marks": 1.0,
                        "options": []
                    }
                ]
            }
        ],
        "config": {
            "subject_name": "Mathematics",
            "page_size": "A4"
        }
    }
    res = client.post("/api/paper/generate", json=payload)
    assert res.status_code == 400
    data = res.json()
    assert "detail" in data
    assert "Quality Assurance Gate" in data["detail"]["message"] or "validation_errors" in data["detail"]


def test_api_quality_check_endpoint():
    payload = {
        "sections": [
            {
                "id": "s1",
                "title": "SECTION A",
                "questions": [
                    {
                        "id": "q1",
                        "number": "1",
                        "text": "What is the capital of France?",
                        "question_type": "mcq",
                        "marks": 1.0,
                        "options": ["Paris", "London", "Berlin", "Rome"]
                    }
                ]
            }
        ],
        "config": {
            "subject_name": "Geography",
            "page_size": "A4"
        }
    }
    res = client.post("/api/paper/quality-check", json=payload)
    assert res.status_code == 200
    report = res.json()
    assert report["can_export"] is True
    assert report["error_count"] == 0
    assert report["total_questions"] == 1
    assert report["status"] in ["passed", "has_warnings"]
