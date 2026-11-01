import os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw

FIXTURES_DIR = Path(__file__).parent.resolve()
OUTPUT_PDF = FIXTURES_DIR / "Class 4 - WORK SHEET 7.pdf"
LOGO_IMG_PATH = FIXTURES_DIR / "school_logo.png"

def create_dummy_school_logo():
    # Create an emblem logo matching the reference
    img = Image.new("RGBA", (140, 80), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    # Maroon shield shape
    draw.rectangle([30, 5, 110, 55], fill=(128, 0, 32))
    # Inner white ribbon
    draw.rectangle([10, 50, 130, 68], fill=(240, 240, 240), outline=(128, 0, 32), width=1)
    draw.text((18, 54), "BELIEVE | BUILD | BECOME", fill=(128, 0, 32))
    img.save(str(LOGO_IMG_PATH), "PNG")

class BorderedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(BorderedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_border()
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_border(self):
        self.saveState()
        w, h = self._pagesize
        self.setStrokeColor(colors.black)
        self.setLineWidth(1.5)
        # 25 pt margin rectangle
        self.rect(25, 25, w - 50, h - 50)
        self.restoreState()

def build_reference_worksheet():
    create_dummy_school_logo()
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=35,
        bottomMargin=35
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'SchoolTitle',
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        alignment=1,
        textColor=colors.black,
        spaceAfter=3
    )
    sub_style = ParagraphStyle(
        'GradeSub',
        fontName='Helvetica',
        fontSize=12,
        leading=15,
        alignment=1,
        textColor=colors.black,
        spaceAfter=3
    )
    ws_style = ParagraphStyle(
        'WorksheetTitle',
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=17,
        alignment=1,
        textColor=colors.black,
        spaceAfter=6
    )
    sec_style = ParagraphStyle(
        'SectionHeader',
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        alignment=0, # Left
        textColor=colors.black,
        spaceBefore=10,
        spaceAfter=6
    )
    q_style = ParagraphStyle(
        'QText',
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        alignment=0,
        textColor=colors.black,
        spaceBefore=4,
        spaceAfter=2
    )
    opt_style = ParagraphStyle(
        'OptionsText',
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        alignment=0,
        textColor=colors.black,
        leftIndent=15,
        spaceAfter=6
    )
    match_hdr_style = ParagraphStyle(
        'MatchHdr',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.black
    )
    match_txt_style = ParagraphStyle(
        'MatchTxt',
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.black
    )

    story = []

    # Page 1 Header
    from reportlab.platypus import Image as RLImage
    story.append(RLImage(str(LOGO_IMG_PATH), width=70, height=40))
    story.append(Spacer(1, 4))
    story.append(Paragraph("SRC GLOBAL CBSE SCHOOL", title_style))
    story.append(Paragraph("Grade 4 – SCIENCE", sub_style))
    story.append(Paragraph("WORKSHEET", ws_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.black, spaceBefore=2, spaceAfter=8))

    # Section A
    story.append(Paragraph("A. CHOOSE THE CORRECT ANSWER", sec_style))

    q_data_p1 = [
        ("1. The top soft layer of earth where plants grow is called -", "a) Rock  b) Soil  c) Water  d) Air"),
        ("2. Soil is made from -", "a) Breaking of rocks  b) Plastic  c) Glass  d) Iron"),
        ("3. The dark part of soil made of dead leaves is called -", "a) Sand  b) Humus  c) Stone  d) Water"),
        ("4. Which soil is found near rivers like Ganga and Kaveri?", "a) Black Soil   b) Red Soil   c) Alluvial Soil   d) Desert Soil"),
        ("5. Black soil is also called -", "a) Cotton Soil   b) Rice Soil   c) Desert Soil   d) Red Soil"),
        ("6. Red soil is red in colour because of -", "a) Water   b) Iron   c) Cotton   d) Salt"),
        ("7. Sandy soil is mostly found in -", "a) Punjab   b) Rajasthan Desert   c) Maharashtra   d) Kerala"),
        ("8. Washing away of topsoil by rain and wind is called -", "a) Soil Conservation   b) Soil Erosion   c) Afforestation   d) Farming"),
    ]

    for qtext, opttext in q_data_p1:
        story.append(Paragraph(qtext, q_style))
        story.append(Paragraph(opttext, opt_style))

    # Page 2
    story.append(PageBreak())

    q_data_p2 = [
        ("9. Main cause of soil erosion is -", "a) Planting trees   b) Cutting of trees   c) Making steps   d) Watering plants"),
        ("10. Roots of plants -", "a) Hold the soil   b) Blow the soil   c) Wash the soil   d) Destroy the soil"),
        ("11. Which soil is best for growing cotton?", "a) Alluvial Soil   b) Black Soil   c) Red Soil   d) Sandy Soil"),
        ("12. Terrace farming is done in -", "a) Desert   b) Hills like Ooty   c) Sea   d) Plain"),
        ("13. Which of these helps to save soil?", "a) Cutting trees   b) Planting more trees   c) Overgrazing   d) Strong wind"),
        ("14. Which soil holds more water?", "a) Black Soil   b) Sandy Soil   c) Rocky Soil   d) None"),
        ("15. How many years does nature need to make 1 inch of soil?", "a) 1 year   b) 10 years   c) 100 years   d) 500 years"),
    ]

    for qtext, opttext in q_data_p2:
        story.append(Paragraph(qtext, q_style))
        story.append(Paragraph(opttext, opt_style))

    # Section B: MATCH THE FOLLOWING
    story.append(Paragraph("B. MATCH THE FOLLOWING", sec_style))

    match_rows_1 = [
        [Paragraph("<b>Column A</b>", match_hdr_style), Paragraph("<b>Column B</b>", match_hdr_style)],
        [Paragraph("1. Alluvial Soil", match_txt_style), Paragraph("a) Rajasthan - Wind erosion", match_txt_style)],
        [Paragraph("2. Black Soil", match_txt_style), Paragraph("b) Roots hold soil", match_txt_style)],
        [Paragraph("3. Red Soil", match_txt_style), Paragraph("c) Near Ganga, Kaveri - Grows Rice", match_txt_style)],
        [Paragraph("4. Sandy Soil", match_txt_style), Paragraph("d) Steps on hills to stop erosion", match_txt_style)],
        [Paragraph("5. Humus", match_txt_style), Paragraph("e) Maharashtra - Grows Cotton", match_txt_style)],
        [Paragraph("6. Soil Erosion", match_txt_style), Paragraph("f) Tamil Nadu - Grows Millets", match_txt_style)],
        [Paragraph("7. Deforestation", match_txt_style), Paragraph("g) Topsoil washed away", match_txt_style)],
        [Paragraph("8. Afforestation", match_txt_style), Paragraph("h) Dead leaves makes soil fertile", match_txt_style)],
    ]
    t1 = Table(match_rows_1, colWidths=[240, 260])
    t1.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t1)

    # Page 3
    story.append(PageBreak())

    match_rows_2 = [
        [Paragraph("9. Terrace Farming", match_txt_style), Paragraph("i) Cutting trees causes erosion", match_txt_style)],
        [Paragraph("10. Grass / Trees", match_txt_style), Paragraph("j) Planting more trees", match_txt_style)],
    ]
    t2 = Table(match_rows_2, colWidths=[240, 260])
    t2.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t2)

    # Section C: FILL IN THE BLANKS
    story.append(Paragraph("C. FILL IN THE BLANKS", sec_style))
    story.append(Spacer(1, 4))

    blanks = [
        "1. Soil contains stones, humus, ____ and water.",
        "2. ____ soil is good for growing rice and wheat.",
        "3. Black soil is found in Maharashtra and is good for growing ____.",
        "4. Soil erosion means ____ soil is washed away by rain and wind.",
        "5. We can save soil by planting more trees and doing ____ farming in hills."
    ]

    for b in blanks:
        story.append(Paragraph(b, q_style))
        story.append(Spacer(1, 4))

    doc.build(story, canvasmaker=BorderedCanvas)
    print(f"Generated sample reference PDF at: {OUTPUT_PDF}")

if __name__ == "__main__":
    build_reference_worksheet()
