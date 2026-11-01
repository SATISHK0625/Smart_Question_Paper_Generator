import pytest
import base64
import io
from pathlib import Path
from PIL import Image, ImageDraw
try:
    import pymupdf as fitz
except ImportError:
    import fitz
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.schemas import Section, Question, DiagramMarker, PaperConfig, GeneratePaperRequest
from backend.app.services.pdf_generator import generate_pdf
from backend.app.services.pdf_analyzer import analyze_reference_pdf
from backend.app.services.pdf_review_service import verify_content_integrity, review_pdf_preservation

client = TestClient(app)
FIXTURES_DIR = Path(__file__).parent.parent / "test_fixtures"

def create_sample_png_base64(width=300, height=200, color="lightblue"):
    """Creates a simple in-memory PNG and returns a data URL."""
    img = Image.new("RGB", (width, height), color=color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, width - 20, height - 20], outline="black", width=3)
    draw.text((40, 80), "Test Diagram Content", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def test_advanced_question_schemas():
    """Verify serialization and validation of advanced question types."""
    sample_img = create_sample_png_base64()

    q_match = Question(
        id="q_match_1",
        number="1",
        text="Match the organelle with its primary function:",
        marks=4.0,
        question_type="matching",
        matching_left=["Mitochondria", "Ribosome", "Chloroplast", "Golgi apparatus"],
        matching_right=["Cellular respiration", "Protein synthesis", "Photosynthesis", "Protein packaging"],
        shuffle_right=True,
        matching_answers={"A": "1", "B": "2", "C": "3", "D": "4"}
    )

    q_img = Question(
        id="q_img_1",
        number="2",
        text="Observe the setup shown below and explain the observed phenomenon:",
        marks=3.0,
        question_type="image_based",
        image_base64=sample_img,
        image_caption="Figure 1: Osmosis Experiment Setup",
        image_width_ratio=0.75
    )

    q_diagram = Question(
        id="q_diag_1",
        number="3",
        text="Identify the numbered parts in the apparatus diagram:",
        marks=5.0,
        question_type="diagram_identify",
        image_base64=sample_img,
        diagram_mode="numbered_markers",
        diagram_markers=[
            DiagramMarker(id="m1", number=1, x=0.25, y=0.30, label="Delivery Tube"),
            DiagramMarker(id="m2", number=2, x=0.65, y=0.70, label="Conical Flask")
        ]
    )

    sec = Section(
        id="sec_adv",
        title="SECTION C: ADVANCED APPLICATION",
        question_type="mixed",
        questions=[q_match, q_img, q_diagram]
    )

    req = GeneratePaperRequest(
        sections=[sec],
        config=PaperConfig(subject_name="General Science", institution_name="Elite Academy", maximum_marks=12.0)
    )

    assert len(req.sections[0].questions) == 3
    assert req.sections[0].questions[0].matching_left[0] == "Mitochondria"
    assert req.sections[0].questions[1].image_caption == "Figure 1: Osmosis Experiment Setup"
    assert len(req.sections[0].questions[2].diagram_markers) == 2
    assert req.sections[0].questions[2].diagram_markers[0].label == "Delivery Tube"


def test_api_validation_advanced_questions():
    """Verify API rejects invalid matching pairs or missing diagram attachments."""
    # 1. Invalid Matching: Mismatched left and right lengths
    bad_matching = {
        "sections": [{
            "id": "s1",
            "title": "SECTION A",
            "questions": [{
                "id": "q1",
                "number": "1",
                "text": "Match the following:",
                "marks": 2.0,
                "question_type": "matching",
                "matching_left": ["Item 1", "Item 2", "Item 3"],
                "matching_right": ["Match 1", "Match 2"] # 3 != 2
            }]
        }],
        "config": {"subject_name": "Test", "institution_name": "Test"}
    }
    resp = client.post("/api/paper/generate", json=bad_matching)
    assert resp.status_code == 400
    assert "Column A and Column B must have the same number of items" in resp.text

    # 2. Invalid Image: Missing image_base64
    bad_img = {
        "sections": [{
            "id": "s1",
            "title": "SECTION A",
            "questions": [{
                "id": "q1",
                "number": "1",
                "text": "Identify the image:",
                "marks": 2.0,
                "question_type": "image_based",
                "image_base64": None
            }]
        }],
        "config": {"subject_name": "Test", "institution_name": "Test"}
    }
    resp = client.post("/api/paper/generate", json=bad_img)
    assert resp.status_code == 400
    assert "Image-based questions require an uploaded image" in resp.text

    # 3. Invalid Diagram: Marker coordinate outside [0.0, 1.0]
    bad_diag = {
        "sections": [{
            "id": "s1",
            "title": "SECTION A",
            "questions": [{
                "id": "q1",
                "number": "1",
                "text": "Identify parts:",
                "marks": 2.0,
                "question_type": "diagram_identify",
                "image_base64": create_sample_png_base64(),
                "diagram_markers": [{"id": "m1", "number": 1, "x": 1.5, "y": 0.5, "label": "Out of bounds"}]
            }]
        }],
        "config": {"subject_name": "Test", "institution_name": "Test"}
    }
    resp = client.post("/api/paper/generate", json=bad_diag)
    assert resp.status_code == 400
    assert "coordinates must be between 0.0 and 1.0" in resp.text


def test_pdf_generation_with_advanced_types():
    """Verify ReportLab PDF generation renders all three question types cleanly and omits answers."""
    sample_img = create_sample_png_base64(400, 250)

    sections = [
        Section(
            id="s1",
            title="SECTION A: MATCHING & VISUALS",
            question_type="mixed",
            questions=[
                Question(
                    id="q1",
                    number="1",
                    text="Match the following physical quantities with their SI units:",
                    marks=4.0,
                    question_type="matching",
                    matching_left=["Force", "Energy", "Power", "Electric Current"],
                    matching_right=["Newton", "Joule", "Watt", "Ampere"],
                    shuffle_right=True,
                    matching_answers={"A": "1", "B": "2", "C": "3", "D": "4"}
                ),
                Question(
                    id="q2",
                    number="2",
                    text="Examine the optical refraction diagram below and answer the question:",
                    marks=3.0,
                    question_type="image_based",
                    image_base64=sample_img,
                    image_caption="Figure 1: Light Ray Passing Through Glass Prism",
                    image_width_ratio=0.60
                ),
                Question(
                    id="q3",
                    number="3",
                    text="Identify the parts marked 1 and 2 in the following circuit schematic:",
                    marks=4.0,
                    question_type="diagram_identify",
                    image_base64=sample_img,
                    diagram_mode="numbered_markers",
                    diagram_markers=[
                        DiagramMarker(id="m1", number=1, x=0.3, y=0.3, label="Rheostat"),
                        DiagramMarker(id="m2", number=2, x=0.7, y=0.7, label="Galvanometer")
                    ]
                )
            ]
        )
    ]

    config = PaperConfig(
        subject_name="Physics & Practical Applications",
        institution_name="National Science Institute",
        time_allowed="1 Hour",
        maximum_marks=11.0,
        page_size="A4"
    )

    pdf_path, pages = generate_pdf(sections=sections, config=config)
    assert pdf_path.exists()
    assert pages >= 1

    # Inspect generated PDF with PyMuPDF
    doc = fitz.open(pdf_path)
    full_text = " ".join([page.get_text() for page in doc])

    # 1. Matching items must be present
    assert "Force" in full_text
    assert "Newton" in full_text
    assert "Column A" in full_text
    assert "Column B" in full_text

    # 2. Image Caption must be present
    assert "Figure 1: Light Ray Passing Through Glass Prism" in full_text

    # 3. Diagram student response prompts must be present
    assert "(1)" in full_text
    assert "(2)" in full_text

    # 4. CRITICAL: Secret answer labels must NOT be present on the student paper
    assert "Rheostat" not in full_text, "Diagram secret answer key leaked on student paper!"
    assert "Galvanometer" not in full_text, "Diagram secret answer key leaked on student paper!"

    # 5. Check images count embedded in PDF
    img_count = sum(len(page.get_images(full=True)) for page in doc)
    assert img_count >= 2, f"Expected at least 2 embedded images, got {img_count}"

    # 6. Verify content integrity service
    expected_changes, content_errors, summary = verify_content_integrity(sections, doc)
    doc.close()

    assert summary["items_not_found"] == 0, f"Dropped content in review: {content_errors}"
    assert summary["items_fully_found"] == 3
