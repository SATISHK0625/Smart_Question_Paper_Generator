import re
import uuid
from typing import List, Tuple, Optional, Dict, Any
from ..models.schemas import Section, Question, SubQuestion, ParseQuestionsResponse

WORD_TO_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
}

# Regex for standard section headers (e.g. PART A, SECTION B, MODULE 1)
STANDARD_SECTION_REGEX = re.compile(
    r"^\s*(?:###\s*)?(PART|SECTION|MODULE|UNIT|GROUP)\s+([A-Z0-9]+|[IVXLCDM]+)(?:\s*[:—–\-\.]\s*(.*))?$",
    re.IGNORECASE
)

# Regex for lettered section headers (e.g. "A. CHOOSE THE CORRECT ANSWER", "(B) CHOOSE THE CORRECT ANSWER", "B. MATCH THE FOLLOWING")
LETTERED_SECTION_REGEX = re.compile(
    r"^\s*(?:\(?([A-Z])\)?[\.\:\-]?\s+)([A-Z\s\-_/&]+)$"
)

# Common section title keywords to avoid false positives with regular single-letter questions
SECTION_KEYWORDS = {
    "CHOOSE", "FILL", "MATCH", "NAME", "ANSWER", "WRITE", "STATE", "SHORT", 
    "QUESTIONS", "TRUE", "FALSE", "MULTIPLE", "IDENTIFY", "GIVE", "EXPLAIN",
    "DEFINE", "DISTINGUISH", "DIFFERENTIATE", "SECTION", "PART"
}

# Regex for question start (e.g., "1.", "1)", "Q1.", "Question 1:", "1 -")
QUESTION_START_REGEX = re.compile(
    r"^\s*(?:Q(?:uestion)?\s*[\.:]?\s*)?(\d{1,3})\s*[\.\)\:\-]\s*(.*)$",
    re.IGNORECASE
)

# Regex for subquestions (e.g. "(a)", "a)", "a.", "(i)", "i)", "i.", "(1)")
SUBQUESTION_START_REGEX = re.compile(
    r"^\s*(?:\(([a-zA-Z]|[ivxlcdmIVXLCDM]+|\d+)\)|([a-zA-Z]|[ivxlcdmIVXLCDM]+)\s*[\.\)]|\b([a-zA-Z]|[ivxlcdmIVXLCDM]+)\))\s+(.*)$"
)

# Regex to detect inline multiple choice options line (e.g. "a) Rock b) Soil c) Water d) Air" or "(a) Hen b) Duck c) Cow d) Sparrow")
MCQ_SPLIT_REGEX = re.compile(
    r"(?:^|\s{1,5})(?:\([a-dA-D]\)|[a-dA-D]\))\s*"
)

# Regex for marks e.g. "(2 marks)", "[5 marks]", "(10M)", "[10]", "(Marks: 5)", "(5 + 5 = 10 marks)"
MARKS_REGEXES = [
    re.compile(r"[\(\[]\s*(\d+)\s*\+\s*(\d+)(?:\s*=\s*(\d+))?\s*(?:marks?|m)?\s*[\)\]]", re.IGNORECASE),
    re.compile(r"[\(\[]\s*(?:marks?\s*[:=]?\s*)?(\d+(?:\.\d+)?)\s*(?:marks?|mark|m|pts?|points?)?\s*[\)\]]\s*$", re.IGNORECASE),
    re.compile(r"\[\s*(\d+(?:\.\d+)?)\s*\]\s*$", re.IGNORECASE),
]

OR_REGEX = re.compile(r"^\s*([—–\-]*\s*OR\s*[—–\-]*)\s*$", re.IGNORECASE)

ANSWER_ANY_REGEX = re.compile(
    r"answer\s+any\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)",
    re.IGNORECASE
)

def extract_marks(text: str) -> Tuple[str, Optional[float]]:
    clean_text = text.strip()
    compound_match = MARKS_REGEXES[0].search(clean_text)
    if compound_match:
        m1, m2, total = compound_match.groups()
        val = float(total) if total else (float(m1) + float(m2))
        clean_text = MARKS_REGEXES[0].sub("", clean_text).strip()
        return clean_text, val

    for regex in MARKS_REGEXES[1:]:
        match = regex.search(clean_text)
        if match:
            try:
                val = float(match.group(1))
                clean_text = regex.sub("", clean_text).strip()
                return clean_text, val
            except (ValueError, IndexError):
                pass

    return clean_text, None

def parse_section_instructions(instructions_str: Optional[str]) -> Tuple[Optional[int], Optional[float]]:
    if not instructions_str:
        return None, None
    req_count = None
    match = ANSWER_ANY_REGEX.search(instructions_str)
    if match:
        token = match.group(1).lower()
        if token.isdigit():
            req_count = int(token)
        elif token in WORD_TO_NUM:
            req_count = WORD_TO_NUM[token]
    return req_count, None

def extract_mcq_options(line: str) -> Optional[List[str]]:
    """
    Checks if a line contains multiple options like 'a) Rock b) Soil c) Water d) Air'
    or '(a) Hen b) Duck c) Cow d) Sparrow' or 'a. Rock b. Soil c. Water d. Air e. Mud'.
    Returns list of formatted options e.g. ['a) Rock', 'b) Soil', 'c) Water', 'd) Air']
    """
    matches = list(re.finditer(r"(?:^|\s+)(\([a-zA-Z0-9]+\)|[a-zA-Z0-9]+[\.\)])\s*([^(\n\r]+?)(?=(?:\s+(?:\([a-zA-Z0-9]+\)|[a-zA-Z0-9]+[\.\)]))|$)", line))
    if len(matches) >= 2:
        options = []
        for m in matches:
            lbl = m.group(1).strip()
            # Normalize to clean label e.g. "a)"
            clean_lbl = lbl if lbl.endswith(")") else f"{lbl})"
            if clean_lbl.startswith("(") and clean_lbl.endswith(")"):
                clean_lbl = clean_lbl[1:-1] + ")"
            val = m.group(2).strip()
            if val:
                options.append(f"{clean_lbl} {val}")
        if len(options) >= 2:
            return options
    return None

def extract_single_mcq_option(line: str) -> Optional[str]:
    """
    Matches a single MCQ option line, e.g. '(a) Hen', 'a) Hen', 'a. Hen', '(1) Option A'.
    Never matches question starts like '8. What is...' or '9. The home of...'.
    """
    m = re.match(r"^\s*(?:\(([a-zA-Z]|[ivxlcdmIVXLCDM]+|[1-9])\)|([a-zA-Z]|[ivxlcdmIVXLCDM]+)[\.\)])\s*(.+)$", line)
    if m:
        lbl = (m.group(1) or m.group(2)).strip()
        val = m.group(3).strip()
        # Exclude questions that end with a question mark
        if val.endswith("?"):
            return None
        clean_lbl = f"{lbl.lower()})"
        return f"{clean_lbl} {val}"
    return None

def parse_matching_columns_line(line: str) -> Optional[Tuple[str, str, str]]:
    """
    Detects if line is a matching row with Column A and Column B items.
    e.g. '1. Alluvial Soil        a) Rajasthan - Wind erosion'
    Returns (item_num, col_a_text, col_b_text)
    """
    # Look for item number on left, and option letter in middle/right
    m = re.match(r"^\s*(\d+)\.\s*(.*?)\s{2,}(?:([a-z]\))\s*(.*)|(.*))", line)
    if m:
        num = m.group(1)
        col_a = m.group(2).strip()
        opt_letter = m.group(3)
        col_b_rest = m.group(4)
        if opt_letter and col_b_rest:
            col_b = f"{opt_letter} {col_b_rest.strip()}"
            return num, col_a, col_b
        elif m.group(5):
            return num, col_a, m.group(5).strip()
    return None

def parse_questions_text(raw_text: str) -> ParseQuestionsResponse:
    lines = [line.rstrip() for line in raw_text.splitlines()]
    
    sections: List[Section] = []
    extracted_instructions: List[str] = []
    warnings: List[str] = []
    uncertain_count = 0

    current_section: Section = Section(
        id=f"sec-{uuid.uuid4().hex[:6]}",
        title="SECTION A",
        instructions=None,
        questions=[]
    )
    has_custom_sections = False

    current_question: Optional[Question] = None
    current_subquestion: Optional[SubQuestion] = None
    in_matching_section = False
    in_mcq_section = False

    seen_numbers = set()

    def finalize_subquestion():
        nonlocal current_subquestion, current_question, uncertain_count
        if current_subquestion and current_question:
            current_question.subquestions.append(current_subquestion)
            current_subquestion = None

    def finalize_question():
        nonlocal current_question, current_section, uncertain_count
        finalize_subquestion()
        if current_question:
            if current_question.subquestions:
                sub_marks = [sq.marks for sq in current_question.subquestions if sq.marks is not None]
                if current_question.marks is None and sub_marks:
                    current_question.marks = sum(sub_marks)

            if current_question.marks is None:
                current_question.is_flagged = True
                current_question.flag_reason = "No marks detected for this question."
                uncertain_count += 1

            sec_key = (current_section.id, current_question.number)
            if sec_key in seen_numbers:
                current_question.is_flagged = True
                current_question.flag_reason = f"Duplicate question number '{current_question.number}' in this section."
                uncertain_count += 1
                warnings.append(f"Duplicate question number '{current_question.number}' detected.")
            else:
                seen_numbers.add(sec_key)

            current_section.questions.append(current_question)
            current_question = None

    def finalize_section():
        nonlocal current_section, sections
        finalize_question()
        if current_section.questions or current_section.instructions:
            total_avail = sum(q.marks or 0.0 for q in current_section.questions)
            current_section.total_marks_available = round(total_avail, 2)
            
            req_count, _ = parse_section_instructions(current_section.instructions)
            if req_count is not None and len(current_section.questions) > 0:
                current_section.required_count = req_count
                avg_mark = total_avail / len(current_section.questions) if len(current_section.questions) else 0.0
                current_section.expected_marks = round(req_count * avg_mark, 2)
            else:
                current_section.expected_marks = current_section.total_marks_available

            sections.append(current_section)

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # 1. Check for Standard Section header e.g. "PART A", "SECTION B"
        sec_match = STANDARD_SECTION_REGEX.match(stripped)
        if sec_match:
            sec_type, sec_id, extra_instr = sec_match.groups()
            title = f"{sec_type.upper()} {sec_id.upper()}"
            instructions = extra_instr.strip() if extra_instr else None

            if has_custom_sections or current_section.questions:
                finalize_section()

            has_custom_sections = True
            in_matching_section = "MATCH" in title.upper()
            in_mcq_section = any(k in title.upper() for k in ("MCQ", "CHOOSE", "MULTIPLE", "OBJECTIVE", "CORRECT"))
            current_section = Section(
                id=f"sec-{uuid.uuid4().hex[:6]}",
                title=title,
                instructions=instructions,
                questions=[]
            )
            continue

        # 2. Check for Lettered Section header e.g. "A. CHOOSE THE CORRECT ANSWER", "(B) CHOOSE THE CORRECT ANSWER"
        letter_match = LETTERED_SECTION_REGEX.match(stripped)
        if letter_match:
            letter_id, title_rest = letter_match.groups()
            # Verify that title_rest contains section keywords or is all caps
            words = [w.strip() for w in title_rest.upper().split()]
            if any(w in SECTION_KEYWORDS for w in words) or (title_rest.isupper() and len(title_rest) > 5):
                title = f"{letter_id.upper()}. {title_rest.strip().upper()}"
                
                if has_custom_sections or current_section.questions:
                    finalize_section()

                has_custom_sections = True
                in_matching_section = "MATCH" in title.upper()
                in_mcq_section = any(k in title.upper() for k in ("MCQ", "CHOOSE", "MULTIPLE", "OBJECTIVE", "CORRECT"))
                current_section = Section(
                    id=f"sec-{uuid.uuid4().hex[:6]}",
                    title=title,
                    instructions=None,
                    questions=[]
                )
                continue

        # 3. Check for general preamble / note lines before any section
        if not has_custom_sections and not current_section.questions:
            if stripped.lower().startswith(("here is worksheet", "worksheet", "note:", "instructions:", "general instructions:")):
                extracted_instructions.append(stripped)
                continue

        # 4. Check for Column A / Column B table header line in matching sections
        if in_matching_section and "column a" in stripped.lower() and "column b" in stripped.lower():
            # Table column header, can skip or use as instruction
            continue

        # 5. Check for Matching row e.g. "1. Alluvial Soil   a) Rajasthan - Wind erosion"
        if in_matching_section:
            match_row = parse_matching_columns_line(stripped)
            if match_row:
                item_num, col_a, col_b = match_row
                finalize_question()
                current_question = Question(
                    id=f"q-{uuid.uuid4().hex[:6]}",
                    number=item_num,
                    text=col_a,
                    is_matching=True,
                    matching_col_a=col_a,
                    matching_col_b=col_b,
                    marks=None
                )
                finalize_question()
                continue

        # 6. Check for OR line between questions
        if OR_REGEX.match(stripped):
            if current_question:
                current_question.or_group = "OR"
                continue

        # 7. Check for MCQ options line following a question e.g. "a) Rock b) Soil c) Water d) Air"
        if current_question:
            mcq_opts = extract_mcq_options(stripped)
            if mcq_opts:
                if current_question.options:
                    current_question.options.extend(mcq_opts)
                else:
                    current_question.options = list(mcq_opts)
                continue

            # Support single option line e.g. "a) Hen" following question or preceding options
            single_opt = extract_single_mcq_option(stripped)
            if single_opt and (current_question.options or in_mcq_section):
                c_val, c_marks = extract_marks(stripped)
                if c_marks is None:
                    current_question.options.append(single_opt)
                    continue

        # 8. Check for Question start e.g. "1. The top soft layer..."
        q_match = QUESTION_START_REGEX.match(stripped)
        if q_match:
            q_num, q_rest = q_match.groups()
            clean_q_text, q_marks = extract_marks(q_rest)

            # Check if this line itself has inline options e.g. "1. Which is? a) X b) Y c) Z"
            inline_mcq = extract_mcq_options(clean_q_text)
            if inline_mcq:
                # Remove options part from question text
                first_opt_idx = re.search(r"(?:\([a-dA-D]\)|[a-dA-D]\))\s+", clean_q_text)
                if first_opt_idx:
                    actual_q_text = clean_q_text[:first_opt_idx.start()].strip()
                else:
                    actual_q_text = clean_q_text
                opts = inline_mcq
            else:
                actual_q_text = clean_q_text
                opts = []

            finalize_question()

            current_question = Question(
                id=f"q-{uuid.uuid4().hex[:6]}",
                number=q_num,
                text=actual_q_text,
                marks=q_marks,
                options=opts,
                subquestions=[]
            )
            continue

        # 9. Check for Subquestion start (a), (i), a) when not an inline MCQ
        sq_match = SUBQUESTION_START_REGEX.match(stripped)
        if sq_match and current_question:
            lbl = next(g for g in sq_match.groups()[:3] if g is not None)
            sq_rest = sq_match.group(4)
            clean_sq_text, sq_marks = extract_marks(sq_rest)

            finalize_subquestion()

            clean_label = f"({lbl})" if not (lbl.startswith("(") and lbl.endswith(")")) else lbl

            current_subquestion = SubQuestion(
                id=f"sq-{uuid.uuid4().hex[:6]}",
                label=clean_label,
                text=clean_sq_text,
                marks=sq_marks
            )
            continue

        # 10. Continuation line
        if current_subquestion:
            c_text, c_marks = extract_marks(stripped)
            if c_marks is not None and (c_text == "" or c_text == stripped):
                current_subquestion.marks = c_marks
                if c_text:
                    current_subquestion.text += " " + c_text
            else:
                current_subquestion.text += "\n" + stripped
        elif current_question:
            c_text, c_marks = extract_marks(stripped)
            if c_marks is not None and (c_text == "" or c_text == stripped):
                current_question.marks = c_marks
                if c_text:
                    current_question.text += " " + c_text
            else:
                current_question.text += "\n" + stripped
        else:
            if not current_section.instructions:
                current_section.instructions = stripped
            else:
                current_section.instructions += " " + stripped

    finalize_section()

    total_q_count = sum(len(s.questions) for s in sections)
    if (total_q_count == 0 or uncertain_count >= 3) and len(raw_text.strip()) > 30:
        try:
            from .cloud_llm import ai_parse_ambiguous_questions
            ai_data = ai_parse_ambiguous_questions(raw_text)
            if ai_data and ai_data.get("sections"):
                ai_sections = []
                for s_data in ai_data["sections"]:
                    q_list = []
                    for q_item in s_data.get("questions", []):
                        q_list.append(Question(
                            id=f"q-{uuid.uuid4().hex[:6]}",
                            number=str(q_item.get("number", "")),
                            text=str(q_item.get("text", "")),
                            marks=float(q_item["marks"]) if q_item.get("marks") is not None else None,
                            options=[str(o) for o in q_item.get("options", [])]
                        ))
                    ai_sections.append(Section(
                        id=f"sec-{uuid.uuid4().hex[:6]}",
                        title=str(s_data.get("title", "SECTION A")),
                        instructions=s_data.get("instructions"),
                        questions=q_list
                    ))
                if ai_sections and any(len(s.questions) > 0 for s in ai_sections):
                    return ParseQuestionsResponse(
                        sections=ai_sections,
                        extracted_instructions=extracted_instructions,
                        warnings=warnings + ["Parsed with Cloud AI assistance for irregular question formatting."],
                        uncertain_items_count=0
                    )
        except Exception:
            pass

    if not sections:
        sections.append(Section(
            id=f"sec-{uuid.uuid4().hex[:6]}",
            title="SECTION A",
            instructions=None,
            questions=[]
        ))

    return ParseQuestionsResponse(
        sections=sections,
        extracted_instructions=extracted_instructions,
        warnings=warnings,
        uncertain_items_count=uncertain_count
    )
