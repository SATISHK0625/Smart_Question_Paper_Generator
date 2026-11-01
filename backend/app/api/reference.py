import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from ..models.schemas import ReferenceAnalysis
from ..services.pdf_analyzer import analyze_reference_pdf
from ..utils.file_utils import save_upload_to_temp, cleanup_file, ALLOWED_PDF_EXTENSIONS, REFERENCES_DIR

router = APIRouter()

@router.post("/analyze", response_model=ReferenceAnalysis)
async def analyze_reference(file: UploadFile = File(...)):
    """
    Accept an uploaded reference PDF, extract layout, fonts, margins,
    header/footers, retain original reference PDF in storage, and return structured analysis.
    """
    temp_path = None
    try:
        temp_path, original_name = save_upload_to_temp(file, ALLOWED_PDF_EXTENSIONS)
        analysis = analyze_reference_pdf(temp_path)

        # Retain original reference PDF for exact template preservation during generation
        ref_id = f"ref_{uuid.uuid4().hex[:12]}"
        persistent_path = REFERENCES_DIR / f"{ref_id}.pdf"
        shutil.copy2(temp_path, persistent_path)
        # Also store latest reference pointer
        latest_path = REFERENCES_DIR / "latest_reference.pdf"
        shutil.copy2(temp_path, latest_path)

        analysis.reference_id = ref_id
        analysis.reference_pdf_path = str(persistent_path)

        return analysis
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze PDF: {str(e)}")
    finally:
        cleanup_file(temp_path)
