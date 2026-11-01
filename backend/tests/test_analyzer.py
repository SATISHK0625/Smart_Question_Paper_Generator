import pytest
from pathlib import Path
try:
    import pymupdf as fitz
except ImportError:
    import fitz
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from backend.app.services.pdf_analyzer import analyze_reference_pdf
from backend.app.utils.file_utils import TEMP_BASE_DIR

@pytest.fixture
def sample_pdf(tmp_path) -> Path:
    pdf_file = tmp_path / "sample_reference.pdf"
    c = canvas.Canvas(str(pdf_file), pagesize=A4)
    # Header
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, 800, "EXAMINATION QUESTION PAPER 2026")
    c.setFont("Helvetica", 10)
    c.drawString(50, 750, "1. What is an operating system? [5 marks]")
    c.drawString(50, 720, "2. Explain virtual memory. [10 marks]")
    c.drawString(280, 25, "Page 1 of 1")
    c.save()
    return pdf_file

@pytest.fixture
def empty_or_scanned_pdf(tmp_path) -> Path:
    # PDF with almost no text (simulating scanned document image)
    pdf_file = tmp_path / "scanned_doc.pdf"
    c = canvas.Canvas(str(pdf_file), pagesize=A4)
    # draw a rectangle (dummy image representation)
    c.rect(50, 50, 495, 740, fill=1)
    c.save()
    return pdf_file

def test_analyze_sample_pdf(sample_pdf):
    analysis = analyze_reference_pdf(sample_pdf)
    assert analysis.page_count == 1
    assert analysis.page_size == "A4"
    assert analysis.page_width_pt > 500
    assert analysis.page_height_pt > 800
    assert analysis.is_scanned is False
    assert analysis.primary_font == "Helvetica"
    assert analysis.has_page_numbers is True

def test_analyze_scanned_pdf(empty_or_scanned_pdf):
    analysis = analyze_reference_pdf(empty_or_scanned_pdf)
    assert analysis.is_scanned is True
    assert any("scanned" in w.lower() for w in analysis.warnings)
