from fastapi import APIRouter, UploadFile, File, HTTPException
from ..models.schemas import ParseQuestionsRequest, ParseQuestionsResponse
from ..services.question_parser import parse_questions_text
from ..services.file_importer import extract_text_from_file
from ..utils.file_utils import save_upload_to_temp, cleanup_file, ALLOWED_QUESTION_EXTENSIONS

router = APIRouter()

@router.post("/parse", response_model=ParseQuestionsResponse)
def parse_questions_endpoint(payload: ParseQuestionsRequest):
    """
    Parse pasted raw questions text into sections, questions, subquestions, and marks.
    Preserves exact text.
    """
    if not payload.raw_text.strip():
        raise HTTPException(status_code=400, detail="Question text cannot be empty.")
    try:
        return parse_questions_text(payload.raw_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse questions: {str(e)}")

@router.post("/import")
async def import_questions_file(file: UploadFile = File(...)):
    """
    Import questions from TXT or DOCX file and extract raw text for editing.
    """
    temp_path = None
    try:
        temp_path, original_name = save_upload_to_temp(file, ALLOWED_QUESTION_EXTENSIONS)
        text = extract_text_from_file(temp_path, original_name)
        return {
            "filename": original_name,
            "raw_text": text
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract file text: {str(e)}")
    finally:
        cleanup_file(temp_path)
