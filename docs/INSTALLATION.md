# ClickDash API Installation Guide

This guide will help you set up the API component of ClickDash, a FastAPI-based backend service.

## Prerequisites

- Python 3.8 or higher
- PostgreSQL database
- pip (Python package manager)

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/valome-org/clickdash-api.git
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

### 3. Activate the Virtual Environment

- On Linux/macOS:
  ```bash
  source .venv/bin/activate
  ```
- On Windows:
  ```bash
  .venv\Scripts\activate
  ```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file in the API root directory with the following variables:

```
# Database Configuration
# LLM Model Configuration
# Choose which model to use: "openai" or "gemini"
LLM_MODEL=gemini

# OpenAI Configuration
# Get your API key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=your-openai-api-key-here

# Google Gemini Configuration
# Get your API key from: https://makersuite.google.com/app/apikey
GOOGLE_API_KEY=your-google-api-key-here

# Application Settings
ENVIRONMENT=development
DEBUG=True

# File Upload Settings
MAX_FILE_SIZE=10485760
UPLOAD_DIR=uploads
```

Replace the placeholder values with your actual configuration.

### 6. Initialize Database

The application will create the necessary tables automatically when started, but you can run database migrations manually:

```bash
alembic upgrade head
```

### 7. Start the API Server

For development:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

For production:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 8. Verify Installation

Visit `http://localhost:8000/health` to verify that the API is running correctly. You should see a JSON response with status "healthy".

## API Documentation

Once the server is running, you can access the automatically generated API documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Troubleshooting

If you encounter issues:

1. Make sure your PostgreSQL server is running
2. Check that your `.env` file contains the correct database connection string
3. Ensure all dependencies are installed correctly
4. Verify that the port 8000 is not in use by another application

For more detailed information, refer to the project's main documentation.
