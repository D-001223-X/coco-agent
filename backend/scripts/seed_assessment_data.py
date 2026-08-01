"""Seed assessment question bank into coco.db (T-002).

Reads ``assessment_data.json`` (46 questions: listening 20 + speaking 15 +
reading 11) and writes them into the ``assessment_questions`` table.
"""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "coco.db"
JSON_PATH = Path(__file__).resolve().parent / "assessment_data.json"


def seed() -> int:
    """Seed the question bank; returns number of inserted questions."""
    if not JSON_PATH.exists():
        raise FileNotFoundError(f"assessment_data.json 不存在: {JSON_PATH}")

    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assessment_questions (
            id TEXT PRIMARY KEY,
            section TEXT NOT NULL,
            section_title TEXT NOT NULL,
            section_description TEXT,
            type TEXT NOT NULL,
            text TEXT NOT NULL,
            options_json TEXT,
            correct_answer TEXT
        )
    """)
    cursor.execute("DELETE FROM assessment_questions")

    count = 0
    for sec in data["sections"]:
        for q in sec["questions"]:
            cursor.execute(
                "INSERT INTO assessment_questions VALUES (?,?,?,?,?,?,?,?)",
                (
                    q["id"],
                    sec["section"],
                    sec["title"],
                    sec.get("description", ""),
                    q["type"],
                    q["text"],
                    json.dumps(q.get("options", []), ensure_ascii=False),
                    q.get("correct_answer"),
                ),
            )
            count += 1
    conn.commit()
    conn.close()
    print(f"✅ 导入 {count} 题成功")
    return count


if __name__ == "__main__":
    seed()
