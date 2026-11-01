import pytest
from pathlib import Path
try:
    import pymupdf as fitz
except ImportError:
    import fitz
from PIL import Image, ImageChops, ImageStat
import os

from backend.app.services.pdf_analyzer import analyze_reference_pdf
from backend.app.services.question_parser import parse_questions_text
from backend.app.services.pdf_generator import generate_pdf
from backend.app.models.schemas import PaperConfig
from backend.app.utils.file_utils import cleanup_file

FIXTURES_DIR = Path(__file__).parent.parent / "test_fixtures"
COMPARISON_DIR = FIXTURES_DIR / "comparison_results"
COMPARISON_DIR.mkdir(parents=True, exist_ok=True)

def render_pdf_to_images(pdf_path: Path, output_prefix: str) -> list[Path]:
    doc = fitz.open(pdf_path)
    image_paths = []
    for i, page in enumerate(doc):
        # Render at 150 DPI for sharp inspection
        pix = page.get_pixmap(dpi=150)
        img_path = COMPARISON_DIR / f"{output_prefix}_page_{i+1}.png"
        pix.save(str(img_path))
        image_paths.append(img_path)
    doc.close()
    return image_paths

def create_side_by_side_diff(img_path1: Path, img_path2: Path, diff_out: Path):
    im1 = Image.open(img_path1).convert("RGB")
    im2 = Image.open(img_path2).convert("RGB")

    # Match heights
    w1, h1 = im1.size
    w2, h2 = im2.size
    max_h = max(h1, h2)
    tot_w = w1 + w2 + 20

    combined = Image.new("RGB", (tot_w, max_h), (240, 240, 240))
    combined.paste(im1, (0, 0))
    combined.paste(im2, (w1 + 20, 0))
    combined.save(str(diff_out))

def test_worksheet_exact_reproduction_regression():
    ref_pdf = FIXTURES_DIR / "Class 4 - WORK SHEET 7.pdf"
    assert ref_pdf.exists(), "Reference PDF must exist"

    # 1. Analyze reference PDF
    analysis = analyze_reference_pdf(ref_pdf)
    assert analysis.document_type == "worksheet"
    assert analysis.has_page_border is True
    assert analysis.has_header_divider is True
    assert bool(analysis.header_logo_base64) is True
    assert len(analysis.header_lines) >= 3
    assert "SRC GLOBAL CBSE SCHOOL" in analysis.header_lines[0].text

    # 2. Parse identical question text
    text_path = FIXTURES_DIR / "class4_reference_text.txt"
    raw_text = text_path.read_text(encoding="utf-8")
    parsed = parse_questions_text(raw_text)
    assert len(parsed.sections) == 3
    assert parsed.sections[0].title == "A. CHOOSE THE CORRECT ANSWER"
    assert parsed.sections[1].title == "B. MATCH THE FOLLOWING"
    assert parsed.sections[2].title == "C. FILL IN THE BLANKS"

    # 3. Generate PDF using extracted template
    config = PaperConfig(
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
        assert page_count == 3, f"Expected 3 pages matching reference, got {page_count}"

        # 4. Render both to images
        ref_images = render_pdf_to_images(ref_pdf, "reference")
        gen_images = render_pdf_to_images(gen_pdf, "generated_reproduction")

        # Create side-by-side comparisons
        for p_idx in range(min(len(ref_images), len(gen_images))):
            diff_path = COMPARISON_DIR / f"comparison_reproduction_page_{p_idx+1}.png"
            create_side_by_side_diff(ref_images[p_idx], gen_images[p_idx], diff_path)
            assert diff_path.exists()

        # 5. Verify generated PDF structure with fitz
        doc = fitz.open(gen_pdf)
        p1_text = doc[0].get_text("text")
        assert "SRC GLOBAL CBSE SCHOOL" in p1_text
        assert "Grade 4" in p1_text
        assert "WORKSHEET" in p1_text
        assert "A. CHOOSE THE CORRECT ANSWER" in p1_text

        # Verify no unwanted college exam metadata was inserted
        assert "CS402" not in p1_text
        assert "Semester 4" not in p1_text
        assert "Maximum Marks: 30" not in p1_text
        assert "SECTION A" not in p1_text

        doc.close()
    finally:
        cleanup_file(gen_pdf)

def test_worksheet_different_questions_content_regression():
    ref_pdf = FIXTURES_DIR / "Class 4 - WORK SHEET 7.pdf"
    analysis = analyze_reference_pdf(ref_pdf)

    # Question text from Science.pdf (Animal Life - II)
    animal_text_path = FIXTURES_DIR / "animal_life_input.txt"
    raw_text = animal_text_path.read_text(encoding="utf-8")
    parsed = parse_questions_text(raw_text)

    config = PaperConfig(
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
        gen_images = render_pdf_to_images(gen_pdf, "generated_animal_life")

        doc = fitz.open(gen_pdf)
        p1_text = doc[0].get_text("text")

        # Preserved reference header styling
        assert "SRC GLOBAL CBSE SCHOOL" in p1_text
        assert "Grade 4" in p1_text
        assert "WORKSHEET" in p1_text

        # Contains the user's new question content
        assert "A. FILL IN THE BLANKS" in p1_text
        assert "Animals that give birth" in p1_text
        all_pages_text = "".join(doc[i].get_text("text") for i in range(len(doc)))
        assert "CHOOSE THE CORRECT ANSWER" in all_pages_text
        assert "NAME THE FOLLOWING" in all_pages_text

        # Confirms NO unwanted exam metadata
        assert "CS402" not in p1_text
        assert "Semester 4" not in p1_text
        assert "Maximum Marks: 30" not in p1_text
        assert "SECTION A" not in p1_text

        doc.close()
    finally:
        cleanup_file(gen_pdf)
