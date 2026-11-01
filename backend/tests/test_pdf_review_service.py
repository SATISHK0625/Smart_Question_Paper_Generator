import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.pdf_review_service import review_pdf_preservation
from backend.app.services.question_parser import parse_questions_text
from backend.app.services.pdf_generator import generate_pdf
from backend.app.services.pdf_analyzer import analyze_reference_pdf
from backend.app.models.schemas import PaperConfig

client = TestClient(app)

FIXTURES_DIR = Path(__file__).parent.parent / "test_fixtures"

def test_pdf_review_preservation_service():
    ref_file = FIXTURES_DIR / "ref1_cbse_worksheet.pdf"
    assert ref_file.exists()

    analysis = analyze_reference_pdf(ref_file)
    parsed = parse_questions_text("A. SECTION ONE\n1. What is water? (1 mark)\n2. What is ice? (1 mark)")
    config = PaperConfig(subject_name="Chemistry", page_size="A4", use_reference_header=True)

    gen_pdf, _ = generate_pdf(parsed.sections, config, reference_style=analysis)
    assert gen_pdf.exists()

    # Perform Stage Three Review
    results = review_pdf_preservation(ref_file, gen_pdf)
    assert results["status"] == "success"
    assert results["fidelity_score"] >= 85
    assert len(results["passes"]) >= 3
    assert any("dimensions" in p.lower() for p in results["passes"])
    assert any("border" in p.lower() for p in results["passes"])
    assert len(results["side_by_side_images"]) >= 1

def test_api_review_endpoint():
    ref_file = FIXTURES_DIR / "ref2_university_exam.pdf"
    with open(ref_file, "rb") as f:
        resp_upload = client.post(
            "/api/reference/analyze",
            files={"file": ("ref2_university_exam.pdf", f, "application/pdf")}
        )
    assert resp_upload.status_code == 200
    analysis = resp_upload.json()
    ref_id = analysis["reference_id"]

    payload = {
        "sections": [
            {
                "id": "s1",
                "title": "SECTION A",
                "questions": [
                    {"id": "q1", "number": "1", "text": "Explain virtual memory.", "marks": 5}
                ]
            }
        ],
        "config": {
            "page_size": "Letter",
            "reference_id": ref_id
        },
        "reference_style": analysis
    }

    resp_review = client.post("/api/paper/review", json=payload)
    assert resp_review.status_code == 200
    review_data = resp_review.json()
    assert review_data["status"] == "success"
    assert review_data["fidelity_score"] >= 85
    assert len(review_data["passes"]) >= 2
