import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import BlueprintConfig, DifficultyDistribution
from app.db.question_bank_db import QuestionBankRepository
from app.services.blueprint_service import generate_exam_blueprint, validate_difficulty_distribution

client = TestClient(app)


@pytest.fixture(autouse=True)
def seed_test_question_bank():
    """Seeds a controlled set of questions in the Question Bank for testing."""
    created_ids = []

    # Easy questions: 5 questions x 2 marks = 10 marks total, 10 questions x 1 mark = 10 marks total -> 20 marks total
    for i in range(1, 6):
        q = QuestionBankRepository.create({
            "text": f"Easy Question 2M #{i}",
            "question_type": "mcq",
            "subject": "Biology",
            "class_level": "Grade 10",
            "chapter": "Cell Biology",
            "topic": "Mitosis",
            "difficulty": "easy",
            "marks": 2.0,
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": f"Explanation for Easy 2M #{i}"
        })
        created_ids.append(q["id"])

    for i in range(1, 11):
        q = QuestionBankRepository.create({
            "text": f"Easy Question 1M #{i}",
            "question_type": "mcq",
            "subject": "Biology",
            "class_level": "Grade 10",
            "chapter": "Cell Biology",
            "topic": "Mitosis",
            "difficulty": "easy",
            "marks": 1.0,
            "options": ["A", "B", "C", "D"],
            "correct_answer": "B",
            "explanation": f"Explanation for Easy 1M #{i}"
        })
        created_ids.append(q["id"])

    # Medium questions: 5 questions x 5 marks = 25 marks, 10 questions x 2.5 marks = 25 marks -> 50 marks total
    for i in range(1, 6):
        q = QuestionBankRepository.create({
            "text": f"Medium Question 5M #{i}",
            "question_type": "short_answer",
            "subject": "Biology",
            "class_level": "Grade 10",
            "chapter": "Cell Biology",
            "topic": "Meiosis",
            "difficulty": "medium",
            "marks": 5.0,
            "correct_answer": f"Model Answer for Medium 5M #{i}",
            "rubric": "Full marks for complete stages explanation.",
            "key_points": ["Prophase I", "Metaphase I"]
        })
        created_ids.append(q["id"])

    for i in range(1, 11):
        q = QuestionBankRepository.create({
            "text": f"Medium Question 2.5M #{i}",
            "question_type": "short_answer",
            "subject": "Biology",
            "class_level": "Grade 10",
            "chapter": "Cell Biology",
            "topic": "Meiosis",
            "difficulty": "medium",
            "marks": 2.5,
            "correct_answer": f"Model Answer for Medium 2.5M #{i}"
        })
        created_ids.append(q["id"])

    # Hard questions: 2 questions x 10 marks = 20 marks total
    for i in range(1, 3):
        q = QuestionBankRepository.create({
            "text": f"Hard Question 10M #{i}",
            "question_type": "long_answer",
            "subject": "Biology",
            "class_level": "Grade 10",
            "chapter": "Genetics",
            "topic": "Inheritance",
            "difficulty": "hard",
            "marks": 10.0,
            "correct_answer": f"Comprehensive solution for Hard 10M #{i}",
            "rubric": "4 marks diagram, 6 marks detailed genetic cross.",
            "key_points": ["Punnett square", "Phenotypic ratio 3:1", "Genotypic ratio 1:2:1"]
        })
        created_ids.append(q["id"])

    # Unlabeled question
    q_unlabeled = QuestionBankRepository.create({
        "text": "Unlabeled Question Without Difficulty",
        "question_type": "mcq",
        "subject": "Biology",
        "class_level": "Grade 10",
        "chapter": "Genetics",
        "difficulty": "", # Missing difficulty
        "marks": 1.0,
        "options": ["X", "Y"]
    })
    created_ids.append(q_unlabeled["id"])

    yield

    # Cleanup seeded questions
    for q_id in created_ids:
        QuestionBankRepository.delete(q_id)


def test_validate_difficulty_distribution():
    # Valid 30/50/20
    valid, _ = validate_difficulty_distribution(30.0, 50.0, 20.0)
    assert valid is True

    # Negative percentage
    valid, msg = validate_difficulty_distribution(-10.0, 60.0, 50.0)
    assert valid is False
    assert "non-negative" in msg

    # Sum not 100%
    valid, msg = validate_difficulty_distribution(40.0, 40.0, 10.0)
    assert valid is False
    assert "100%" in msg


def test_exact_distribution_by_marks():
    # 50 total marks: Easy 30% (15M), Medium 50% (25M), Hard 20% (10M)
    config = BlueprintConfig(
        name="Biology Unit Test",
        subject="Biology",
        class_level="Grade 10",
        total_marks=50.0,
        distribution_basis="marks",
        difficulty_distribution=DifficultyDistribution(easy=30.0, medium=50.0, hard=20.0),
        allow_approximate=False,
        random_seed=42
    )

    result = generate_exam_blueprint(config)
    assert result.is_exact_match is True
    assert result.total_marks == 50.0
    assert len(result.shortfalls) == 0

    ach = result.achieved_distribution
    assert ach.easy.achieved_marks == 15.0
    assert ach.medium.achieved_marks == 25.0
    assert ach.hard.achieved_marks == 10.0
    assert ach.easy.achieved_percentage == 30.0
    assert ach.medium.achieved_percentage == 50.0
    assert ach.hard.achieved_percentage == 20.0

    # Unlabeled questions detected and reported
    assert result.unlabeled_questions_found >= 1


def test_distribution_by_question_count():
    # Target 10 questions: 30% easy (3 Qs), 50% med (5 Qs), 20% hard (2 Qs)
    config = BlueprintConfig(
        name="Biology Quiz",
        subject="Biology",
        target_question_count=10,
        distribution_basis="count",
        difficulty_distribution=DifficultyDistribution(easy=30.0, medium=50.0, hard=20.0),
        allow_approximate=False,
        random_seed=123
    )

    result = generate_exam_blueprint(config)
    assert result.total_questions == 10
    ach = result.achieved_distribution
    assert ach.easy.question_count == 3
    assert ach.medium.question_count == 5
    assert ach.hard.question_count == 2


def test_insufficient_questions_reports_shortfall():
    # Requesting 100 marks of Hard questions when only 20 marks exist
    config = BlueprintConfig(
        name="Impossible Hard Paper",
        subject="Biology",
        total_marks=100.0,
        distribution_basis="marks",
        difficulty_distribution=DifficultyDistribution(easy=10.0, medium=10.0, hard=80.0), # Needs 80M hard, only 20M exist
        allow_approximate=False
    )

    result = generate_exam_blueprint(config)
    assert result.is_exact_match is False
    assert len(result.shortfalls) > 0
    hard_shortfall = next(s for s in result.shortfalls if s.category == "hard")
    assert hard_shortfall.required == 80.0
    assert hard_shortfall.available == 20.0
    assert hard_shortfall.shortfall == 60.0
    assert len(result.suggestions) > 0


def test_approximate_distribution_when_enabled():
    # When allow_approximate=True, it selects the closest available subset
    config = BlueprintConfig(
        name="Approximate Paper",
        subject="Biology",
        total_marks=100.0,
        distribution_basis="marks",
        difficulty_distribution=DifficultyDistribution(easy=10.0, medium=10.0, hard=80.0),
        allow_approximate=True
    )

    result = generate_exam_blueprint(config)
    assert result.is_approximate is True
    # Still succeeds in generating paper with closest achievable distribution
    assert len(result.sections) > 0


def test_deterministic_reproducibility_with_seed():
    config1 = BlueprintConfig(
        name="Seeded Paper 1",
        subject="Biology",
        total_marks=50.0,
        random_seed=999
    )
    res1 = generate_exam_blueprint(config1)

    config2 = BlueprintConfig(
        name="Seeded Paper 2",
        subject="Biology",
        total_marks=50.0,
        random_seed=999
    )
    res2 = generate_exam_blueprint(config2)

    # Identical question IDs in identical order
    q_ids_1 = [q.id for s in res1.sections for q in s.questions]
    q_ids_2 = [q.id for s in res2.sections for q in s.questions]
    bank_ids_1 = [q.bank_question_id for s in res1.sections for q in s.questions]
    bank_ids_2 = [q.bank_question_id for s in res2.sections for q in s.questions]

    assert bank_ids_1 == bank_ids_2


def test_locked_question_preservation():
    # Pick a specific hard question
    hard_qs, _ = QuestionBankRepository.list_and_search(subject="Biology", difficulty="hard", limit=1)
    target_hard_id = hard_qs[0]["id"]

    config = BlueprintConfig(
        name="Locked Question Paper",
        subject="Biology",
        total_marks=50.0,
        locked_question_ids=[target_hard_id]
    )

    result = generate_exam_blueprint(config)
    selected_bank_ids = [q.bank_question_id for s in result.sections for q in s.questions]
    assert target_hard_id in selected_bank_ids

    # Find the locked question in the section
    locked_q = next(q for s in result.sections for q in s.questions if q.bank_question_id == target_hard_id)
    assert locked_q.is_locked is True


def test_api_blueprint_generate_and_replace():
    # 1. Generate via API
    res = client.post("/api/blueprint/generate", json={
        "name": "API Blueprint Test",
        "subject": "Biology",
        "class_level": "Grade 10",
        "total_marks": 50.0,
        "difficulty_distribution": {"easy": 30.0, "medium": 50.0, "hard": 20.0},
        "distribution_basis": "marks"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_exact_match"] is True
    assert data["total_marks"] == 50.0
    bp_id = data["blueprint_id"]

    # 2. List saved blueprints
    list_res = client.get("/api/blueprint")
    assert list_res.status_code == 200
    bps = list_res.json()["blueprints"]
    assert any(b["id"] == bp_id for b in bps)

    # 3. Clean up
    client.delete(f"/api/blueprint/{bp_id}")
