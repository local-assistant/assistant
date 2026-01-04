# Assistant ✅

**Purpose**

A small autonomous execution assistant that accepts human-readable task descriptions, uses an LLM (via Ollama) to translate them into a sequence of shell commands, executes those commands in per-task working directories, and stores results and logs. Intended as a simple prototype for autonomous task execution and experimentation.

---

## Quick start 🔧

- Start the worker (polling loop + LLM calls):
  - `python worker.py`
- Start the API (FastAPI):
  - `uvicorn api:app --reload` (or run via your preferred ASGI server)
- Tasks DB: `tasks.db` (SQLite). The repository will initialize it automatically on startup.

> Note: The worker expects an Ollama endpoint (configurable in `worker.py`) and will execute shell commands returned by the model.

---

## Top-level structure 📁

- `api.py` — FastAPI app exposing endpoints to create/list tasks, get task logs, examine outputs, cancel or retry tasks.
- `worker.py` — Main polling worker. Polls `tasks` DB for pending tasks, requests commands from the LLM, executes them in an isolated directory (`tasks/task-<id>`), and writes status updates to the DB.
- `task_store.py` — Thin SQLite wrapper for task CRUD (init DB, add/list/update tasks, create task records).
- `tasks.db` / `tasks.db.bak` — SQLite database storing task rows (id, description, status, parent_id).
- `tasks/` — Working directories for executed tasks (`task-<id>/`). Some example task folders are present.
- `output/` — Misc debug / test output and example files (used during development and tests).
- `venv/` — Local Python virtual environment (if present).

---

## How a task flows ✨

1. A client posts a task description to `POST /tasks` (`api.py`) → `task_store.add_task()` creates a DB row with status `pending`.
2. `worker.py` polls the DB and sets a `pending` task to `running`.
3. Worker calls `ask_ollama()` (Ollama API) sending a `SYSTEM_PROMPT` that requires the model to emit JSON: `{ "commands": ["...", ...] }`.
4. Worker executes each shell command in the task's directory `tasks/task-<id>` (via `subprocess.run(..., shell=True, cwd=task_dir)`) and logs progress.
5. Worker marks the task `done`, `failed`, or `cancelled` in the DB.
6. Logs are written to stdout and are intended to be captured by systemd journal (`assistant-worker.service`) — `api.py` can query the logs with `journalctl`.

---

## Important endpoints (API) 🧭

- `POST /tasks` — Create a new task (JSON body: `{ "description": "..." }`).
- `GET /tasks` — List tasks and statuses.
- `GET /tasks/{task_id}/logs?lines=200` — Get recent logs for a task (filters journalctl output by `[TASK {id}]`).
- `GET /tasks/{task_id}/outputs` — Heuristically extracts output file paths from logs (pattern `> output/...`).
- `POST /tasks/{task_id}/cancel` — Mark a task `cancelled` in DB.
- `POST /tasks/{task_id}/retry` — Create a new pending task copying the original description (tracks `parent_id`).

---

## Developer notes & gotchas ⚠️

- The worker trusts the LLM to return only a JSON object containing shell commands. The LLM output is parsed with `json.loads(...)` and executed as shells commands without sanitization — **this is a security risk**. Do not run this against untrusted models or data.
- Commands are executed with `shell=True` and may have side effects. Prefer running in containers or sandboxes for experiments.
- Logs use the `[TASK {id}]` prefix to make parsing easy. The API depends on those tags when extracting logs/outputs.
- Task output files are simply any files created in `tasks/task-<id>`; the `GET /tasks/{task_id}/outputs` endpoint looks for redirection patterns in logs (e.g., `> output/...`).
- Ollama config in `worker.py`:
  - `OLLAMA_URL` and `MODEL` are top-level constants — change them for your environment.

---

## Recommended contributions / next steps 💡

- Add a test harness that runs the worker in a sandboxed environment (e.g., temporary container) to validate command execution safely.
- Improve LLM response validation (schema checks, whitelists) before executing shell commands.
- Add a full-featured CLI for creating/retrying/canceling tasks.
- Add unit tests for `task_store.py` and integration tests for API endpoints.

---

## Contact / context

If you need context for why certain design choices were made (for example, reading logs from `journalctl` instead of a file), check the logging usage in `worker.py` and the log parsing logic in `api.py`.

---


