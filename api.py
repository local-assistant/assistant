# api.py
from fastapi import FastAPI
from pydantic import BaseModel
from task_store import init_db, add_task, list_tasks, get_task, update_status, create_task_record
import subprocess
from fastapi import Query
import re


app = FastAPI()
init_db()


class TaskRequest(BaseModel):
    description: str


@app.post("/tasks")
def create_task_api(req: TaskRequest):
    task_id = add_task(req.description)
    return {"id": task_id, "status": "created"}


@app.get("/tasks")
def get_tasks():
    rows = list_tasks()
    return [
        {
            "id": row[0],
            "description": row[1],
            "status": row[2],
        }
        for row in rows
    ]

@app.get("/tasks/{task_id}/logs")
def get_task_logs(task_id: int, lines: int = Query(200, ge=50, le=2000)):
    """
    Return recent logs for a task by filtering journald output.
    """
    cmd = [
        "journalctl",
        "-u", "assistant-worker.service",
        "-n", str(lines),
        "--no-pager",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    tag = f"[TASK {task_id}]"
    logs = [line for line in result.stdout.splitlines() if tag in line]

    return {
        "task_id": task_id,
        "logs": logs,
    }

@app.get("/tasks/{task_id}/outputs")
def get_task_outputs(task_id: int):
    """
    Extract output file paths from task logs.
    """
    cmd = [
        "journalctl",
        "-u", "assistant-worker.service",
        "--no-pager",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    tag = f"[TASK {task_id}]"
    output_files = set()

    # Simple but reliable redirection detection
    redir_pattern = re.compile(r'>\s*(output/[\w\-.\/]+)')

    for line in result.stdout.splitlines():
        if tag not in line:
            continue

        match = redir_pattern.search(line)
        if match:
            output_files.add(match.group(1))

    return {
        "task_id": task_id,
        "outputs": sorted(output_files),
    }


@app.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: int):
    update_status(task_id, "cancelled")
    return {"task_id": task_id, "status": "cancelled"}


@app.post("/tasks/{task_id}/retry")
def retry_task(task_id: int):
    original = get_task(task_id)

    if not original:
        raise HTTPException(status_code=404, detail="Task not found")

    _, description, _ = original

    new_task_id = create_task_record(description, parent_id=task_id)

    return {
        "original_task_id": task_id,
        "new_task_id": new_task_id,
        "status": "pending",
    }




