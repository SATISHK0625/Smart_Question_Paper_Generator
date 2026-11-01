from backend.app.models.schemas import Section, Question, SubQuestion, PaperConfig
from backend.app.services.overview_service import compute_overview_data

def test_overview_calculations_and_optional_questions():
    config = PaperConfig(maximum_marks=50.0)

    # Section 1: 5 questions of 2 marks = 10 marks compulsory
    sec1 = Section(
        id="s1",
        title="PART A",
        questions=[Question(id=f"q{i}", number=str(i), text=f"Question {i}", marks=2.0) for i in range(1, 6)]
    )

    # Section 2: 4 questions of 10 marks = 40 marks total, but "Answer any 4" out of 6
    # Let's say 4 questions of 10 marks with required_count = 4 (expected = 40)
    sec2 = Section(
        id="s2",
        title="PART B",
        instructions="Answer any 4 questions (10 marks each)",
        required_count=4,
        questions=[Question(id=f"q{i}", number=str(i), text=f"Question {i}", marks=10.0) for i in range(6, 12)] # 6 questions
    )

    overview = compute_overview_data([sec1, sec2], config)

    assert overview.total_questions_count == 11
    assert overview.total_sections_count == 2
    # Total marks sum of all available questions = 5*2 + 6*10 = 70
    assert overview.total_marks_sum == 70.0
    # Calculated student marks = 10 + 4*10 = 50.0
    assert overview.calculated_student_marks == 50.0
    assert overview.marks_match is True
    assert overview.optional_questions_detected is True
    assert overview.missing_marks_count == 0

def test_overview_validation_issues():
    config = PaperConfig(maximum_marks=100.0)

    # Missing marks, duplicate number, gap in numbering
    # Numbers: 1, 1 (dup), 3 (gap 2 missing)
    sec = Section(
        id="s1",
        title="PART A",
        questions=[
            Question(id="q1", number="1", text="Define Q1", marks=10.0),
            Question(id="q2", number="1", text="Duplicate Q1", marks=None),
            Question(id="q3", number="3", text="Define Q3", marks=10.0)
        ]
    )

    overview = compute_overview_data([sec], config)

    assert overview.missing_marks_count == 1
    assert "1" in overview.duplicate_numbers
    assert "2" in overview.numbering_gaps
    assert overview.marks_match is False  # 20 != 100

    issue_msgs = " ".join(iss.message for iss in overview.validation_issues)
    assert "duplicated" in issue_msgs
    assert "missing Question 2" in issue_msgs
    assert "missing marks" in issue_msgs
    assert "Marks mismatch" in issue_msgs
