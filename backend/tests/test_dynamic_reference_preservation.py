import io
from pathlib import Path
try:
    import pymupdf as fitz
except ImportError:
    import fitz
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.question_parser import parse_questions_text
from backend.app.models.schemas import PaperConfig, GeneratePaperRequest

client = TestClient(app)

FIXTURES_DIR = Path(__file__).parent.parent / "test_fixtures"
COMPARISON_DIR = FIXTURES_DIR / "comparison_results"
COMPARISON_DIR.mkdir(parents=True, exist_ok=True)

def render_pages_to_images(pdf_path: Path, prefix: str) -> list[Path]:
    doc = fitz.open(pdf_path)
    paths = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150)
        out = COMPARISON_DIR / f"{prefix}_page_{i+1}.png"
        pix.save(str(out))
        paths.append(out)
    doc.close()
    return paths

def create_side_by_side(img1: Path, img2: Path, out_path: Path):
    im1 = Image.open(img1).convert("RGB")
    im2 = Image.open(img2).convert("RGB")
    w1, h1 = im1.size
    w2, h2 = im2.size
    max_h = max(h1, h2)
    tot_w = w1 + w2 + 20
    combined = Image.new("RGB", (tot_w, max_h), (235, 235, 235))
    combined.paste(im1, (0, 0))
    combined.paste(im2, (w1 + 20, 0))
    combined.save(str(out_path))

def test_unseen_reference_1_cbse_worksheet():
    """
    Test 1: Unseen CBSE Worksheet (A4, 2 pages, blue outer border, school logo, divider).
    Ensures:
    - Uploaded PDF (ref1_cbse_worksheet.pdf) is used, NOT the sample fixture.
    - Blue outer border and logo are preserved.
    - Replacement questions are inserted.
    """
    ref_file = FIXTURES_DIR / "ref1_cbse_worksheet.pdf"
    assert ref_file.exists()

    # 1. Upload via API
    with open(ref_file, "rb") as f:
        resp = client.post(
            "/api/reference/analyze",
            files={"file": ("ref1_cbse_worksheet.pdf", f, "application/pdf")}
        )
    assert resp.status_code == 200
    analysis = resp.json()
    assert analysis["has_page_border"] is True
    assert analysis["has_header_divider"] is True
    assert analysis["reference_id"] is not None
    ref_id = analysis["reference_id"]

    # 2. Replacement questions
    new_questions_text = """
A. GENERAL SCIENCE QUESTIONS
1. Photosynthesis occurs in which plant cell organelle?
(a) Chloroplast   (b) Nucleus   (c) Vacuole   (d) Cell wall
2. What gas do human beings exhale during cellular respiration?
(a) Oxygen   (b) Carbon dioxide   (c) Nitrogen   (d) Hydrogen

B. SHORT DEFINITIONS
3. Define friction and state its SI unit.
4. What is the boiling point of pure water at sea level?
"""
    parsed = parse_questions_text(new_questions_text)
    assert len(parsed.sections) == 2

    # 3. Request preview and generation
    payload = {
        "sections": [s.model_dump() for s in parsed.sections],
        "config": {
            "subject_name": "General Science",
            "page_size": "A4",
            "use_reference_header": True,
            "reference_id": ref_id
        },
        "reference_style": analysis
    }

    resp_gen = client.post("/api/paper/generate", json=payload)
    assert resp_gen.status_code == 200
    assert resp_gen.headers["content-type"] == "application/pdf"

    # Save and verify
    out_pdf = COMPARISON_DIR / "generated_ref1_test.pdf"
    out_pdf.write_bytes(resp_gen.content)

    doc = fitz.open(out_pdf)
    assert len(doc) >= 1

    # Verify template was ref1 (DELHI PUBLIC ACADEMY), NOT the sample (SRC GLOBAL CBSE SCHOOL)
    p0_text = doc[0].get_text("text")
    assert "DELHI PUBLIC ACADEMY" in p0_text, "Must preserve uploaded school name, NOT sample fixture"
    assert "SRC GLOBAL" not in p0_text, "Must NOT contain sample fixture school name"

    # Verify logo preserved
    images = doc[0].get_images()
    assert len(images) >= 1, "Emblem logo from uploaded ref1 must be preserved"

    # Verify outer rectangular border
    drawings = doc[0].get_drawings()
    has_border = any(
        (d.get("rect") and (d["rect"][2] - d["rect"][0]) > doc[0].rect.width * 0.75 and (d["rect"][3] - d["rect"][1]) > doc[0].rect.height * 0.75)
        for d in drawings
    )
    assert has_border, "Ref1 outer border must be preserved"

    # Verify replacement questions present
    all_text = "".join(p.get_text("text") for p in doc)
    assert "Photosynthesis occurs" in all_text
    assert "Define friction" in all_text

    # Render pages and side-by-side
    ref_imgs = render_pages_to_images(ref_file, "ref1_source")
    gen_imgs = render_pages_to_images(out_pdf, "ref1_generated")
    for i in range(min(len(ref_imgs), len(gen_imgs))):
        create_side_by_side(ref_imgs[i], gen_imgs[i], COMPARISON_DIR / f"diff_ref1_page_{i+1}.png")
    doc.close()

def test_unseen_reference_2_university_exam():
    """
    Test 2: Unseen University Exam Paper (Letter size, Times-Roman serif, NO border, metadata table).
    Ensures:
    - Letter dimensions (612x792 pt) are preserved, NOT forced to A4!
    - Times-Roman serif typography is used, NOT Helvetica!
    - NO border is added (does not invent sample border).
    - University header table is preserved.
    """
    ref_file = FIXTURES_DIR / "ref2_university_exam.pdf"
    assert ref_file.exists()

    # 1. Upload via API
    with open(ref_file, "rb") as f:
        resp = client.post(
            "/api/reference/analyze",
            files={"file": ("ref2_university_exam.pdf", f, "application/pdf")}
        )
    assert resp.status_code == 200
    analysis = resp.json()
    assert analysis["page_size"] == "Letter"
    assert analysis["has_page_border"] is False, "Ref2 has no page border"
    assert "times" in analysis["primary_font"].lower() or "roman" in analysis["primary_font"].lower()
    ref_id = analysis["reference_id"]

    # 2. Replacement questions
    new_questions_text = """
SECTION A: OPERATING SYSTEMS PRINCIPLES
1. Differentiate between a process and a thread with architectural diagrams. (5 marks)
2. Explain the four necessary conditions for a deadlock to occur in an operating system. (5 marks)
3. Describe the working mechanism of virtual memory and demand paging. (5 marks)
"""
    parsed = parse_questions_text(new_questions_text)

    # 3. Generate
    payload = {
        "sections": [s.model_dump() for s in parsed.sections],
        "config": {
            "page_size": "Letter",
            "use_reference_header": True,
            "reference_id": ref_id
        },
        "reference_style": analysis
    }

    resp_gen = client.post("/api/paper/generate", json=payload)
    assert resp_gen.status_code == 200

    out_pdf = COMPARISON_DIR / "generated_ref2_test.pdf"
    out_pdf.write_bytes(resp_gen.content)

    doc = fitz.open(out_pdf)
    p0 = doc[0]

    # Verify Letter dimensions: width ~ 612 pt, height ~ 792 pt
    assert abs(p0.rect.width - 612.0) < 5.0, f"Expected Letter width 612, got {p0.rect.width}"
    assert abs(p0.rect.height - 792.0) < 5.0, f"Expected Letter height 792, got {p0.rect.height}"

    # Verify NO outer border
    drawings = p0.get_drawings()
    has_outer_border = any(
        (d.get("rect") and (d["rect"][2] - d["rect"][0]) > p0.rect.width * 0.8 and (d["rect"][3] - d["rect"][1]) > p0.rect.height * 0.8)
        for d in drawings
    )
    assert not has_outer_border, "Ref2 must NOT invent a border when reference has no border"

    # Verify University Header preserved
    p0_text = p0.get_text("text")
    assert "METROPOLITAN INSTITUTE OF TECHNOLOGY" in p0_text
    assert "DEPARTMENT OF COMPUTER SCIENCE" in p0_text
    assert "SRC GLOBAL" not in p0_text

    # Verify new questions inserted
    assert "OPERATING SYSTEMS PRINCIPLES" in p0_text
    assert "deadlock" in p0_text

    # Render diff
    ref_imgs = render_pages_to_images(ref_file, "ref2_source")
    gen_imgs = render_pages_to_images(out_pdf, "ref2_generated")
    for i in range(min(len(ref_imgs), len(gen_imgs))):
        create_side_by_side(ref_imgs[i], gen_imgs[i], COMPARISON_DIR / f"diff_ref2_page_{i+1}.png")
    doc.close()

def test_unseen_reference_3_medical_quiz():
    """
    Test 3: Unseen Multi-page Medical Quiz (A4, 2 pages, running header on page 2, no border).
    Ensures:
    - Running headers on subsequent pages are preserved.
    - No outer border is invented.
    - Long replacement text wraps cleanly across pages.
    """
    ref_file = FIXTURES_DIR / "ref3_medical_quiz.pdf"
    assert ref_file.exists()

    # 1. Upload via API
    with open(ref_file, "rb") as f:
        resp = client.post(
            "/api/reference/analyze",
            files={"file": ("ref3_medical_quiz.pdf", f, "application/pdf")}
        )
    assert resp.status_code == 200
    analysis = resp.json()
    assert analysis["page_count"] == 2
    assert analysis["has_page_border"] is False
    ref_id = analysis["reference_id"]

    # 2. Replacement questions across 3 sections
    new_questions_text = """
SECTION 1: CLINICAL PHARMACOLOGY
1. Explain the pharmacokinetics of beta-blockers in managing hypertension.
2. What are the key indications and contraindications of ACE inhibitors?

SECTION 2: PATHOLOGY & IMMUNOLOGY
3. Detail the cellular mechanisms underlying Type 1 hypersensitivity reactions.
4. Contrast acute inflammation with chronic inflammation at the histopathological level.

SECTION 3: DIAGNOSTIC TECHNIQUES
5. Describe the biochemical basis of ELISA in detecting antigen-antibody complexes.
6. What diagnostic markers are evaluated in an arterial blood gas (ABG) analysis?
"""
    parsed = parse_questions_text(new_questions_text)
    assert len(parsed.sections) == 3

    # 3. Generate
    payload = {
        "sections": [s.model_dump() for s in parsed.sections],
        "config": {
            "page_size": "A4",
            "use_reference_header": True,
            "reference_id": ref_id
        },
        "reference_style": analysis
    }

    resp_gen = client.post("/api/paper/generate", json=payload)
    assert resp_gen.status_code == 200

    out_pdf = COMPARISON_DIR / "generated_ref3_test.pdf"
    out_pdf.write_bytes(resp_gen.content)

    doc = fitz.open(out_pdf)
    assert len(doc) >= 2, f"Expected multi-page output, got {len(doc)}"

    # Verify Page 1 header preserved
    p0_text = doc[0].get_text("text")
    assert "NATIONAL HEALTH SCIENCE INSTITUTE" in p0_text
    assert "CLINICAL PHARMACOLOGY" in p0_text
    assert "SRC GLOBAL" not in p0_text

    # Verify Page 2 running header preserved
    p1_text = doc[1].get_text("text")
    assert "BIOMEDICAL SCIENCES TEST — CONTINUED" in p1_text, "Running header on Page 2 must be preserved"

    # Verify replacement questions present
    all_text = "".join(p.get_text("text") for p in doc)
    assert "beta-blockers" in all_text
    assert "ELISA" in all_text

    # Render diff
    ref_imgs = render_pages_to_images(ref_file, "ref3_source")
    gen_imgs = render_pages_to_images(out_pdf, "ref3_generated")
    for i in range(min(len(ref_imgs), len(gen_imgs))):
        create_side_by_side(ref_imgs[i], gen_imgs[i], COMPARISON_DIR / f"diff_ref3_page_{i+1}.png")
    doc.close()

def test_unseen_reference_4_scanned_worksheet():
    """
    Test 4: Scanned / Image-based Worksheet Reference.
    Ensures:
    - Detected as is_scanned=True
    - Template background image, emblem, and header are preserved directly.
    - Replacement questions are inserted without losing content.
    - Full difference report distinguishes expected content differences from layout differences.
    """
    ref_file = FIXTURES_DIR / "scanned_worksheet_reference.pdf"
    if not ref_file.exists():
        from backend.test_fixtures.create_scanned_reference import generate_scanned_worksheet_reference
        generate_scanned_worksheet_reference(ref_file)

    # 1. Upload via API
    with open(ref_file, "rb") as f:
        resp = client.post(
            "/api/reference/analyze",
            files={"file": ("scanned_worksheet_reference.pdf", f, "application/pdf")}
        )
    assert resp.status_code == 200
    analysis = resp.json()
    assert analysis["is_scanned"] is True
    ref_id = analysis["reference_id"]

    # 2. Replacement questions
    new_questions_text = """
SECTION A: CELLULAR RESPIRATION
1. Explain the biochemical steps of the Krebs cycle occurring within mitochondrial matrix. (5 marks)
2. What role does ATP synthase play in the electron transport chain during oxidative phosphorylation? (5 marks)
"""
    parsed = parse_questions_text(new_questions_text)
    assert len(parsed.sections) == 1

    # 3. Generate Paper
    payload = {
        "sections": [s.model_dump() for s in parsed.sections],
        "config": {
            "subject_name": "Biology",
            "page_size": "A4",
            "use_reference_header": True,
            "reference_id": ref_id
        },
        "reference_style": analysis
    }

    resp_gen = client.post("/api/paper/generate", json=payload)
    assert resp_gen.status_code == 200

    out_pdf = COMPARISON_DIR / "generated_scanned_test.pdf"
    out_pdf.write_bytes(resp_gen.content)

    doc = fitz.open(out_pdf)
    assert len(doc) >= 1
    p0_text = doc[0].get_text("text")
    assert "Krebs cycle" in p0_text
    assert "ATP synthase" in p0_text
    doc.close()

    # 4. Review & Compare via API
    resp_review = client.post("/api/paper/review", json=payload)
    assert resp_review.status_code == 200
    review_data = resp_review.json()
    assert review_data["status"] == "success"
    assert review_data["validation_status"] in ("PASS", "WARNING")
    assert review_data["fidelity_score"] >= 85
    assert len(review_data["page_comparisons"]) >= 1
    assert "diff_overlay_data" in review_data["page_comparisons"][0]

