import os
import sys
from pathlib import Path
try:
    import pymupdf as fitz
except ImportError:
    import fitz

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.schemas import Section, Question, PaperConfig, ReferenceAnalysis
from app.services.pdf_analyzer import analyze_reference_pdf
from app.services.pdf_generator import generate_pdf
from app.services.pdf_comparison_service import run_visual_pdf_comparison
from app.services.quality_checker import run_pre_export_quality_check

OUTPUT_DIR = Path(__file__).parent / "visual_verification_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def run_verification():
    fixtures = [
        Path(__file__).parent / "ref1_cbse_worksheet.pdf",
        Path(__file__).parent / "ref2_university_exam.pdf",
        Path(__file__).parent / "ref3_medical_quiz.pdf"
    ]

    results = []

    for ref_path in fixtures:
        if not ref_path.exists():
            print(f"Skipping missing fixture: {ref_path}")
            continue

        print(f"\n--- Processing Reference: {ref_path.name} ---")
        ref_analysis = analyze_reference_pdf(ref_path)

        # Build realistic questions matching the exam theme
        sections = [
            Section(
                id="sec_1",
                title="SECTION A: OBJECTIVE QUESTIONS",
                questions=[
                    Question(
                        id="q_1",
                        number="1",
                        text="Which of the following is a renewable source of energy?",
                        marks=1.0,
                        question_type="mcq",
                        options=["(a) Solar energy", "(b) Coal", "(c) Petroleum", "(d) Natural gas"]
                    ),
                    Question(
                        id="q_2",
                        number="2",
                        text="What is the unit of electric current?",
                        marks=1.0,
                        question_type="mcq",
                        options=["(a) Volt", "(b) Ampere", "(c) Ohm", "(d) Watt"]
                    )
                ]
            ),
            Section(
                id="sec_2",
                title="SECTION B: DESCRIPTIVE QUESTIONS",
                questions=[
                    Question(
                        id="q_3",
                        number="3",
                        text="Explain the principle of conservation of energy with an illustrative example from daily life.",
                        marks=4.0,
                        question_type="long_answer"
                    ),
                    Question(
                        id="q_4",
                        number="4",
                        text="State Newton's second law of motion and derive the mathematical relation F = ma.",
                        marks=4.0,
                        question_type="short_answer"
                    )
                ]
            )
        ]

        config = PaperConfig(
            institution_name=ref_analysis.header_lines[0].text if ref_analysis.header_lines else "Excellence Academy",
            subject_name="Physics & Natural Science",
            maximum_marks=10.0,
            use_reference_header=True,
            show_page_numbers=ref_analysis.has_page_numbers,
            reference_id=ref_analysis.reference_id,
            reference_pdf_path=str(ref_path)
        )

        # 1. Run Pre-Export Quality Check
        quality_rep = run_pre_export_quality_check(sections, config, ref_analysis)
        print(f"Quality Check Status: {quality_rep.status} (Errors: {quality_rep.error_count}, Warnings: {quality_rep.warning_count})")
        assert quality_rep.can_export is True

        # 2. Generate PDF
        gen_pdf, page_count = generate_pdf(
            sections=sections,
            config=config,
            reference_style=ref_analysis
        )
        print(f"Generated PDF: {gen_pdf.name} ({page_count} pages)")

        # 3. Run Visual PDF Comparison
        comp_rep = run_visual_pdf_comparison(ref_path, gen_pdf)
        print(f"Visual Comparison Status: {comp_rep['overall_status']}")
        print(f"Average Similarity Score: {comp_rep['average_similarity_score']}%")
        print(f"Summary: {comp_rep['summary']}")

        # Copy rendered comparison images for inspection
        for p in comp_rep["pages"]:
            print(f"  Page {p['page_number']}: status={p['status']}, sim={p['similarity_score']}%, layout_var={p['layout_difference_percentage']}%, content_diff={p['content_difference_percentage']}%")

        results.append({
            "fixture": ref_path.name,
            "quality_status": quality_rep.status,
            "overall_comp_status": comp_rep["overall_status"],
            "avg_similarity": comp_rep["average_similarity_score"],
            "gen_pdf": str(gen_pdf),
            "ref_pages": comp_rep["reference_pages"],
            "gen_pages": comp_rep["generated_pages"]
        })

    print("\n=== SUMMARY OF ALL VISUAL VERIFICATIONS ===")
    for r in results:
        print(f"{r['fixture']}: Similarity={r['avg_similarity']}%, Quality={r['quality_status']}, Comp={r['overall_comp_status']}")


if __name__ == "__main__":
    run_verification()
