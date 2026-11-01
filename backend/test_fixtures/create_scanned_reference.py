import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
try:
    import pymupdf as fitz
except ImportError:
    import fitz

def generate_scanned_worksheet_reference(out_path: Path) -> Path:
    """
    Creates an image-based / scanned worksheet PDF:
    - Entire page is a raster scan image (no selectable text).
    - Contains school header emblem, school title, border, and divider line.
    - Scanned question lines in the content area.
    """
    w, h = 1240, 1754  # A4 at ~150 DPI
    img = Image.new("RGB", (w, h), (252, 252, 250)) # Slight paper tint
    draw = ImageDraw.Draw(img)

    # 1. Outer rectangular border (dark slate)
    draw.rectangle([50, 50, w - 50, h - 50], outline=(30, 41, 59), width=3)

    # 2. Header Logo (Shield emblem)
    draw.ellipse([w // 2 - 40, 75, w // 2 + 40, 145], fill=(37, 99, 235))
    draw.ellipse([w // 2 - 30, 85, w // 2 + 30, 135], fill=(255, 255, 255))
    draw.text((w // 2 - 16, 102), "STP", fill=(37, 99, 235))

    # 3. Header text
    draw.text((w // 2 - 180, 160), "ST. PETERS INTERNATIONAL ACADEMY", fill=(15, 23, 42))
    draw.text((w // 2 - 120, 185), "GRADE 8 · BIOLOGY WORKSHEET", fill=(71, 85, 105))
    draw.text((w // 2 - 90, 210), "TERM I ASSESSMENT", fill=(15, 23, 42))

    # 4. Horizontal divider rule
    draw.line([(70, 245), (w - 70, 245)], fill=(37, 99, 235), width=3)

    # 5. Scanned question text (simulated printed text)
    draw.text((80, 275), "SECTION A: PLANT PHYSIOLOGY", fill=(15, 23, 42))
    draw.text((80, 310), "1. Name the pigment present in chloroplasts responsible for trapping light.", fill=(30, 41, 59))
    draw.text((80, 345), "2. Define transpiration and mention two factors affecting transpiration rate.", fill=(30, 41, 59))
    draw.text((80, 380), "3. What is the role of stomata in gaseous exchange during daylight hours?", fill=(30, 41, 59))

    draw.text((80, 430), "SECTION B: CELL STRUCTURE", fill=(15, 23, 42))
    draw.text((80, 465), "4. State three differences between plant cells and animal cells.", fill=(30, 41, 59))
    draw.text((80, 500), "5. Explain the function of mitochondria in cellular energy production.", fill=(30, 41, 59))

    # Convert to PDF
    doc = fitz.open()
    # A4 dimensions in points: 595.28 x 841.89
    page = doc.new_page(width=595.28, height=841.89)

    img_buf = io.BytesIO()
    img.save(img_buf, format="PNG")
    img_bytes = img_buf.getvalue()

    # Insert page image filling entire page
    page.insert_image(fitz.Rect(0, 0, 595.28, 841.89), stream=img_bytes)
    doc.save(str(out_path))
    doc.close()
    return out_path

if __name__ == "__main__":
    import io
    fixtures_dir = Path(__file__).parent
    out = fixtures_dir / "scanned_worksheet_reference.pdf"
    generate_scanned_worksheet_reference(out)
    print("Created scanned reference PDF:", out)
