import random
import uuid
from typing import List, Dict, Any, Optional, Tuple

from ..models.schemas import (
    BlueprintConfig, BlueprintGenerationResult, BlueprintShortfall,
    AchievedCategoryDistribution, AchievedDistributionReport,
    Section, Question, DiagramMarker
)
from ..db.question_bank_db import QuestionBankRepository


def validate_difficulty_distribution(easy_pct: float, medium_pct: float, hard_pct: float) -> Tuple[bool, str]:
    """Validates that difficulty percentages are non-negative and sum to 100%."""
    if easy_pct < 0 or medium_pct < 0 or hard_pct < 0:
        return False, "Difficulty percentages must be non-negative."
    total = round(easy_pct + medium_pct + hard_pct, 2)
    if abs(total - 100.0) > 0.01:
        return False, f"Difficulty percentages must total 100% (currently {total}%)."
    return True, ""


def find_subset_sum(
    candidates: List[Dict[str, Any]],
    target_sum: float,
    allow_approximate: bool = False
) -> Tuple[Optional[List[Dict[str, Any]]], float]:
    """
    Finds a combination of questions whose marks sum exactly to target_sum.
    If exact match is impossible and allow_approximate is True, returns closest combination.
    Candidates must be distinct questions.
    """
    # Scale to integer cents/units to avoid floating-point issues (e.g. 0.5 -> 5, 1.0 -> 10)
    SCALE = 10
    target_int = int(round(target_sum * SCALE))
    
    # Filter valid positive marks
    items = []
    for c in candidates:
        m = c.get("marks", 1.0)
        if m is not None and m > 0:
            items.append((c, int(round(m * SCALE))))

    # Quick checks
    total_avail = sum(val for _, val in items)
    if total_avail < target_int and not allow_approximate:
        return None, total_avail / SCALE

    # Dynamic programming for subset sum with question retrieval
    # dp[w] = list of indices that form sum w
    dp: Dict[int, List[int]] = {0: []}

    for idx, (_, val) in enumerate(items):
        new_dp = dict(dp)
        for w, path in dp.items():
            new_w = w + val
            if new_w not in new_dp:
                new_dp[new_w] = path + [idx]
                if new_w == target_int:
                    # Found exact match
                    selected = [items[i][0] for i in new_dp[new_w]]
                    return selected, target_sum
        dp = new_dp

    if target_int in dp:
        selected = [items[i][0] for i in dp[target_int]]
        return selected, target_sum

    if not allow_approximate:
        return None, 0.0

    # If approximate allowed, find closest achievable sum
    if not dp:
        return [], 0.0

    closest_w = min(dp.keys(), key=lambda w: (abs(w - target_int), w < target_int))
    selected = [items[i][0] for i in dp[closest_w]]
    return selected, closest_w / SCALE


def find_subset_count(
    candidates: List[Dict[str, Any]],
    target_count: int,
    allow_approximate: bool = False
) -> Tuple[Optional[List[Dict[str, Any]]], int]:
    """Selects target_count questions from candidates."""
    if len(candidates) >= target_count:
        return candidates[:target_count], target_count
    if allow_approximate:
        return candidates[:], len(candidates)
    return None, len(candidates)


def create_question_snapshot_from_bank(bank_q: Dict[str, Any], number: str = "") -> Question:
    """
    Creates an immutable, isolated paper question snapshot from a Question Bank row.
    Retains traceability (bank_question_id, difficulty, topic, chapter)
    and answer fields (rubric, alternative_answers, key_points, correct_answer).
    """
    markers = []
    for m in bank_q.get("diagram_markers", []):
        markers.append(DiagramMarker(
            id=m.get("id") or f"m_{uuid.uuid4().hex[:6]}",
            number=int(m.get("number", 1)),
            x=float(m.get("x", 0.5)),
            y=float(m.get("y", 0.5)),
            label=m.get("label")
        ))

    return Question(
        id=f"snap_{uuid.uuid4().hex[:8]}",
        bank_question_id=bank_q.get("id"),
        number=str(number),
        text=bank_q.get("text", ""),
        marks=float(bank_q.get("marks", 1.0) or 1.0),
        options=list(bank_q.get("options", [])),
        question_type=bank_q.get("question_type", "mcq"),
        matching_left=list(bank_q.get("matching_left", [])),
        matching_right=list(bank_q.get("matching_right", [])),
        matching_answers=dict(bank_q.get("matching_answers", {})),
        image_base64=bank_q.get("image_base64"),
        image_caption=bank_q.get("image_caption"),
        diagram_markers=markers,
        difficulty=bank_q.get("difficulty", "medium"),
        topic=bank_q.get("topic", ""),
        chapter=bank_q.get("chapter", ""),
        correct_answer=bank_q.get("correct_answer", ""),
        explanation=bank_q.get("explanation", ""),
        rubric=bank_q.get("rubric", ""),
        alternative_answers=list(bank_q.get("alternative_answers", [])),
        key_points=list(bank_q.get("key_points", []))
    )


def organize_into_sections(
    questions: List[Question],
    section_structure: str = "by_type"
) -> List[Section]:
    """Organizes selected questions into formatted examination sections."""
    if not questions:
        return []

    sections: List[Section] = []

    if section_structure == "by_type":
        # Group by type in logical examination order
        type_order = [
            ("mcq", "Section A", "Multiple Choice Questions", "Choose the correct option for each question:"),
            ("true_false", "Section B", "True or False", "State whether the following statements are True or False:"),
            ("fill_in_the_blanks", "Section C", "Fill in the Blanks", "Fill in the blanks with suitable words:"),
            ("matching", "Section D", "Match the Following", "Match the items in Column A with Column B:"),
            ("short_answer", "Section E", "Short Answer Questions", "Answer the following questions briefly:"),
            ("long_answer", "Section F", "Long Answer Questions", "Answer the following questions in detail:"),
            ("image_based", "Section G", "Image-Based Questions", "Observe the figures and answer the questions:"),
            ("diagram_identify", "Section H", "Diagram Identification", "Identify the numbered parts in the diagrams:")
        ]

        assigned_q_ids = set()
        sec_letter_idx = 0
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        for q_type, _, type_title, default_instr in type_order:
            matching_qs = [q for q in questions if (q.question_type or "").lower() == q_type and q.id not in assigned_q_ids]
            if matching_qs:
                letter = alphabet[sec_letter_idx] if sec_letter_idx < len(alphabet) else f"S{sec_letter_idx}"
                sec_letter_idx += 1
                total_m = sum(q.marks or 1.0 for q in matching_qs)
                sections.append(Section(
                    id=f"sec_{letter.lower()}_{uuid.uuid4().hex[:6]}",
                    title=f"Section {letter}: {type_title}",
                    instructions=default_instr,
                    question_type=q_type,
                    questions=matching_qs,
                    total_marks_available=total_m,
                    expected_marks=total_m,
                    required_count=len(matching_qs)
                ))
                for q in matching_qs:
                    assigned_q_ids.add(q.id)

        # Catch-all for any other question types
        remaining_qs = [q for q in questions if q.id not in assigned_q_ids]
        if remaining_qs:
            letter = alphabet[sec_letter_idx] if sec_letter_idx < len(alphabet) else f"S{sec_letter_idx}"
            total_m = sum(q.marks or 1.0 for q in remaining_qs)
            sections.append(Section(
                id=f"sec_{letter.lower()}_{uuid.uuid4().hex[:6]}",
                title=f"Section {letter}: General Questions",
                instructions="Answer all of the following questions:",
                question_type="mixed",
                questions=remaining_qs,
                total_marks_available=total_m,
                expected_marks=total_m,
                required_count=len(remaining_qs)
            ))

    elif section_structure == "by_difficulty":
        diff_order = [
            ("easy", "Section A", "Knowledge & Recall (Easy)", "Answer the following fundamental questions:"),
            ("medium", "Section B", "Understanding & Application (Medium)", "Answer the following conceptual questions:"),
            ("hard", "Section C", "Higher-Order Thinking & Analysis (Hard)", "Answer the following advanced analytical questions:")
        ]
        assigned_q_ids = set()
        for diff_key, sec_code, sec_title, default_instr in diff_order:
            matching_qs = [q for q in questions if (q.difficulty or "medium").lower() == diff_key and q.id not in assigned_q_ids]
            if matching_qs:
                total_m = sum(q.marks or 1.0 for q in matching_qs)
                sections.append(Section(
                    id=f"sec_{diff_key}_{uuid.uuid4().hex[:6]}",
                    title=f"{sec_code}: {sec_title}",
                    instructions=default_instr,
                    question_type="mixed",
                    questions=matching_qs,
                    total_marks_available=total_m,
                    expected_marks=total_m,
                    required_count=len(matching_qs)
                ))
                for q in matching_qs:
                    assigned_q_ids.add(q.id)

        remaining_qs = [q for q in questions if q.id not in assigned_q_ids]
        if remaining_qs:
            total_m = sum(q.marks or 1.0 for q in remaining_qs)
            sections.append(Section(
                id=f"sec_other_{uuid.uuid4().hex[:6]}",
                title="Section D: Additional Questions",
                instructions="Answer the following questions:",
                question_type="mixed",
                questions=remaining_qs,
                total_marks_available=total_m,
                expected_marks=total_m,
                required_count=len(remaining_qs)
            ))

    else:
        # Single Section
        total_m = sum(q.marks or 1.0 for q in questions)
        sections.append(Section(
            id=f"sec_all_{uuid.uuid4().hex[:6]}",
            title="Section A: Examination Questions",
            instructions="Answer all questions carefully.",
            question_type="mixed",
            questions=questions,
            total_marks_available=total_m,
            expected_marks=total_m,
            required_count=len(questions)
        ))

    # Number all questions sequentially across sections
    q_counter = 1
    for sec in sections:
        for q in sec.questions:
            q.number = str(q_counter)
            q_counter += 1

    return sections


def generate_exam_blueprint(config: BlueprintConfig) -> BlueprintGenerationResult:
    """
    Executes the deterministic Tag-Based Exam Blueprint Generation algorithm.
    Follows Steps A, B, C, D strictly as specified in Feature 4 requirements.
    """
    # 1. Validate percentage distribution
    easy_pct = float(config.difficulty_distribution.easy)
    med_pct = float(config.difficulty_distribution.medium)
    hard_pct = float(config.difficulty_distribution.hard)
    is_valid, err_msg = validate_difficulty_distribution(easy_pct, med_pct, hard_pct)
    if not is_valid:
        raise ValueError(err_msg)

    # 2. Step A: Retrieve eligible questions from Question Bank
    all_questions, _ = QuestionBankRepository.list_and_search(limit=500, offset=0)

    # Filter by Subject
    if config.subject and config.subject.strip():
        req_sub = config.subject.strip().lower()
        all_questions = [q for q in all_questions if (q.get("subject") or "").strip().lower() == req_sub]

    # Filter by Class / Grade
    if config.class_level and config.class_level.strip():
        req_cls = config.class_level.strip().lower()
        all_questions = [q for q in all_questions if (q.get("class_level") or "").strip().lower() == req_cls]

    # Filter by Topic / Chapter
    if config.chapter and config.chapter.strip():
        req_ch = config.chapter.strip().lower()
        all_questions = [q for q in all_questions if (q.get("chapter") or "").strip().lower() == req_ch]

    if config.topic and config.topic.strip():
        req_tp = config.topic.strip().lower()
        all_questions = [q for q in all_questions if (q.get("topic") or "").strip().lower() == req_tp]

    # Filter by Question Types if specified
    if config.question_types and len(config.question_types) > 0:
        req_types = {t.lower().strip() for t in config.question_types if t.strip()}
        all_questions = [q for q in all_questions if (q.get("question_type") or "mcq").lower().strip() in req_types]

    # Separate unlabeled difficulty questions
    unlabeled_questions = []
    categorized_questions = []
    for q in all_questions:
        diff = (q.get("difficulty") or "").strip().lower()
        if diff in ["easy", "medium", "hard"]:
            categorized_questions.append(q)
        else:
            unlabeled_questions.append(q)

    # Group eligible questions by difficulty
    easy_pool = [q for q in categorized_questions if (q.get("difficulty") or "").lower() == "easy"]
    med_pool = [q for q in categorized_questions if (q.get("difficulty") or "").lower() == "medium"]
    hard_pool = [q for q in categorized_questions if (q.get("difficulty") or "").lower() == "hard"]

    # Deduplicate locked questions and partition
    locked_ids = set(config.locked_question_ids or [])
    locked_questions = [q for q in categorized_questions if q.get("id") in locked_ids]

    # Deterministic sorting or seed-based shuffle
    rng = random.Random(config.random_seed) if config.random_seed is not None else None
    for pool in [easy_pool, med_pool, hard_pool]:
        if rng:
            rng.shuffle(pool)
        else:
            # Stable deterministic sort: marks DESC, then ID ASC
            pool.sort(key=lambda x: (-float(x.get("marks", 1.0) or 1.0), str(x.get("id"))))

    # 3. Step B: Calculate targets
    total_target_marks = float(config.total_marks or 100.0)
    basis = config.distribution_basis or "marks"

    shortfalls: List[BlueprintShortfall] = []
    unmet_requirements: List[str] = []
    suggestions: List[str] = []

    selected_bank_questions: List[Dict[str, Any]] = []
    selected_ids = set()

    # Pre-select locked questions
    for lq in locked_questions:
        if lq.get("id") not in selected_ids:
            selected_bank_questions.append(lq)
            selected_ids.add(lq.get("id"))

    # Remaining pools (excluding locked ones already picked)
    easy_candidates = [q for q in easy_pool if q.get("id") not in selected_ids]
    med_candidates = [q for q in med_pool if q.get("id") not in selected_ids]
    hard_candidates = [q for q in hard_pool if q.get("id") not in selected_ids]

    rounding_note: Optional[str] = None

    if basis == "marks":
        # Calculate marks targets
        target_easy_m = round(total_target_marks * (easy_pct / 100.0), 2)
        target_med_m = round(total_target_marks * (med_pct / 100.0), 2)
        target_hard_m = round(total_target_marks * (hard_pct / 100.0), 2)

        # Check rounding discrepancy
        target_sum = round(target_easy_m + target_med_m + target_hard_m, 2)
        if target_sum != total_target_marks:
            diff = round(total_target_marks - target_sum, 2)
            target_med_m = round(target_med_m + diff, 2)
            rounding_note = f"Difficulty mark allocation adjusted by {diff} marks to match exact total paper marks ({total_target_marks})."

        # Subtract already locked marks in each category
        locked_easy_m = sum(float(q.get("marks", 1.0) or 1.0) for q in selected_bank_questions if (q.get("difficulty") or "").lower() == "easy")
        locked_med_m = sum(float(q.get("marks", 1.0) or 1.0) for q in selected_bank_questions if (q.get("difficulty") or "").lower() == "medium")
        locked_hard_m = sum(float(q.get("marks", 1.0) or 1.0) for q in selected_bank_questions if (q.get("difficulty") or "").lower() == "hard")

        need_easy_m = max(0.0, round(target_easy_m - locked_easy_m, 2))
        need_med_m = max(0.0, round(target_med_m - locked_med_m, 2))
        need_hard_m = max(0.0, round(target_hard_m - locked_hard_m, 2))

        # Easy Selection
        easy_sel, easy_ach = find_subset_sum(easy_candidates, need_easy_m, config.allow_approximate)
        if easy_sel is None:
            avail_m = sum(float(q.get("marks", 1.0) or 1.0) for q in easy_candidates)
            shortfalls.append(BlueprintShortfall(
                category="easy",
                required=need_easy_m,
                available=avail_m,
                shortfall=round(need_easy_m - avail_m, 2),
                message=f"Insufficient Easy questions. Required: {need_easy_m} marks, Available: {avail_m} marks."
            ))
            unmet_requirements.append(f"Cannot assemble {need_easy_m} marks of Easy questions.")
            suggestions.append("Add more Easy questions to the Question Bank or enable 'Approximate Distribution'.")
        else:
            for q in easy_sel:
                selected_bank_questions.append(q)
                selected_ids.add(q.get("id"))

        # Medium Selection
        med_sel, med_ach = find_subset_sum(med_candidates, need_med_m, config.allow_approximate)
        if med_sel is None:
            avail_m = sum(float(q.get("marks", 1.0) or 1.0) for q in med_candidates)
            shortfalls.append(BlueprintShortfall(
                category="medium",
                required=need_med_m,
                available=avail_m,
                shortfall=round(need_med_m - avail_m, 2),
                message=f"Insufficient Medium questions. Required: {need_med_m} marks, Available: {avail_m} marks."
            ))
            unmet_requirements.append(f"Cannot assemble {need_med_m} marks of Medium questions.")
            suggestions.append("Add more Medium questions to the Question Bank or relax the chapter/topic filter.")
        else:
            for q in med_sel:
                selected_bank_questions.append(q)
                selected_ids.add(q.get("id"))

        # Hard Selection
        hard_sel, hard_ach = find_subset_sum(hard_candidates, need_hard_m, config.allow_approximate)
        if hard_sel is None:
            avail_m = sum(float(q.get("marks", 1.0) or 1.0) for q in hard_candidates)
            shortfalls.append(BlueprintShortfall(
                category="hard",
                required=need_hard_m,
                available=avail_m,
                shortfall=round(need_hard_m - avail_m, 2),
                message=f"Insufficient Hard questions. Required: {need_hard_m} marks, Available: {avail_m} marks."
            ))
            unmet_requirements.append(f"Cannot assemble {need_hard_m} marks of Hard questions.")
            suggestions.append("Add more Hard questions with required mark values to the Question Bank.")
        else:
            for q in hard_sel:
                selected_bank_questions.append(q)
                selected_ids.add(q.get("id"))

    else:
        # Basis is Question Count
        target_count = config.target_question_count or 20
        target_easy_c = round(target_count * (easy_pct / 100.0))
        target_med_c = round(target_count * (med_pct / 100.0))
        target_hard_c = target_count - target_easy_c - target_med_c

        locked_easy_c = sum(1 for q in selected_bank_questions if (q.get("difficulty") or "").lower() == "easy")
        locked_med_c = sum(1 for q in selected_bank_questions if (q.get("difficulty") or "").lower() == "medium")
        locked_hard_c = sum(1 for q in selected_bank_questions if (q.get("difficulty") or "").lower() == "hard")

        need_easy_c = max(0, target_easy_c - locked_easy_c)
        need_med_c = max(0, target_med_c - locked_med_c)
        need_hard_c = max(0, target_hard_c - locked_hard_c)

        easy_sel, _ = find_subset_count(easy_candidates, need_easy_c, config.allow_approximate)
        if easy_sel is None:
            shortfalls.append(BlueprintShortfall(
                category="easy",
                required=float(need_easy_c),
                available=float(len(easy_candidates)),
                shortfall=float(need_easy_c - len(easy_candidates)),
                message=f"Insufficient Easy questions count. Required: {need_easy_c}, Available: {len(easy_candidates)}."
            ))
        else:
            for q in easy_sel:
                selected_bank_questions.append(q)
                selected_ids.add(q.get("id"))

        med_sel, _ = find_subset_count(med_candidates, need_med_c, config.allow_approximate)
        if med_sel is None:
            shortfalls.append(BlueprintShortfall(
                category="medium",
                required=float(need_med_c),
                available=float(len(med_candidates)),
                shortfall=float(need_med_c - len(med_candidates)),
                message=f"Insufficient Medium questions count. Required: {need_med_c}, Available: {len(med_candidates)}."
            ))
        else:
            for q in med_sel:
                selected_bank_questions.append(q)
                selected_ids.add(q.get("id"))

        hard_sel, _ = find_subset_count(hard_candidates, need_hard_c, config.allow_approximate)
        if hard_sel is None:
            shortfalls.append(BlueprintShortfall(
                category="hard",
                required=float(need_hard_c),
                available=float(len(hard_candidates)),
                shortfall=float(need_hard_c - len(hard_candidates)),
                message=f"Insufficient Hard questions count. Required: {need_hard_c}, Available: {len(hard_candidates)}."
            ))
        else:
            for q in hard_sel:
                selected_bank_questions.append(q)
                selected_ids.add(q.get("id"))

    # Convert selected bank questions to immutable Question objects
    selected_paper_questions: List[Question] = []
    for q in selected_bank_questions:
        q_obj = create_question_snapshot_from_bank(q)
        if q.get("id") in locked_ids:
            q_obj.is_locked = True
        selected_paper_questions.append(q_obj)

    # 4. Step D: Organize into sections
    sections = organize_into_sections(selected_paper_questions, config.section_structure or "by_type")

    # Calculate achieved statistics
    achieved_easy_m = sum(q.marks or 1.0 for q in selected_paper_questions if (q.difficulty or "").lower() == "easy")
    achieved_med_m = sum(q.marks or 1.0 for q in selected_paper_questions if (q.difficulty or "").lower() == "medium")
    achieved_hard_m = sum(q.marks or 1.0 for q in selected_paper_questions if (q.difficulty or "").lower() == "hard")
    achieved_total_m = round(achieved_easy_m + achieved_med_m + achieved_hard_m, 2)

    achieved_easy_c = sum(1 for q in selected_paper_questions if (q.difficulty or "").lower() == "easy")
    achieved_med_c = sum(1 for q in selected_paper_questions if (q.difficulty or "").lower() == "medium")
    achieved_hard_c = sum(1 for q in selected_paper_questions if (q.difficulty or "").lower() == "hard")
    total_q_count = len(selected_paper_questions)

    # Calculate achieved percentages
    ach_easy_pct = round((achieved_easy_m / achieved_total_m * 100.0) if achieved_total_m > 0 else 0.0, 1) if basis == "marks" else round((achieved_easy_c / total_q_count * 100.0) if total_q_count > 0 else 0.0, 1)
    ach_med_pct = round((achieved_med_m / achieved_total_m * 100.0) if achieved_total_m > 0 else 0.0, 1) if basis == "marks" else round((achieved_med_c / total_q_count * 100.0) if total_q_count > 0 else 0.0, 1)
    ach_hard_pct = round((achieved_hard_m / achieved_total_m * 100.0) if achieved_total_m > 0 else 0.0, 1) if basis == "marks" else round((achieved_hard_c / total_q_count * 100.0) if total_q_count > 0 else 0.0, 1)

    target_easy_pct = easy_pct
    target_med_pct = med_pct
    target_hard_pct = hard_pct

    achieved_report = AchievedDistributionReport(
        distribution_basis=basis,
        total_marks=achieved_total_m,
        total_questions=total_q_count,
        easy=AchievedCategoryDistribution(
            target_marks=round(total_target_marks * (easy_pct / 100.0), 2) if basis == "marks" else float(target_easy_c if 'target_easy_c' in locals() else 0),
            achieved_marks=achieved_easy_m if basis == "marks" else float(achieved_easy_c),
            target_percentage=target_easy_pct,
            achieved_percentage=ach_easy_pct,
            question_count=achieved_easy_c
        ),
        medium=AchievedCategoryDistribution(
            target_marks=round(total_target_marks * (med_pct / 100.0), 2) if basis == "marks" else float(target_med_c if 'target_med_c' in locals() else 0),
            achieved_marks=achieved_med_m if basis == "marks" else float(achieved_med_c),
            target_percentage=target_med_pct,
            achieved_percentage=ach_med_pct,
            question_count=achieved_med_c
        ),
        hard=AchievedCategoryDistribution(
            target_marks=round(total_target_marks * (hard_pct / 100.0), 2) if basis == "marks" else float(target_hard_c if 'target_hard_c' in locals() else 0),
            achieved_marks=achieved_hard_m if basis == "marks" else float(achieved_hard_c),
            target_percentage=target_hard_pct,
            achieved_percentage=ach_hard_pct,
            question_count=achieved_hard_c
        ),
        unlabeled_count=len(unlabeled_questions),
        rounding_note=rounding_note
    )

    is_exact = (len(shortfalls) == 0) and (
        (achieved_total_m == total_target_marks) if basis == "marks" else (total_q_count == (config.target_question_count or 0))
    )

    is_approximate = not is_exact and config.allow_approximate

    # Persistence in blueprints DB table
    bp_dict = {
        "id": config.id or f"bp_{uuid.uuid4().hex[:10]}",
        "name": config.name or "Exam Blueprint",
        "subject": config.subject,
        "class_level": config.class_level,
        "chapter": config.chapter,
        "topic": config.topic,
        "total_marks": total_target_marks,
        "target_question_count": config.target_question_count,
        "distribution_basis": basis,
        "easy_pct": easy_pct,
        "medium_pct": med_pct,
        "hard_pct": hard_pct,
        "question_types": config.question_types,
        "allow_approximate": config.allow_approximate,
        "section_structure": config.section_structure,
        "locked_question_ids": list(locked_ids),
        "selected_question_ids": [q.bank_question_id for q in selected_paper_questions if q.bank_question_id],
        "question_snapshots": [q.model_dump() for q in selected_paper_questions],
        "achieved_distribution": achieved_report.model_dump(),
        "random_seed": config.random_seed
    }

    try:
        QuestionBankRepository.create_blueprint(bp_dict)
    except Exception:
        # If ID exists, try update
        try:
            QuestionBankRepository.update_blueprint(bp_dict["id"], bp_dict)
        except Exception:
            pass

    return BlueprintGenerationResult(
        blueprint_id=bp_dict["id"],
        name=config.name,
        config=config,
        sections=sections,
        selected_question_ids=[q.bank_question_id for q in selected_paper_questions if q.bank_question_id],
        total_marks=achieved_total_m,
        total_questions=total_q_count,
        achieved_distribution=achieved_report,
        is_exact_match=is_exact,
        is_approximate=is_approximate,
        shortfalls=shortfalls,
        unmet_requirements=unmet_requirements,
        suggestions=suggestions,
        unlabeled_questions_found=len(unlabeled_questions),
        locked_question_count=len(locked_questions)
    )
