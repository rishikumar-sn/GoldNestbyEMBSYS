# Backend setup

Use Python 3.11 or 3.12. From `backend/`, create a virtual environment and install the API, developer, and AI requirements.

```powershell
py -3.12 -m venv ..\.venv
..\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt -r requirements-ai.txt
Copy-Item .env.example .env
```

Set a unique `JWT_SECRET` in `backend/.env`, download/verify models as described in [MODEL_SETUP.md](MODEL_SETUP.md), then apply migrations:

```powershell
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m app.cli create-user <username>
```

Start the HTTPS API and worker in separate terminals after generating `certs/server.crt` and `certs/server.key`:

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8443 --ssl-keyfile certs/server.key --ssl-certfile certs/server.crt
..\.venv\Scripts\python.exe -m app.workers.run
```

`GET /api/v1/health` confirms the API process; `/api/v1/ready` also requires the database and worker. Keep the process working directory as `backend/` so the configured relative paths resolve there.
