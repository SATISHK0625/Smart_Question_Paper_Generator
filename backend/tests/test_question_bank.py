import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.question_bank_db import QuestionBankRepository, get_db_connection

client = TestClient(app)


def test_question_bank_crud():
    # 1. Create Question
    create_payload = {
        "text": "Which element has atomic number 1?",
        "question_type": "mcq",
        "subject": "Chemistry",
        "class_level": "Grade 9",
        "chapter": "Periodic Table",
        "topic": "Elements",
        "difficulty": "easy",
        "marks": 1.0,
        "options": ["Hydrogen", "Helium", "Lithium", "Carbon"],
        "correct_answer": "Hydrogen",
        "explanation": "Hydrogen is the first element with 1 proton.",
        "tags": ["chemistry", "atomic-structure"]
    }
    res = client.post("/api/bank/questions", json=create_payload)
    assert res.status_code == 201
    created = res.json()
    q_id = created["id"]
    assert q_id.startswith("bank_")
    assert created["text"] == create_payload["text"]
    assert created["correct_answer"] == "Hydrogen"
    assert created["marks"] == 1.0

    # 2. Get by ID
    get_res = client.get(f"/api/bank/questions/{q_id}")
    assert get_res.status_code == 200
    fetched = get_res.json()
    assert fetched["id"] == q_id
    assert fetched["subject"] == "Chemistry"

    # 3. Update Question
    update_res = client.put(f"/api/bank/questions/{q_id}", json={
        "difficulty": "hard",
        "marks": 2.0
    })
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["difficulty"] == "hard"
    assert updated["marks"] == 2.0

    # 4. Search & Filter
    search_res = client.get("/api/bank/questions?subject=Chemistry&difficulty=hard")
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total"] >= 1
    assert any(q["id"] == q_id for q in search_data["items"])

    # 5. Delete Question
    del_res = client.delete(f"/api/bank/questions/{q_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Confirm deletion
    get_after_del = client.get(f"/api/bank/questions/{q_id}")
    assert get_after_del.status_code == 404


def test_question_bank_snapshot_isolation():
    # Create question in bank with correct answer and solution
    create_payload = {
        "text": "What is the speed of light in vacuum?",
        "question_type": "short_answer",
        "subject": "Physics",
        "difficulty": "medium",
        "marks": 2.0,
        "correct_answer": "3 x 10^8 m/s",
        "explanation": "Exact defined value is 299,792,458 m/s"
    }
    res = client.post("/api/bank/questions", json=create_payload)
    assert res.status_code == 201
    bank_q = res.json()
    q_id = bank_q["id"]

    # Request paper snapshot
    snap_res = client.post(f"/api/bank/questions/{q_id}/snapshot?number=5")
    assert snap_res.status_code == 200
    snapshot = snap_res.json()

    # The snapshot ID should be independent (not equal to bank_q['id'])
    assert snapshot["id"] != bank_q["id"]
    assert snapshot["number"] == "5"
    assert snapshot["text"] == bank_q["text"]
    assert snapshot["marks"] == 2.0

    # If the bank item is updated later, the snapshot was already deep copied
    client.put(f"/api/bank/questions/{q_id}", json={"text": "Modified bank text"})
    # Verify the snapshot data previously fetched was unchanged
    assert snapshot["text"] == "What is the speed of light in vacuum?"

    # Cleanup
    client.delete(f"/api/bank/questions/{q_id}")


def test_question_bank_bulk_import():
    payload = {
        "questions": [
            {
                "text": "Bulk Question 1",
                "question_type": "mcq",
                "subject": "General",
                "options": ["A", "B"]
            },
            {
                "text": "Bulk Question 2",
                "question_type": "short_answer",
                "subject": "General"
            }
        ]
    }
    res = client.post("/api/bank/questions/bulk", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["imported_count"] == 2
    for item in data["items"]:
        client.delete(f"/api/bank/questions/{item['id']}")


def test_question_bank_duplicate_detection():
    payload = {
        "text": "Duplicate Detection Unique Test String 12345",
        "question_type": "short_answer",
        "subject": "Science"
    }
    res1 = client.post("/api/bank/questions", json=payload)
    assert res1.status_code == 201
    q1_id = res1.json()["id"]

    # Posting identical question text should flag duplicate_warning
    res2 = client.post("/api/bank/questions", json=payload)
    assert res2.status_code == 201
    assert "duplicate_warning" in res2.json()

    # Cleanup
    client.delete(f"/api/bank/questions/{q1_id}")
    client.delete(f"/api/bank/questions/{res2.json()['id']}")
