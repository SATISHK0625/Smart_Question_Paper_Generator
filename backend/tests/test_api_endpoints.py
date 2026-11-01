import io
from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from docx import Document

from backend.app.main import app

client = TestClient(app)

def create_in_memory_pdf() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.drawString(100, 750, "Sample Examination Reference PDF")
    c.drawString(100, 700, "1. What is an API? (5 marks)")
    c.save()
    buf.seek(0)
    return buf.getvalue()

def create_in_memory_docx() -> bytes:
    doc = Document()
    doc.add_paragraph("PART A")
    doc.add_paragraph("1. Explain REST architecture. (5 marks)")
    doc.add_paragraph("2. What is FastAPI? (5 marks)")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()

def test_api_analyze_reference_pdf():
    pdf_bytes = create_in_memory_pdf()
    response = client.post(
        "/api/reference/analyze",
        files={"file": ("reference.pdf", pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["page_count"] == 1
    assert data["page_size"] == "A4"
    assert "primary_font" in data

def test_api_analyze_invalid_extension():
    response = client.post(
        "/api/reference/analyze",
        files={"file": ("invalid.exe", b"binarycontent", "application/octet-stream")}
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]

def test_api_parse_questions():
    payload = {
        "raw_text": "PART A\n1. Define recursion. (2 marks)\n2. What is an array? (2 marks)"
    }
    response = client.post("/api/questions/parse", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["sections"]) == 1
    assert len(data["sections"][0]["questions"]) == 2
    assert data["sections"][0]["questions"][0]["marks"] == 2.0

def test_api_import_docx():
    docx_bytes = create_in_memory_docx()
    response = client.post(
        "/api/questions/import",
        files={"file": ("questions.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "PART A" in data["raw_text"]
    assert "Explain REST" in data["raw_text"]

def test_api_import_txt():
    txt_content = b"1. Question One (5M)\n2. Question Two (5M)"
    response = client.post(
        "/api/questions/import",
        files={"file": ("questions.txt", txt_content, "text/plain")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "Question One" in data["raw_text"]

def test_api_paper_preview_and_generate():
    payload = {
        "sections": [
            {
                "id": "s1",
                "title": "SECTION A",
                "instructions": "Answer all questions.",
                "questions": [
                    {
                        "id": "q1",
                        "number": "1",
                        "text": "Explain Python GIL.",
                        "marks": 5.0,
                        "subquestions": []
                    }
                ]
            }
        ],
        "config": {
            "institution_name": "Test University",
            "exam_name": "Final Exam",
            "subject_name": "Python Programming",
            "maximum_marks": 5.0
        }
    }

    # Test preview
    resp_prev = client.post("/api/paper/preview", json=payload)
    assert resp_prev.status_code == 200
    assert resp_prev.headers["content-type"] == "application/pdf"
    assert len(resp_prev.content) > 1000

    # Test generate
    resp_gen = client.post("/api/paper/generate", json=payload)
    assert resp_gen.status_code == 200
    assert resp_gen.headers["content-type"] == "application/pdf"
    assert "attachment" in resp_gen.headers["content-disposition"]
    assert len(resp_gen.content) > 1000

    # Test overview JSON
    resp_ov = client.post("/api/paper/overview", json=payload)
    assert resp_ov.status_code == 200
    ov_data = resp_ov.json()
    assert ov_data["total_questions_count"] == 1
    assert ov_data["marks_match"] is True

    # Test overview PDF download
    resp_ov_pdf = client.post("/api/paper/overview?download_pdf=true", json=payload)
    assert resp_ov_pdf.status_code == 200
    assert resp_ov_pdf.headers["content-type"] == "application/pdf"
    assert "Question_Paper_Overview.pdf" in resp_ov_pdf.headers["content-disposition"]
