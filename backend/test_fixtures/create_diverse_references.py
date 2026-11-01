import os
from pathlib import Path
try:
    import pymupdf as fitz
except ImportError:
    import fitz
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable, Image as RLImage
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw

FIXTURES_DIR = Path(__file__).parent.resolve()
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

def create_logo_image(path: Path, color=(20, 80, 160)):
    img = Image.new("RGBA", (120, 60), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    # Circular seal / shield emblem
    draw.ellipse([10, 5, 110, 55], fill=color)
    draw.ellipse([20, 15, 100, 45], fill=(255, 255, 255))
    draw.text((32, 24), "DPA 2026", fill=color)
    img.save(str(path), "PNG")

def generate_pdf1_cbse_worksheet():
    """
    Reference PDF 1:
    - A4, Outer rectangular border (blue-gray)
    - Blue school logo emblem
    - Centered Header: DELHI PUBLIC ACADEMY, Class 6 · MATHEMATICS, WORKSHEET 3
    - Horizontal divider line
    - 2 Pages with section headings
    """
    out_pdf = FIXTURES_DIR / "ref1_cbse_worksheet.pdf"
    logo_path = FIXTURES_DIR / "dpa_logo.png"
    create_logo_image(logo_path, color=(20, 60, 140))

    class BorderCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.saveState()
                w, h = self._pagesize
                self.setStrokeColor(colors.HexColor("#1e3a8a")) # Deep blue border
                self.setLineWidth(1.6)
                self.rect(26, 26, w - 52, h - 52)
                self.restoreState()
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)

    doc = SimpleDocTemplate(
        str(out_pdf),
        pagesize=A4,
        leftMargin=42,
        rightMargin=42,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    h_school = ParagraphStyle("School", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=15, leading=18, alignment=1, textColor=colors.HexColor("#1e3a8a"))
    h_sub = ParagraphStyle("Sub", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=12, leading=15, alignment=1, textColor=colors.HexColor("#334155"))
    h_title = ParagraphStyle("Title", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=13, leading=16, alignment=1, textColor=colors.HexColor("#0f172a"))
    h_sec = ParagraphStyle("Sec", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=11, leading=14, spaceBefore=8, spaceAfter=4)
    p_body = ParagraphStyle("Body", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=14, spaceAfter=6)

    story = [
        RLImage(str(logo_path), width=70, height=35),
        Spacer(1, 4),
        Paragraph("DELHI PUBLIC ACADEMY", h_school),
        Paragraph("Class 6 · MATHEMATICS", h_sub),
        Paragraph("PRACTICE WORKSHEET 3", h_title),
        Spacer(1, 4),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1e3a8a"), spaceBefore=2, spaceAfter=10),
        
        # Section A
        Paragraph("A. MULTIPLE CHOICE QUESTIONS", h_sec),
        Paragraph("1. What is the value of 15 * 8? (a) 100   (b) 120   (c) 140   (d) 160", p_body),
        Paragraph("2. Which of the following is a prime number? (a) 9   (b) 15   (c) 17   (d) 21", p_body),
        Paragraph("3. The perimeter of a square with side 5 cm is: (a) 15 cm   (b) 20 cm   (c) 25 cm   (d) 30 cm", p_body),
        Spacer(1, 10),
        
        # Section B
        Paragraph("B. FILL IN THE BLANKS", h_sec),
        Paragraph("4. The smallest whole number is _________.", p_body),
        Paragraph("5. An angle greater than 90 degrees and less than 180 degrees is an _________ angle.", p_body),
        Paragraph("6. The fraction 3/4 converted to percentage is _________ %.", p_body),
        
        PageBreak(),
        
        # Page 2: Section C
        Paragraph("C. SOLVE THE FOLLOWING PROBLEMS", h_sec),
        Paragraph("7. Simplify the expression: 45 - [38 - {60 / 3 - (6 - 9 / 3)}].", p_body),
        Paragraph("8. A rectangular garden is 25 m long and 16 m wide. Find its area and perimeter.", p_body),
        Paragraph("9. Find the HCF and LCM of 24 and 36 using prime factorization method.", p_body),
        Paragraph("10. Draw a circle of radius 4.5 cm and label its center, diameter, and a chord.", p_body),
    ]

    doc.build(story, canvasmaker=BorderCanvas)
    return out_pdf

def generate_pdf2_university_exam():
    """
    Reference PDF 2:
    - Page size: Letter (612 x 792 pt)
    - Typography: Times-Roman (Serif)
    - NO page border
    - Boxed university metadata table (Course Code, Max Marks, Duration)
    - 1 Page exam paper
    """
    out_pdf = FIXTURES_DIR / "ref2_university_exam.pdf"

    doc = SimpleDocTemplate(
        str(out_pdf),
        pagesize=letter,
        leftMargin=45,
        rightMargin=45,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    u_title = ParagraphStyle("UTitle", fontName="Times-Bold", fontSize=14, leading=17, alignment=1, textColor=colors.black)
    u_sub = ParagraphStyle("USub", fontName="Times-Bold", fontSize=11, leading=14, alignment=1, textColor=colors.black)
    sec_title = ParagraphStyle("SecTitle", fontName="Times-Bold", fontSize=11, leading=14, spaceBefore=10, spaceAfter=4)
    meta_style = ParagraphStyle("Meta", fontName="Times-Roman", fontSize=9.5, leading=12)
    q_style = ParagraphStyle("Question", fontName="Times-Roman", fontSize=10, leading=14, spaceAfter=5)

    meta_table_data = [
        [Paragraph("<b>Course:</b> CS301 - Data Structures", meta_style), Paragraph("<b>Semester:</b> V B.Tech", meta_style)],
        [Paragraph("<b>Duration:</b> 90 Minutes", meta_style), Paragraph("<b>Maximum Marks:</b> 50", meta_style)]
    ]
    t = Table(meta_table_data, colWidths=[260, 260])
    t.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1.0, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.gray),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))

    story = [
        Paragraph("METROPOLITAN INSTITUTE OF TECHNOLOGY", u_title),
        Paragraph("DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING", u_sub),
        Paragraph("MID-TERM ASSESSMENT 2026", u_sub),
        Spacer(1, 6),
        t,
        Spacer(1, 8),
        
        Paragraph("PART A - SHORT ANSWER QUESTIONS (5 x 2 = 10 Marks)", sec_title),
        Paragraph("1. Define asymptotic time complexity and Big-O notation.", q_style),
        Paragraph("2. Differentiate between an array and a linked list in terms of memory allocation.", q_style),
        Paragraph("3. What is the postfix equivalent of the infix expression (A + B) * C?", q_style),
        Paragraph("4. State the properties of a complete binary tree.", q_style),
        Paragraph("5. Explain the concept of hash collision resolution using linear probing.", q_style),
        
        Spacer(1, 6),
        Paragraph("PART B - DETAILED PROBLEMS (2 x 10 = 20 Marks)", sec_title),
        Paragraph("6. Write an algorithm to reverse a singly linked list in-place with O(N) time complexity.", q_style),
        Paragraph("7. Construct an AVL tree by inserting the keys: 40, 20, 10, 25, 30, 22, 50. Show all rotations.", q_style),
    ]

    doc.build(story)
    return out_pdf

def generate_pdf3_medical_quiz():
    """
    Reference PDF 3:
    - A4, Modern format with running header on page 2
    - Sans-serif (Helvetica), no outer border
    - Multi-page (2 pages)
    - Longer questions with matching and options
    """
    out_pdf = FIXTURES_DIR / "ref3_medical_quiz.pdf"

    class RunningHeaderCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.saveState()
                w, h = self._pagesize
                if self._pageNumber > 1:
                    # Running header on page 2+
                    self.setFont("Helvetica", 9)
                    self.setFillColor(colors.HexColor("#475569"))
                    self.drawString(40, h - 30, "BIOMEDICAL SCIENCES TEST — CONTINUED")
                    self.setStrokeColor(colors.HexColor("#cbd5e1"))
                    self.setLineWidth(0.5)
                    self.line(40, h - 34, w - 40, h - 34)
                # Footer on all pages
                self.setFont("Helvetica", 8)
                self.setFillColor(colors.HexColor("#64748b"))
                self.drawRightString(w - 40, 20, f"Page {self._pageNumber} of {num_pages}")
                self.restoreState()
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)

    doc = SimpleDocTemplate(
        str(out_pdf),
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    main_title = ParagraphStyle("MTitle", fontName="Helvetica-Bold", fontSize=14, leading=17, alignment=0, textColor=colors.HexColor("#0f766e"))
    sub_title = ParagraphStyle("MSub", fontName="Helvetica", fontSize=10, leading=13, alignment=0, textColor=colors.HexColor("#334155"))
    sec_title = ParagraphStyle("Sec", fontName="Helvetica-Bold", fontSize=11, leading=14, spaceBefore=8, spaceAfter=4, textColor=colors.HexColor("#0f766e"))
    q_style = ParagraphStyle("Q", fontName="Helvetica", fontSize=9.5, leading=13.5, spaceAfter=5)

    story = [
        Paragraph("NATIONAL HEALTH SCIENCE INSTITUTE", main_title),
        Paragraph("HUMAN ANATOMY & CELL PHYSIOLOGY ASSESSMENT · SEMESTER II", sub_title),
        HRFlowable(width="100%", thickness=1.0, color=colors.HexColor("#0f766e"), spaceBefore=4, spaceAfter=10),

        Paragraph("SECTION 1: CELL BIOLOGY", sec_title),
        Paragraph("1. Which organelle is primarily responsible for ATP synthesis in eukaryotic cells?", q_style),
        Paragraph("   (a) Ribosome   (b) Mitochondrion   (c) Golgi Apparatus   (d) Lysosome", q_style),
        Paragraph("2. The phospholipid bilayer of the cell membrane possesses which critical characteristic?", q_style),
        Paragraph("   (a) Amphipathic nature   (b) Complete impermeability   (c) Rigid structure   (d) Lack of proteins", q_style),
        Paragraph("3. During DNA replication, which enzyme unwinds the double helix structure?", q_style),
        Paragraph("   (a) DNA Polymerase   (b) Ligase   (c) Helicase   (d) Topoisomerase", q_style),
        Spacer(1, 8),

        Paragraph("SECTION 2: ORGAN SYSTEMS", sec_title),
        Paragraph("4. Which valve prevents the backflow of blood from the left ventricle into the left atrium?", q_style),
        Paragraph("   (a) Tricuspid valve   (b) Bicuspid (Mitral) valve   (c) Aortic semilunar valve   (d) Pulmonary valve", q_style),
        Paragraph("5. The functional filtering unit of the human kidney is the nephron.", q_style),

        PageBreak(),

        Paragraph("SECTION 3: PHYSIOLOGICAL PROCESSES", sec_title),
        Paragraph("6. Describe the role of surfactant in pulmonary alveoli and explain how it prevents alveolar collapse.", q_style),
        Paragraph("7. Explain the mechanism of the sodium-potassium pump (Na+/K+-ATPase) in maintaining resting membrane potential in neurons.", q_style),
        Paragraph("8. Detail the hormonal feedback loop involving insulin and glucagon in regulating blood glucose levels after a carbohydrate-rich meal.", q_style),
    ]

    doc.build(story, canvasmaker=RunningHeaderCanvas)
    return out_pdf

if __name__ == "__main__":
    p1 = generate_pdf1_cbse_worksheet()
    print("Created:", p1)
    p2 = generate_pdf2_university_exam()
    print("Created:", p2)
    p3 = generate_pdf3_medical_quiz()
    print("Created:", p3)
