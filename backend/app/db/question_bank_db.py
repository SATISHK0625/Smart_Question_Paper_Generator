import sqlite3
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from ..utils.file_utils import TEMP_BASE_DIR

DB_DIR = TEMP_BASE_DIR.parent / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "question_bank.db"

CURRENT_SCHEMA_VERSION = 2


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    # Enable foreign keys and WAL mode for better concurrency
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_database() -> None:
    """Initializes the SQLite database with versioned schema migration."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            );
        """)

        cursor.execute("SELECT MAX(version) FROM schema_version;")
        row = cursor.fetchone()
        current_v = row[0] if (row and row[0] is not None) else 0

        if current_v < 1:
            # Migration 1: Base Question Bank table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    question_type TEXT NOT NULL,
                    subject TEXT DEFAULT '',
                    class_level TEXT DEFAULT '',
                    chapter TEXT DEFAULT '',
                    topic TEXT DEFAULT '',
                    difficulty TEXT DEFAULT 'medium',
                    marks REAL DEFAULT 1.0,
                    options_json TEXT DEFAULT '[]',
                    correct_answer TEXT DEFAULT '',
                    explanation TEXT DEFAULT '',
                    matching_left_json TEXT DEFAULT '[]',
                    matching_right_json TEXT DEFAULT '[]',
                    matching_answers_json TEXT DEFAULT '{}',
                    image_base64 TEXT DEFAULT '',
                    image_caption TEXT DEFAULT '',
                    diagram_markers_json TEXT DEFAULT '[]',
                    tags_json TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_questions_subject ON questions(subject);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_questions_type ON questions(question_type);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions(difficulty);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_questions_class ON questions(class_level);
            """)

            now_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?);",
                (1, now_iso)
            )
            conn.commit()

        if current_v < 2:
            # Migration 2: Rubric, Alternative Answers, Key Points & Blueprint Persistence
            cursor.execute("PRAGMA table_info(questions);")
            columns = [col[1] for col in cursor.fetchall()]
            if "rubric" not in columns:
                cursor.execute("ALTER TABLE questions ADD COLUMN rubric TEXT DEFAULT '';")
            if "alternative_answers_json" not in columns:
                cursor.execute("ALTER TABLE questions ADD COLUMN alternative_answers_json TEXT DEFAULT '[]';")
            if "key_points_json" not in columns:
                cursor.execute("ALTER TABLE questions ADD COLUMN key_points_json TEXT DEFAULT '[]';")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blueprints (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    subject TEXT DEFAULT '',
                    class_level TEXT DEFAULT '',
                    chapter TEXT DEFAULT '',
                    topic TEXT DEFAULT '',
                    total_marks REAL DEFAULT 100.0,
                    target_question_count INTEGER DEFAULT NULL,
                    distribution_basis TEXT DEFAULT 'marks',
                    easy_pct REAL DEFAULT 30.0,
                    medium_pct REAL DEFAULT 50.0,
                    hard_pct REAL DEFAULT 20.0,
                    question_types_json TEXT DEFAULT '[]',
                    allow_approximate INTEGER DEFAULT 0,
                    section_structure TEXT DEFAULT 'by_type',
                    locked_question_ids_json TEXT DEFAULT '[]',
                    selected_question_ids_json TEXT DEFAULT '[]',
                    question_snapshots_json TEXT DEFAULT '[]',
                    achieved_distribution_json TEXT DEFAULT '{}',
                    random_seed INTEGER DEFAULT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_blueprints_subject ON blueprints(subject);
            """)

            now_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?);",
                (2, now_iso)
            )
            conn.commit()
    finally:
        conn.close()


# Ensure DB schema is created at import time
init_database()


def row_to_question_dict(row: sqlite3.Row) -> Dict[str, Any]:
    if not row:
        return {}
    d = dict(row)
    try:
        d["options"] = json.loads(d.pop("options_json", "[]") or "[]")
    except Exception:
        d["options"] = []

    try:
        d["matching_left"] = json.loads(d.pop("matching_left_json", "[]") or "[]")
    except Exception:
        d["matching_left"] = []

    try:
        d["matching_right"] = json.loads(d.pop("matching_right_json", "[]") or "[]")
    except Exception:
        d["matching_right"] = []

    try:
        d["matching_answers"] = json.loads(d.pop("matching_answers_json", "{}") or "{}")
    except Exception:
        d["matching_answers"] = {}

    try:
        d["diagram_markers"] = json.loads(d.pop("diagram_markers_json", "[]") or "[]")
    except Exception:
        d["diagram_markers"] = []

    try:
        d["tags"] = json.loads(d.pop("tags_json", "[]") or "[]")
    except Exception:
        d["tags"] = []

    try:
        d["alternative_answers"] = json.loads(d.pop("alternative_answers_json", "[]") or "[]")
    except Exception:
        d["alternative_answers"] = []

    try:
        d["key_points"] = json.loads(d.pop("key_points_json", "[]") or "[]")
    except Exception:
        d["key_points"] = []

    if "rubric" not in d:
        d["rubric"] = ""

    return d


def row_to_blueprint_dict(row: sqlite3.Row) -> Dict[str, Any]:
    if not row:
        return {}
    d = dict(row)
    for field in ["question_types", "locked_question_ids", "selected_question_ids", "question_snapshots"]:
        try:
            d[field] = json.loads(d.pop(f"{field}_json", "[]") or "[]")
        except Exception:
            d[field] = []

    try:
        d["achieved_distribution"] = json.loads(d.pop("achieved_distribution_json", "{}") or "{}")
    except Exception:
        d["achieved_distribution"] = {}

    d["allow_approximate"] = bool(d.get("allow_approximate", 0))
    return d


class QuestionBankRepository:
    """Repository handling SQLite parameterized data access."""

    @staticmethod
    def create(data: Dict[str, Any]) -> Dict[str, Any]:
        conn = get_db_connection()
        try:
            q_id = data.get("id") or f"bank_{uuid.uuid4().hex[:12]}"
            now_iso = datetime.now(timezone.utc).isoformat()

            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO questions (
                    id, text, question_type, subject, class_level, chapter, topic,
                    difficulty, marks, options_json, correct_answer, explanation,
                    matching_left_json, matching_right_json, matching_answers_json,
                    image_base64, image_caption, diagram_markers_json, tags_json,
                    rubric, alternative_answers_json, key_points_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                q_id,
                data.get("text", "").strip(),
                data.get("question_type", "mcq").strip(),
                data.get("subject", "").strip(),
                data.get("class_level", "").strip(),
                data.get("chapter", "").strip(),
                data.get("topic", "").strip(),
                data.get("difficulty", "medium").strip(),
                float(data.get("marks", 1.0) or 1.0),
                json.dumps(data.get("options", [])),
                data.get("correct_answer", "").strip(),
                data.get("explanation", "").strip(),
                json.dumps(data.get("matching_left", [])),
                json.dumps(data.get("matching_right", [])),
                json.dumps(data.get("matching_answers", {})),
                data.get("image_base64", "") or "",
                data.get("image_caption", "").strip(),
                json.dumps(data.get("diagram_markers", [])),
                json.dumps(data.get("tags", [])),
                data.get("rubric", "").strip(),
                json.dumps(data.get("alternative_answers", [])),
                json.dumps(data.get("key_points", [])),
                now_iso,
                now_iso
            ))
            conn.commit()
            return QuestionBankRepository.get_by_id(q_id)
        finally:
            conn.close()

    @staticmethod
    def get_by_id(q_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM questions WHERE id = ?", (q_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return row_to_question_dict(row)
        finally:
            conn.close()

    @staticmethod
    def get_by_ids(q_ids: List[str]) -> List[Dict[str, Any]]:
        if not q_ids:
            return []
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            placeholders = ",".join("?" for _ in q_ids)
            cursor.execute(f"SELECT * FROM questions WHERE id IN ({placeholders})", q_ids)
            rows = cursor.fetchall()
            return [row_to_question_dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def update(q_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        existing = QuestionBankRepository.get_by_id(q_id)
        if not existing:
            return None

        conn = get_db_connection()
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE questions SET
                    text = ?,
                    question_type = ?,
                    subject = ?,
                    class_level = ?,
                    chapter = ?,
                    topic = ?,
                    difficulty = ?,
                    marks = ?,
                    options_json = ?,
                    correct_answer = ?,
                    explanation = ?,
                    matching_left_json = ?,
                    matching_right_json = ?,
                    matching_answers_json = ?,
                    image_base64 = ?,
                    image_caption = ?,
                    diagram_markers_json = ?,
                    tags_json = ?,
                    rubric = ?,
                    alternative_answers_json = ?,
                    key_points_json = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                data.get("text", existing["text"]).strip(),
                data.get("question_type", existing["question_type"]).strip(),
                data.get("subject", existing.get("subject", "")).strip(),
                data.get("class_level", existing.get("class_level", "")).strip(),
                data.get("chapter", existing.get("chapter", "")).strip(),
                data.get("topic", existing.get("topic", "")).strip(),
                data.get("difficulty", existing.get("difficulty", "medium")).strip(),
                float(data.get("marks", existing.get("marks", 1.0)) or 1.0),
                json.dumps(data.get("options", existing.get("options", []))),
                data.get("correct_answer", existing.get("correct_answer", "")).strip(),
                data.get("explanation", existing.get("explanation", "")).strip(),
                json.dumps(data.get("matching_left", existing.get("matching_left", []))),
                json.dumps(data.get("matching_right", existing.get("matching_right", []))),
                json.dumps(data.get("matching_answers", existing.get("matching_answers", {}))),
                data.get("image_base64", existing.get("image_base64", "")),
                data.get("image_caption", existing.get("image_caption", "")).strip(),
                json.dumps(data.get("diagram_markers", existing.get("diagram_markers", []))),
                json.dumps(data.get("tags", existing.get("tags", []))),
                data.get("rubric", existing.get("rubric", "")).strip(),
                json.dumps(data.get("alternative_answers", existing.get("alternative_answers", []))),
                json.dumps(data.get("key_points", existing.get("key_points", []))),
                now_iso,
                q_id
            ))
            conn.commit()
            return QuestionBankRepository.get_by_id(q_id)
        finally:
            conn.close()

    @staticmethod
    def delete(q_id: str) -> bool:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM questions WHERE id = ?", (q_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def create_blueprint(data: Dict[str, Any]) -> Dict[str, Any]:
        conn = get_db_connection()
        try:
            b_id = data.get("id") or f"bp_{uuid.uuid4().hex[:12]}"
            now_iso = datetime.now(timezone.utc).isoformat()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO blueprints (
                    id, name, subject, class_level, chapter, topic,
                    total_marks, target_question_count, distribution_basis,
                    easy_pct, medium_pct, hard_pct, question_types_json,
                    allow_approximate, section_structure, locked_question_ids_json,
                    selected_question_ids_json, question_snapshots_json,
                    achieved_distribution_json, random_seed, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                b_id,
                data.get("name", "Exam Blueprint").strip(),
                data.get("subject", "").strip(),
                data.get("class_level", "").strip(),
                data.get("chapter", "").strip(),
                data.get("topic", "").strip(),
                float(data.get("total_marks", 100.0) or 100.0),
                int(data["target_question_count"]) if data.get("target_question_count") is not None else None,
                data.get("distribution_basis", "marks").strip(),
                float(data.get("easy_pct", 30.0)),
                float(data.get("medium_pct", 50.0)),
                float(data.get("hard_pct", 20.0)),
                json.dumps(data.get("question_types", [])),
                1 if data.get("allow_approximate") else 0,
                data.get("section_structure", "by_type"),
                json.dumps(data.get("locked_question_ids", [])),
                json.dumps(data.get("selected_question_ids", [])),
                json.dumps(data.get("question_snapshots", [])),
                json.dumps(data.get("achieved_distribution", {})),
                int(data["random_seed"]) if data.get("random_seed") is not None else None,
                now_iso,
                now_iso
            ))
            conn.commit()
            return QuestionBankRepository.get_blueprint(b_id)
        finally:
            conn.close()

    @staticmethod
    def get_blueprint(b_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM blueprints WHERE id = ?", (b_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return row_to_blueprint_dict(row)
        finally:
            conn.close()

    @staticmethod
    def list_blueprints() -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM blueprints ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            return [row_to_blueprint_dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def update_blueprint(b_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        existing = QuestionBankRepository.get_blueprint(b_id)
        if not existing:
            return None
        conn = get_db_connection()
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE blueprints SET
                    name = ?,
                    subject = ?,
                    class_level = ?,
                    chapter = ?,
                    topic = ?,
                    total_marks = ?,
                    target_question_count = ?,
                    distribution_basis = ?,
                    easy_pct = ?,
                    medium_pct = ?,
                    hard_pct = ?,
                    question_types_json = ?,
                    allow_approximate = ?,
                    section_structure = ?,
                    locked_question_ids_json = ?,
                    selected_question_ids_json = ?,
                    question_snapshots_json = ?,
                    achieved_distribution_json = ?,
                    random_seed = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                data.get("name", existing["name"]).strip(),
                data.get("subject", existing["subject"]).strip(),
                data.get("class_level", existing["class_level"]).strip(),
                data.get("chapter", existing["chapter"]).strip(),
                data.get("topic", existing["topic"]).strip(),
                float(data.get("total_marks", existing["total_marks"]) or 100.0),
                int(data["target_question_count"]) if data.get("target_question_count") is not None else existing.get("target_question_count"),
                data.get("distribution_basis", existing["distribution_basis"]).strip(),
                float(data.get("easy_pct", existing["easy_pct"])),
                float(data.get("medium_pct", existing["medium_pct"])),
                float(data.get("hard_pct", existing["hard_pct"])),
                json.dumps(data.get("question_types", existing.get("question_types", []))),
                1 if data.get("allow_approximate", existing.get("allow_approximate", False)) else 0,
                data.get("section_structure", existing.get("section_structure", "by_type")),
                json.dumps(data.get("locked_question_ids", existing.get("locked_question_ids", []))),
                json.dumps(data.get("selected_question_ids", existing.get("selected_question_ids", []))),
                json.dumps(data.get("question_snapshots", existing.get("question_snapshots", []))),
                json.dumps(data.get("achieved_distribution", existing.get("achieved_distribution", {}))),
                int(data["random_seed"]) if data.get("random_seed") is not None else existing.get("random_seed"),
                now_iso,
                b_id
            ))
            conn.commit()
            return QuestionBankRepository.get_blueprint(b_id)
        finally:
            conn.close()

    @staticmethod
    def delete_blueprint(b_id: str) -> bool:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM blueprints WHERE id = ?", (b_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def list_and_search(
        search: Optional[str] = None,
        subject: Optional[str] = None,
        class_level: Optional[str] = None,
        chapter: Optional[str] = None,
        topic: Optional[str] = None,
        difficulty: Optional[str] = None,
        question_type: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Dict[str, Any]], int]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            query_parts = ["1=1"]
            params: List[Any] = []

            if search and search.strip():
                s = f"%{search.strip().lower()}%"
                query_parts.append("(LOWER(text) LIKE ? OR LOWER(topic) LIKE ? OR LOWER(chapter) LIKE ? OR LOWER(subject) LIKE ?)")
                params.extend([s, s, s, s])

            if subject and subject.strip():
                query_parts.append("LOWER(subject) = ?")
                params.append(subject.strip().lower())

            if class_level and class_level.strip():
                query_parts.append("LOWER(class_level) = ?")
                params.append(class_level.strip().lower())

            if chapter and chapter.strip():
                query_parts.append("LOWER(chapter) = ?")
                params.append(chapter.strip().lower())

            if topic and topic.strip():
                query_parts.append("LOWER(topic) = ?")
                params.append(topic.strip().lower())

            if difficulty and difficulty.strip():
                query_parts.append("LOWER(difficulty) = ?")
                params.append(difficulty.strip().lower())

            if question_type and question_type.strip():
                query_parts.append("LOWER(question_type) = ?")
                params.append(question_type.strip().lower())

            if tag and tag.strip():
                t = f"%\"{tag.strip().lower()}\"%"
                query_parts.append("LOWER(tags_json) LIKE ?")
                params.append(t)

            where_clause = " AND ".join(query_parts)

            # Count total
            count_sql = f"SELECT COUNT(*) FROM questions WHERE {where_clause}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()[0]

            # Validate sort columns
            valid_sort_cols = {"created_at", "updated_at", "marks", "difficulty", "text", "subject"}
            col = sort_by if sort_by in valid_sort_cols else "created_at"
            order = "ASC" if sort_order.lower() == "asc" else "DESC"

            data_sql = f"""
                SELECT * FROM questions
                WHERE {where_clause}
                ORDER BY {col} {order}
                LIMIT ? OFFSET ?
            """
            cursor.execute(data_sql, params + [max(1, limit), max(0, offset)])
            rows = cursor.fetchall()
            return [row_to_question_dict(r) for r in rows], total
        finally:
            conn.close()

    @staticmethod
    def get_all_subjects() -> List[str]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT subject FROM questions WHERE subject != '' ORDER BY subject ASC")
            return [r[0] for r in cursor.fetchall()]
        finally:
            conn.close()
