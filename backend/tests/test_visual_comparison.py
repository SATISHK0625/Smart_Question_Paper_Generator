import pytest
from pathlib import Path
from PIL import Image, ImageDraw

from app.services.pdf_comparison_service import (
    calculate_image_difference_metrics,
    generate_difference_heatmap,
    generate_side_by_side_comparison,
    generate_visual_diff_overlay,
    run_visual_pdf_comparison,
    COMPARISONS_DIR
)
from app.services.pdf_generator import generate_pdf
from app.models.schemas import Section, Question, PaperConfig


def test_image_difference_metrics_identical_images():
    im1 = Image.new("RGB", (200, 300), (255, 255, 255))
    im2 = Image.new("RGB", (200, 300), (255, 255, 255))
    metrics = calculate_image_difference_metrics(im1, im2)

    assert metrics["difference_percentage"] == 0.0
    assert metrics["mean_absolute_difference"] == 0.0
    assert metrics["layout_difference_percentage"] == 0.0
    assert metrics["similarity_score"] == 100.0


def test_image_difference_metrics_layout_vs_content():
    # 200w x 400h
    # Content zone: top 22% (y=88) to bottom 90% (y=360)
    # Header zone: y < 88
    im1 = Image.new("RGB", (200, 400), (255, 255, 255))
    im2 = Image.new("RGB", (200, 400), (255, 255, 255))

    # Add difference in content zone
    draw = ImageDraw.Draw(im2)
    draw.rectangle([50, 150, 150, 250], fill=(0, 0, 0))

    metrics = calculate_image_difference_metrics(im1, im2)
    assert metrics["content_difference_percentage"] > 0.0
    assert metrics["layout_difference_percentage"] == 0.0
    # Similarity score should not be 0 because layout is preserved
    assert metrics["similarity_score"] > 85.0


def test_difference_heatmap_generation(tmp_path):
    im1 = Image.new("RGB", (200, 200), (255, 255, 255))
    im2 = Image.new("RGB", (200, 200), (255, 255, 255))
    draw = ImageDraw.Draw(im2)
    draw.rectangle([20, 20, 80, 80], fill=(0, 0, 0))

    p1 = tmp_path / "ref.png"
    p2 = tmp_path / "gen.png"
    out = tmp_path / "heatmap.png"
    im1.save(str(p1))
    im2.save(str(p2))

    heatmap_path = generate_difference_heatmap(p1, p2, out)
    assert heatmap_path.exists()
    assert heatmap_path.stat().st_size > 0

    res_img = Image.open(heatmap_path)
    # Top legend banner is 36px
    assert res_img.height == 200 + 36
    assert res_img.width == 200


def test_run_visual_pdf_comparison_with_fixtures():
    ref_fixture = Path("test_fixtures") / "ref1_cbse_worksheet.pdf"
    if not ref_fixture.exists():
        pytest.skip("Reference fixture not found")

    sec = Section(
        id="s1",
        title="SECTION A",
        questions=[
            Question(id="q1", number="1", text="What is the process of photosynthesis?", marks=2.0)
        ]
    )
    cfg = PaperConfig(subject_name="Science", institution_name="Test School")
    gen_pdf, _ = generate_pdf(sections=[sec], config=cfg)

    report = run_visual_pdf_comparison(ref_fixture, gen_pdf)
    assert report["status"] == "completed"
    assert report["reference_pages"] > 0
    assert report["generated_pages"] > 0
    assert len(report["pages"]) > 0
    assert "average_similarity_score" in report

    first_page = report["pages"][0]
    assert first_page["page_number"] == 1
    assert "similarity_score" in first_page
    assert "difference_image" in first_page
    assert "heatmap_image" in first_page
    assert "side_by_side_image" in first_page
