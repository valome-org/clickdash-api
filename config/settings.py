import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(exist_ok=True)

# File size limit (10MB)
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))

def _normalize_db_url(url: str) -> str:
    """Ensure SQLAlchemy uses psycopg (psycopg3) driver for PostgreSQL.

    - Convert deprecated "postgres://" to "postgresql://"
    - If no explicit driver is provided, force "+psycopg"
    - Migrate old "+psycopg2" to "+psycopg"
    """
    if not url:
        return url

    # Heroku-style URLs use the deprecated postgres:// scheme
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    # If no driver specified, prefer psycopg (psycopg3)
    if url.startswith("postgresql://") and "+" not in url.split("://", 1)[1].split("@", 1)[0]:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    # Upgrade explicit psycopg2 to psycopg
    if url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)

    return url

# Database Configuration
DATABASE_URL = _normalize_db_url(os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres@localhost:5432/clickdash_db"
))

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# LLM Configuration
# Provider selector (gemini|openai)
LLM_MODEL = os.getenv("LLM_MODEL", "gemini").lower()
# Model identifiers are configurable so deployments can swap models without code changes
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-05-20")

# API Configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

# App metadata
APP_TITLE = os.getenv("APP_TITLE", "Excel Dashboard AI API")
APP_DESCRIPTION = os.getenv("APP_DESCRIPTION", "Convert Excel files to interactive dashboards using AI")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
