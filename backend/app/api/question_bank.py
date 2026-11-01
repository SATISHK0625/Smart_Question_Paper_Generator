from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..db.question_bank_db import QuestionBankRepository
from ..services.question_bank_service import (
    clone_bank_question_to_paper_question,
    check_for_duplicate_question
)
from ..models.schemas import Question

router = APIRouter()


class BankQuestionCreate(BaseModel):
    text: str
    question_type: str = "mcq" # "mcq", "short_answer", "long_answer", "fill_in_the_blanks", "true_false", "matching", "image_based", "diagram_identify"
    subject: Optional[str] = ""
    class_level: Optional[str] = ""
    chapter: Optional[str] = ""
    topic: Optional[str] = ""
    difficulty: Optional[str] = "medium" # "easy", "medium", "hard"
    marks: Optional[float] = 1.0
    options: List[str] = Field(default_factory=list)
    correct_answer: Optional[str] = ""
    explanation: Optional[str] = ""
    matching_left: List[str] = Field(default_factory=list)
    matching_right: List[str] = Field(default_factory=list)
    matching_answers: Dict[str, str] = Field(default_factory=dict)
    image_base64: Optional[str] = ""
    image_caption: Optional[str] = ""
    diagram_markers: List[Dict[str, Any]] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class BankQuestionUpdate(BaseModel):
    text: Optional[str] = None
    question_type: Optional[str] = None
    subject: Optional[str] = None
    class_level: Optional[str] = None
    chapter: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[str] = None
    marks: Optional[float] = None
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    matching_left: Optional[List[str]] = None
    matching_right: Optional[List[str]] = None
    matching_answers: Optional[Dict[str, str]] = None
    image_base64: Optional[str] = None
    image_caption: Optional[str] = None
    diagram_markers: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None


class BulkImportRequest(BaseModel):
    questions: List[BankQuestionCreate]


@router.post("/questions", status_code=status.HTTP_201_CREATED)
def create_question(payload: BankQuestionCreate):
    """Creates a new question in the persistent Question Bank."""
    if not payload.text or not payload.text.strip():
        raise HTTPException(status_code=400, detail="Question text cannot be empty.")

    # Check for near-duplicate
    dup = check_for_duplicate_question(payload.text)
    data = payload.model_dump()
    created = QuestionBankRepository.create(data)
    if dup:
        created["duplicate_warning"] = f"Similar question already exists: '{dup.get('text', '')[:50]}...'"
    return created


@router.get("/questions")
def list_questions(
    search: Optional[str] = Query(None, description="Search keyword in text, topic, chapter"),
    subject: Optional[str] = Query(None),
    class_level: Optional[str] = Query(None),
    chapter: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    question_type: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at", description="created_at, marks, difficulty, text, subject"),
    sort_order: str = Query("desc", description="asc or desc")
):
    """Lists, searches, and filters questions with server-side pagination."""
    items, total = QuestionBankRepository.list_and_search(
        search=search,
        subject=subject,
        class_level=class_level,
        chapter=chapter,
        topic=topic,
        difficulty=difficulty,
        question_type=question_type,
        tag=tag,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "page": (offset // limit) + 1,
        "total_pages": (total + limit - 1) // limit if total > 0 else 1
    }


@router.get("/questions/subjects")
def get_subjects():
    """Returns list of distinct subjects present in the bank."""
    return {"subjects": QuestionBankRepository.get_all_subjects()}


@router.get("/questions/{q_id}")
def get_question(q_id: str):
    """Retrieves a single question by its unique Bank ID."""
    q = QuestionBankRepository.get_by_id(q_id)
    if not q:
        raise HTTPException(status_code=404, detail=f"Question '{q_id}' not found.")
    return q


@router.put("/questions/{q_id}")
def update_question(q_id: str, payload: BankQuestionUpdate):
    """Updates an existing question in the bank."""
    existing = QuestionBankRepository.get_by_id(q_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Question '{q_id}' not found.")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = QuestionBankRepository.update(q_id, update_data)
    return updated


@router.delete("/questions/{q_id}")
def delete_question(q_id: str):
    """Deletes a question from the bank."""
    success = QuestionBankRepository.delete(q_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Question '{q_id}' not found or already deleted.")
    return {"success": True, "message": f"Question '{q_id}' deleted."}


@router.post("/questions/bulk", status_code=status.HTTP_201_CREATED)
def bulk_import_questions(payload: BulkImportRequest):
    """Bulk imports a list of valid questions into the bank."""
    created_items = []
    skipped = 0
    for q_data in payload.questions:
        if not q_data.text or not q_data.text.strip():
            skipped += 1
            continue
        created = QuestionBankRepository.create(q_data.model_dump())
        created_items.append(created)

    return {
        "imported_count": len(created_items),
        "skipped_count": skipped,
        "items": created_items
    }


@router.post("/questions/{q_id}/snapshot")
def get_question_paper_snapshot(q_id: str, number: Optional[str] = Query(None)):
    """
    Creates an independent Question model snapshot for inclusion in a paper section.
    Isolates answer keys from the student-facing document.
    """
    bank_q = QuestionBankRepository.get_by_id(q_id)
    if not bank_q:
        raise HTTPException(status_code=404, detail=f"Question '{q_id}' not found.")

    snapshot = clone_bank_question_to_paper_question(bank_q, number_override=number)
    return snapshot
