import sys
import os
import shutil
from pathlib import Path
try:
    import pymupdf as fitz
except ImportError:
    import fitz

sys.path.insert(0, os.path.abspath("backend"))
from app.services.question_parser import parse_questions_text
from app.services.pdf_analyzer import analyze_reference_pdf
from app.services.pdf_generator import generate_pdf
from app.models.schemas import PaperConfig

def main():
    ref_pdf = Path("Class 4 - WORK SHEET 7.pdf")
    if not ref_pdf.exists():
        ref_pdf = Path("backend/test_fixtures/Class 4 - WORK SHEET 7.pdf")

    print(f"Using reference PDF: {ref_pdf.resolve()}")
    analysis = analyze_reference_pdf(ref_pdf)

    # Input text for Science worksheet (Animal Life - II)
    animal_text_path = Path("backend/test_fixtures/animal_life_input.txt")
    raw_text = animal_text_path.read_text(encoding="utf-8")
    parsed = parse_questions_text(raw_text)

    config = PaperConfig(
        subject_name="Science",
        semester_class="Class 5",
        institution_name="", # Keep original school name from reference
        page_size="A4",
        use_reference_header=True,
        show_page_numbers=False
    )

    gen_path, page_count = generate_pdf(
        sections=parsed.sections,
        config=config,
        reference_style=analysis
    )

    print(f"Generated PDF: {gen_path} with {page_count} pages.")
    # Copy to workspace root Science.pdf
    dest_path = Path("Science.pdf").resolve()
    shutil.copy2(gen_path, dest_path)
    print(f"Successfully updated {dest_path}")

    # Render pages for visual verification
    doc = fitz.open(str(dest_path))
    comp_dir = Path("backend/test_fixtures/comparison_results")
    comp_dir.mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(doc):
        pix = p.get_pixmap(dpi=150)
        img_out = comp_dir / f"science_corrected_page_{i+1}.png"
        pix.save(str(img_out))
        print(f"Rendered: {img_out}")
    doc.close()

if __name__ == "__main__":
    main()
