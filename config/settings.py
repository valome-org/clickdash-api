import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(exist_ok=True)

# File size limit (10MB)
MAX_FILE_SIZE = os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024)

# Database Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres@localhost:5432/clickdash_db"
)

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30)

# LLM Configuration
LLM_MODEL = os.getenv("LLM_MODEL", "gemini").lower()

# API Configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

# App metadata
APP_TITLE = os.getenv("APP_TITLE", "Excel Dashboard AI API")
APP_DESCRIPTION = os.getenv("APP_DESCRIPTION", "Convert Excel files to interactive dashboards using AI")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
