# worker.py
import time
import json
import subprocess
import requests
from task_store import init_db, list_tasks, update_status
import logging
import sys
from pathlib import Path


OLLAMA_URL = "http://192.168.122.1:11434/api/chat"
MODEL = "llama3.1:8b"
POLL_INTERVAL = 2
BASE_TASK_DIR = Path("/home/nishant/assistant/tasks")
BASE_TASK_DIR.mkdir(exist_ok=True)


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

log = logging.getLogger("assistant-worker")


SYSTEM_PROMPT = """
You are an autonomous execution agent.

Given a task description, you MUST return a JSON object
with this exact schema:

{
  "commands": [
    "shell command 1",
    "shell command 2"
  ]
}

Execution model:
- Each task runs in its own isolated working directory
- Any files you create will automatically be saved as task results
- You do NOT need to specify output directories

Rules:
- ONLY shell commands
- Use relative paths only
- Do NOT reference absolute paths
- Do NOT assume any pre-existing files
- Commands must be safe and deterministic
- Do NOT include explanations
- Do NOT include markdown
"""



def ask_ollama(task_description: str) -> list[str]:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task_description},
        ],
        "stream": False,
    }

    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()

    content = resp.json()["message"]["content"]
    plan = json.loads(content)

    return plan["commands"]

def is_cancelled(task_id: int) -> bool:
    tasks = list_tasks()
    for tid, _, status in tasks:
        if tid == task_id:
            return status == "cancelled"
    return False

def get_task_status(task_id: int) -> str | None:
    tasks = list_tasks()
    for tid, _, status in tasks:
        if tid == task_id:
            return status
    return None



def execute_task(task_id: int, description: str):
    task_dir = BASE_TASK_DIR / f"task-{task_id}"
    task_dir.mkdir(parents=True, exist_ok=True)

    log.info(f"[TASK {task_id}] START {description}")
    log.info(f"[TASK {task_id}] DIR {task_dir}")

    try:
        commands = ask_ollama(description)

        for cmd in commands:
            if is_cancelled(task_id):
                log.info(f"[TASK {task_id}] CANCELLED before executing next command")
                return

            log.info(f"[TASK {task_id}] EXEC {cmd}")

            result = subprocess.run(
                cmd,
                shell=True,
                cwd=task_dir,
                capture_output=True,
                text=True,
            )

            if result.stdout:
                log.info(f"[TASK {task_id}] STDOUT:\n{result.stdout}")

            if result.stderr:
                log.info(f"[TASK {task_id}] STDERR:\n{result.stderr}")

            if result.returncode != 0:
                raise RuntimeError(f"Command failed: {cmd}")


        final_status = get_task_status(task_id)

        log.info(f"[TASK {task_id}] FINAL STATUS CHECK = {get_task_status(task_id)}")

        if final_status == "cancelled":
            log.info(f"[TASK {task_id}] NOT marking done because task was cancelled")
        else:
            log.info(f"[TASK {task_id}] DONE")
            update_status(task_id, "done")


    except Exception as e:
        if is_cancelled(task_id):
            log.info(f"[TASK {task_id}] CANCELLED during execution")
            update_status(task_id, "cancelled")
        else:
            log.info(f"[TASK {task_id}] FAILED: {e}")
            update_status(task_id, "failed")





def main():
    init_db()
    log.info("Autonomous assistant worker started (LLM-enabled).")

    while True:
        tasks = list_tasks()
        for task_id, description, status, parent_id in tasks:
            if status == "pending":
                update_status(task_id, "running")
                execute_task(task_id, description)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
