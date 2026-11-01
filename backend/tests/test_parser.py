import pytest
from backend.app.services.question_parser import parse_questions_text, extract_marks

def test_extract_marks_various_formats():
    cases = [
        ("Define an algorithm. (2 marks)", 2.0),
        ("Explain a data structure. [5 marks]", 5.0),
        ("Describe binary search tree. (10M)", 10.0),
        ("State Ohm's law. [4]", 4.0),
        ("Write short note on DFS. (Marks: 6)", 6.0),
        ("Calculate impedance and power. (5 + 5 = 10 marks)", 10.0),
        ("Explain recursion without marks stated.", None)
    ]
    for text, expected in cases:
        _, val = extract_marks(text)
        assert val == expected, f"Failed for '{text}': got {val}, expected {expected}"

def test_parse_prompt_sample():
    sample_text = """
PART A — Answer all questions.

1. Define an algorithm. (2 marks)
2. Explain a data structure. (2 marks)

PART B — Answer any two questions.

11. Explain binary search. (10 marks)

12. Describe a sorting algorithm. (10 marks)
"""
    result = parse_questions_text(sample_text)
    assert len(result.sections) == 2

    # Section A
    sec_a = result.sections[0]
    assert sec_a.title == "PART A"
    assert "Answer all questions" in (sec_a.instructions or "")
    assert len(sec_a.questions) == 2
    assert sec_a.questions[0].number == "1"
    assert sec_a.questions[0].marks == 2.0
    assert "algorithm" in sec_a.questions[0].text
    assert sec_a.questions[1].number == "2"
    assert sec_a.questions[1].marks == 2.0
    assert sec_a.total_marks_available == 4.0

    # Section B
    sec_b = result.sections[1]
    assert sec_b.title == "PART B"
    assert "Answer any two" in (sec_b.instructions or "")
    assert sec_b.required_count == 2
    assert len(sec_b.questions) == 2
    assert sec_b.questions[0].number == "11"
    assert sec_b.questions[0].marks == 10.0
    assert sec_b.questions[1].number == "12"
    assert sec_b.questions[1].marks == 10.0
    assert sec_b.total_marks_available == 20.0
    assert sec_b.expected_marks == 20.0

def test_subquestions_parsing():
    sample = """
SECTION A

1. Answer the following:
(a) What is polymorphism? (5 marks)
(b) Explain inheritance with code example. (5 marks)

2. What is encapsulation?
"""
    result = parse_questions_text(sample)
    sec = result.sections[0]
    assert len(sec.questions) == 2
    
    q1 = sec.questions[0]
    assert len(q1.subquestions) == 2
    assert q1.subquestions[0].label == "(a)"
    assert q1.subquestions[0].marks == 5.0
    assert q1.subquestions[1].label == "(b)"
    assert q1.subquestions[1].marks == 5.0
    assert q1.marks == 10.0  # Sum of subquestions

    q2 = sec.questions[1]
    assert q2.marks is None
    assert q2.is_flagged is True
    assert "No marks detected" in (q2.flag_reason or "")
