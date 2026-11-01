from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..models.schemas import (
    BlueprintConfig, BlueprintGenerationResult, BlueprintReplaceRequest,
    Section, Question
)
from ..services.blueprint_service import (
    generate_exam_blueprint, validate_difficulty_distribution,
    create_question_snapshot_from_bank
)
from ..db.question_bank_db import QuestionBankRepository

router = APIRouter()


@router.post("/generate", response_model=BlueprintGenerationResult)
def generate_blueprint_endpoint(payload: BlueprintConfig):
    """
    Executes the Tag-Based Exam Blueprint Generation algorithm.
    Selects eligible questions, satisfies difficulty distribution, and generates a structured paper draft.
    """
    # 1. Validate distribution
    is_valid, msg = validate_difficulty_distribution(
        payload.difficulty_distribution.easy,
        payload.difficulty_distribution.medium,
        payload.difficulty_distribution.hard
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg)

    try:
        result = generate_exam_blueprint(payload)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Blueprint generation failed: {str(e)}")


@router.post("/validate")
def validate_blueprint_config_endpoint(payload: BlueprintConfig):
    """
    Validates blueprint configuration and checks availability in the Question Bank.
    """
    is_valid, msg = validate_difficulty_distribution(
        payload.difficulty_distribution.easy,
        payload.difficulty_distribution.medium,
        payload.difficulty_distribution.hard
    )
    if not is_valid:
        return {"valid": False, "message": msg}

    # Query matching candidate counts
    questions, total = QuestionBankRepository.list_and_search(limit=500)
    if payload.subject:
        questions = [q for q in questions if (q.get("subject") or "").lower() == payload.subject.lower()]
    if payload.class_level:
        questions = [q for q in questions if (q.get("class_level") or "").lower() == payload.class_level.lower()]
    if payload.chapter:
        questions = [q for q in questions if (q.get("chapter") or "").lower() == payload.chapter.lower()]
    if payload.topic:
        questions = [q for q in questions if (q.get("topic") or "").lower() == payload.topic.lower()]

    easy_count = sum(1 for q in questions if (q.get("difficulty") or "").lower() == "easy")
    med_count = sum(1 for q in questions if (q.get("difficulty") or "").lower() == "medium")
    hard_count = sum(1 for q in questions if (q.get("difficulty") or "").lower() == "hard")
    unlabeled_count = len(questions) - (easy_count + med_count + hard_count)

    easy_marks = sum(float(q.get("marks", 1.0) or 1.0) for q in questions if (q.get("difficulty") or "").lower() == "easy")
    med_marks = sum(float(q.get("marks", 1.0) or 1.0) for q in questions if (q.get("difficulty") or "").lower() == "medium")
    hard_marks = sum(float(q.get("marks", 1.0) or 1.0) for q in questions if (q.get("difficulty") or "").lower() == "hard")

    return {
        "valid": True,
        "message": "Configuration is valid.",
        "pool_summary": {
            "total_questions": len(questions),
            "easy": {"count": easy_count, "marks": easy_marks},
            "medium": {"count": med_count, "marks": med_marks},
            "hard": {"count": hard_count, "marks": hard_marks},
            "unlabeled": {"count": unlabeled_count}
        }
    }


@router.get("")
def list_saved_blueprints():
    """Lists saved blueprints with metadata and achieved distribution."""
    return {"blueprints": QuestionBankRepository.list_blueprints()}


@router.get("/{bp_id}")
def get_blueprint_by_id(bp_id: str):
    """Retrieves a saved blueprint by ID."""
    bp = QuestionBankRepository.get_blueprint(bp_id)
    if not bp:
        raise HTTPException(status_code=404, detail=f"Blueprint '{bp_id}' not found.")
    return bp


@router.delete("/{bp_id}")
def delete_blueprint_by_id(bp_id: str):
    """Deletes a blueprint configuration."""
    success = QuestionBankRepository.delete_blueprint(bp_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Blueprint '{bp_id}' not found or already deleted.")
    return {"success": True, "message": f"Blueprint '{bp_id}' deleted."}


@router.post("/replace-question")
def replace_question_endpoint(payload: BlueprintReplaceRequest):
    """
    Replaces a question in the blueprint draft with another eligible question from the bank,
    preserving question numbering and updating section marks.
    """
    bank_rep = QuestionBankRepository.get_by_id(payload.replacement_question_id)
    if not bank_rep:
        raise HTTPException(status_code=404, detail=f"Replacement question '{payload.replacement_question_id}' not found.")

    found = False
    for sec in payload.sections:
        for idx, q in enumerate(sec.questions):
            if q.id == payload.current_question_id or q.bank_question_id == payload.current_question_id:
                # Create snapshot of replacement
                new_q = create_question_snapshot_from_bank(bank_rep, number=q.number)
                sec.questions[idx] = new_q
                found = True
                break
        if found:
            # Recalculate section marks
            sec.total_marks_available = sum(sq.marks or 1.0 for sq in sec.questions)
            sec.expected_marks = sec.total_marks_available
            break

    if not found:
        raise HTTPException(status_code=404, detail=f"Target question '{payload.current_question_id}' not found in sections.")

    return {"success": True, "sections": payload.sections}
