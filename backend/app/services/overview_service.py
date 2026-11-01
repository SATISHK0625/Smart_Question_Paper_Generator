from typing import List, Dict, Any, Tuple
from pathlib import Path
from ..models.schemas import (
    Section, PaperConfig, OverviewData, SectionSummary, ValidationIssue
)

def compute_overview_data(
    sections: List[Section],
    config: PaperConfig,
    page_count: int = 1
) -> OverviewData:
    total_questions = 0
    section_summaries: List[SectionSummary] = []
    total_available_marks = 0.0
    calculated_student_marks = 0.0
    missing_marks_count = 0
    optional_questions_detected = False

    seen_numbers: Dict[str, int] = {}
    numeric_numbers: List[int] = []
    duplicate_numbers: List[str] = []
    numbering_gaps: List[str] = []
    validation_issues: List[ValidationIssue] = []

    for sec in sections:
        sec_q_count = len(sec.questions)
        total_questions += sec_q_count
        sec_marks_sum = 0.0

        for q in sec.questions:
            # Check numbers
            num_clean = q.number.strip()
            seen_numbers[num_clean] = seen_numbers.get(num_clean, 0) + 1
            if num_clean.isdigit():
                numeric_numbers.append(int(num_clean))

            # Marks
            if q.marks is not None:
                sec_marks_sum += q.marks
            else:
                # check subquestions
                if q.subquestions:
                    sub_sum = sum(sq.marks for sq in q.subquestions if sq.marks is not None)
                    if sub_sum > 0:
                        sec_marks_sum += sub_sum
                    else:
                        missing_marks_count += 1
                else:
                    missing_marks_count += 1

            # Check subquestions missing marks
            for sq in q.subquestions:
                if sq.marks is None:
                    missing_marks_count += 1

        total_available_marks += sec_marks_sum

        # Check optional instructions
        expected_sec_marks = sec_marks_sum
        if sec.required_count and sec.required_count < sec_q_count:
            optional_questions_detected = True
            avg_per_q = (sec_marks_sum / sec_q_count) if sec_q_count > 0 else 0.0
            expected_sec_marks = round(sec.required_count * avg_per_q, 2)
            calculated_student_marks += expected_sec_marks
        else:
            calculated_student_marks += sec_marks_sum

        section_summaries.append(SectionSummary(
            section_id=sec.id,
            section_title=sec.title,
            question_count=sec_q_count,
            total_marks_available=round(sec_marks_sum, 2),
            expected_marks=round(expected_sec_marks, 2),
            required_count=sec.required_count,
            instructions=sec.instructions
        ))

    # Check duplicate numbers
    for num, cnt in seen_numbers.items():
        if cnt > 1:
            duplicate_numbers.append(num)
            validation_issues.append(ValidationIssue(
                severity="warning",
                message=f"Question number '{num}' is duplicated {cnt} times.",
                location=f"Question {num}"
            ))

    # Check numbering gaps
    if numeric_numbers:
        sorted_nums = sorted(set(numeric_numbers))
        min_n, max_n = sorted_nums[0], sorted_nums[-1]
        full_set = set(range(min_n, max_n + 1))
        missing_nums = sorted(full_set - set(sorted_nums))
        if missing_nums and len(missing_nums) <= 10:
            for mn in missing_nums:
                gap_str = str(mn)
                numbering_gaps.append(gap_str)
                validation_issues.append(ValidationIssue(
                    severity="info",
                    message=f"Gap detected in question numbering: missing Question {mn}.",
                    location=f"Between {mn-1} and {mn+1}"
                ))

    # Missing marks warning
    if missing_marks_count > 0:
        validation_issues.append(ValidationIssue(
            severity="warning",
            message=f"{missing_marks_count} question(s) or subquestion(s) are missing marks.",
            location="Questions"
        ))

    # Maximum marks comparison (if specified)
    if config.maximum_marks is not None:
        marks_match = abs(calculated_student_marks - config.maximum_marks) < 0.01
        if not marks_match:
            diff = round(calculated_student_marks - config.maximum_marks, 2)
            validation_issues.append(ValidationIssue(
                severity="warning",
                message=f"Marks mismatch: Total calculated student marks ({calculated_student_marks}) does not equal configured maximum marks ({config.maximum_marks}). Difference: {diff:+0.2f}.",
                location="Configuration"
            ))
    else:
        marks_match = True

    return OverviewData(
        total_questions_count=total_questions,
        total_sections_count=len(sections),
        section_summaries=section_summaries,
        total_marks_sum=round(total_available_marks, 2),
        calculated_student_marks=round(calculated_student_marks, 2),
        configured_max_marks=config.maximum_marks,
        marks_match=marks_match,
        optional_questions_detected=optional_questions_detected,
        missing_marks_count=missing_marks_count,
        duplicate_numbers=duplicate_numbers,
        numbering_gaps=numbering_gaps,
        validation_issues=validation_issues,
        page_count=page_count,
        page_size=config.page_size
    )
