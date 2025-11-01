# backend_api — Excel AI Modifier (FastAPI)

Lightweight backend implementing a Clean Architecture (controllers, services, dto, utils). It exposes:

- GET `/sample-data` — returns sample rules JSON
- POST `/export` — accepts multipart form (`file`, `sheet`) and returns modified `.xlsx`

Quick start (Windows PowerShell):

```powershell
cd backend_api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Notes:
- Put your OpenAI key in `.env` as `OPENAI_API_KEY` to enable real model calls. If no key is present, the backend uses a deterministic mock implementation.
- CORS is enabled for http://localhost:3000 to work with the frontend.

Logging and debugging
- The backend configures logging at startup. General logs are written to `backend_api/data/logs/app.log` (rotating files).
- When the LLM call returns malformed output that cannot be parsed as CSV, the raw text or prompt and error are saved for debugging under `backend_api/data/llm_debug/` as `llm_raw_<UTC-timestamp>.txt`.

Environment variables
- `OPENAI_API_KEY`: optional, if provided the backend will attempt to call the OpenAI API. If omitted, a deterministic fallback is used.

Run examples (PowerShell):

```powershell
cd backend_api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
