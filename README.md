## ClickDash API

FastAPI backend for converting uploaded Excel files into interactive dashboards with AI assistance.

### Prerequisites

- Python 3.13 (recommended to use a virtual environment)
- PostgreSQL 14+ running and accessible
- A PostgreSQL database created (e.g., `clickdash_db`)

### Quick Start

```bash
# 1) Clone and enter the project
git clone <your-repo-url> && cd clickdash-api

# 2) Create and activate a virtual environment
python3.13 -m venv .venv
source .venv/bin/activate

# 3) Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4) Set environment variables (see Environment section)
export DATABASE_URL="postgresql+psycopg://postgres@localhost:5432/clickdash_db"
export SECRET_KEY="dev-secret"  # change in production

# 5) Run database migrations
alembic upgrade head

# 6) Start the API
uvicorn main:app --reload
```

API will start at `http://127.0.0.1:8000` with docs at `http://127.0.0.1:8000/docs`.

### Environment

Configuration is loaded from environment variables in `config/settings.py`. Common variables:

- `DATABASE_URL` (required): PostgreSQL URL.
  - Use the psycopg3 driver scheme: `postgresql+psycopg://user:pass@host:5432/dbname`
  - Heroku-style `postgres://...` is auto-normalized to `postgresql+psycopg://...`.
- `SECRET_KEY` (required): JWT signing key.
- `ACCESS_TOKEN_EXPIRE_MINUTES` (default: `30`): Access token lifetime.
- `UPLOAD_DIR` (default: `uploads`): Directory to store uploaded files (created if missing).
- `CORS_ORIGINS` (default: `http://localhost:3000`): Comma-separated list for CORS.
- `LLM_MODEL` (default: `gemini`): LLM provider selection.
- `OPENAI_MODEL` (default: `gpt-4-turbo-preview`): OpenAI model ID to use.
- `GEMINI_MODEL` (default: `gemini-2.5-flash-preview-05-20`): Gemini model ID to use.
- `APP_TITLE`, `APP_DESCRIPTION`, `APP_VERSION`: OpenAPI metadata.

Tip: You can place these in a local `.env` file and they will be loaded automatically.

Example `.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres@localhost:5432/clickdash_db
SECRET_KEY=dev-secret
ACCESS_TOKEN_EXPIRE_MINUTES=30
UPLOAD_DIR=uploads
CORS_ORIGINS=http://localhost:3000
LLM_MODEL=gemini
OPENAI_MODEL=gpt-4-turbo-preview
GEMINI_MODEL=gemini-2.5-flash-preview-05-20
APP_TITLE=Excel Dashboard AI API
APP_DESCRIPTION=Convert Excel files to interactive dashboards using AI
APP_VERSION=1.0.0
```

### Database Migrations (Alembic)

Alembic is already configured under `alembic/` and uses your `DATABASE_URL`.

- Show current revision:

```bash
alembic current
```

- Upgrade to latest schema:

```bash
alembic upgrade head
```

- Create a new migration after changing models in `database/models.py`:

```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

- Downgrade one migration:

```bash
alembic downgrade -1
```

### Seeding / Initializing Data (optional)

There is a helper script that can be customized for initial data:

```bash
python scripts/init_db.py
```

### Running the API

```bash
uvicorn main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for interactive Swagger UI.

### Project Structure

```
config/            # Settings and environment
database/          # Engine, session, and models
routers/           # FastAPI routers
services/          # Business logic
utils/             # Helpers
alembic/           # Alembic migrations
uploads/           # Uploaded files (created automatically)
```

### Troubleshooting

- psycopg/driver errors:
  - Ensure `psycopg[binary]>=3.2.0` is installed (already in `requirements.txt`).
  - Confirm your URL uses psycopg3 scheme: `postgresql+psycopg://...`.
  - We normalize `postgres://` to `postgresql+psycopg://` automatically.
- Alembic cannot connect:
  - Verify `DATABASE_URL` is exported/loaded and the database exists and is reachable.
  - Check that Postgres is running and credentials are correct.
- Permission/port issues on 8000:
  - Set a different host/port: `uvicorn main:app --host 0.0.0.0 --port 8080`.

### Useful Commands

```bash
# Install deps
pip install -r requirements.txt

# Lint (if you add a linter), run tests (if you add pytest), etc.

# Run dev server
uvicorn main:app --reload

# Migrations
alembic revision --autogenerate -m "msg"
alembic upgrade head
alembic downgrade -1
```
