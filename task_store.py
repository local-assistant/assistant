# task_store.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "tasks.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                parent_id INTEGER
            )
            """
        )


def add_task(description: str):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (description, status) VALUES (?, 'pending')",
            (description,),
        )
        return cur.lastrowid


def list_tasks():
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, description, status, parent_id FROM tasks ORDER BY id DESC"
        ).fetchall()


def update_status(task_id: int, status: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE tasks SET status = ? WHERE id = ?",
            (status, task_id),
        )

def create_task_record(description: str, parent_id: int | None = None) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO tasks (description, status, parent_id)
            VALUES (?, 'pending', ?)
            """,
            (description, parent_id),
        )
        conn.commit()
        return cur.lastrowid
    
def get_task(task_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, description, status FROM tasks WHERE id = ?",
            (task_id,),
        )
        return cur.fetchone()

