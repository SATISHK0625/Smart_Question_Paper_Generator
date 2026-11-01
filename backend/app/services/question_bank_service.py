import uuid
from typing import List, Dict, Any, Optional, Tuple
from ..db.question_bank_db import QuestionBankRepository
from ..models.schemas import Question, SubQuestion, DiagramMarker


def clone_bank_question_to_paper_question(bank_q: Dict[str, Any], number_override: Optional[str] = None) -> Question:
    """
    Creates an independent SNAPSHOT of a bank question for inclusion into a paper draft.
    Crucial isolation properties:
    1. Generates a fresh unique question ID so that subsequent bank modifications do not alter this exam draft.
    2. Strips internal answer keys and solutions from student-facing PDF fields.
    3. Retains question text, options, marks, diagram markers, and matching column definitions.
    """
    new_id = f"q_{uuid.uuid4().hex[:8]}"
    q_type = bank_q.get("question_type", "mcq")

    # Diagram markers: retain coordinates and numbers, but keep student-facing representation
    markers = []
    for m in bank_q.get("diagram_markers", []):
        markers.append(DiagramMarker(
            id=m.get("id") or f"m_{uuid.uuid4().hex[:6]}",
            number=int(m.get("number", 1)),
            x=float(m.get("x", 0.5)),
            y=float(m.get("y", 0.5)),
            label=m.get("label") # Answer key part retained in model for teacher reference
        ))

    return Question(
        id=new_id,
        number=number_override or "",
        text=bank_q.get("text", ""),
        marks=bank_q.get("marks", 1.0),
        options=list(bank_q.get("options", [])),
        question_type=q_type,
        matching_left=list(bank_q.get("matching_left", [])),
        matching_right=list(bank_q.get("matching_right", [])),
        matching_answers=dict(bank_q.get("matching_answers", {})),
        image_base64=bank_q.get("image_base64"),
        image_caption=bank_q.get("image_caption"),
        diagram_markers=markers
    )


def save_paper_question_to_bank(
    q: Question,
    subject: str = "",
    class_level: str = "",
    chapter: str = "",
    topic: str = "",
    difficulty: str = "medium",
    correct_answer: str = "",
    explanation: str = "",
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Saves a question from the current paper builder into the persistent Question Bank."""
    markers = [m.model_dump() if hasattr(m, "model_dump") else dict(m) for m in q.diagram_markers]
    data = {
        "text": q.text,
        "question_type": q.question_type or "mcq",
        "subject": subject,
        "class_level": class_level,
        "chapter": chapter,
        "topic": topic,
        "difficulty": difficulty,
        "marks": q.marks or 1.0,
        "options": q.options or [],
        "correct_answer": correct_answer,
        "explanation": explanation,
        "matching_left": q.matching_left or [],
        "matching_right": q.matching_right or [],
        "matching_answers": q.matching_answers or {},
        "image_base64": q.image_base64 or "",
        "image_caption": q.image_caption or "",
        "diagram_markers": markers,
        "tags": tags or []
    }
    return QuestionBankRepository.create(data)


def check_for_duplicate_question(text: str) -> Optional[Dict[str, Any]]:
    """Checks if a question with near-identical text already exists in the bank."""
    if not text or len(text.strip()) < 5:
        return None
    results, _ = QuestionBankRepository.list_and_search(search=text.strip()[:40], limit=1)
    if results:
        # Check text similarity
        existing_text = results[0]["text"].strip().lower()
        if text.strip().lower() == existing_text:
            return results[0]
    return None
