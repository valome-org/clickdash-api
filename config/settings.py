import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# File size limit (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Database Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres@localhost:5432/clickdash_db"
)

# LLM Configuration
LLM_MODEL = os.getenv("LLM_MODEL", "gemini").lower()

# API Configuration
CORS_ORIGINS = ["http://localhost:3000", "https://your-domain.com"]

# App metadata
APP_TITLE = "Excel Dashboard AI API"
APP_DESCRIPTION = "Convert Excel files to interactive dashboards using AI"
APP_VERSION = "1.0.0"
