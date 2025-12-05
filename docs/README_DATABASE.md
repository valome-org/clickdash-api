# PostgreSQL Integration Setup

This guide will help you set up PostgreSQL for the Excel Dashboard AI API.

## Prerequisites

1. PostgreSQL installed and running
2. Python dependencies installed

## Installation Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create PostgreSQL Database

```sql
-- Connect to PostgreSQL as superuser
CREATE DATABASE clickdash_db;
CREATE USER clickdash_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE clickdash_db TO clickdash_user;
```

### 3. Configure Environment Variables

Create a `.env` file in the `api` directory:

```env
# Database Configuration
DATABASE_URL=postgresql://clickdash_user:your_password@localhost:5432/clickdash_db

# LLM Configuration
LLM_MODEL=gemini
OPENAI_MODEL=gpt-4-turbo-preview
GEMINI_MODEL=gemini-2.5-flash-preview-05-20
OPENAI_API_KEY=your-openai-api-key-here
GOOGLE_API_KEY=your-google-api-key-here

# Application Configuration
DEBUG=False
```

### 4. Initialize Database

Run the database initialization script:

```bash
cd api
python scripts/init_db.py
```

Or the tables will be created automatically when you start the application.

### 5. Start the Application

```bash
cd api
uvicorn main:app --reload
```

## Database Schema

### Dashboard Table

| Column       | Type     | Description                 |
| ------------ | -------- | --------------------------- |
| id           | Integer  | Primary key                 |
| dashboard_id | String   | Unique dashboard identifier |
| title        | String   | Dashboard title             |
| charts       | JSON     | Chart configurations        |
| insights     | Text     | Dashboard insights          |
| summary      | Text     | Dashboard summary           |
| key_metrics  | JSON     | Key metrics data            |
| status       | String   | Dashboard status            |
| file_url     | String   | Original file URL           |
| created_at   | DateTime | Creation timestamp          |
| updated_at   | DateTime | Update timestamp            |

## API Changes

### New Endpoints

- `GET /api/dashboards` - List all dashboards with pagination
- `GET /api/dashboard/{id}` - Get specific dashboard (updated to use database)
- `POST /api/upload` - Upload and create dashboard (updated to use database)

### Migration from Memory Storage

The application now uses PostgreSQL instead of in-memory storage (`dashboards_storage`). All existing functionality is preserved, but data is now persistent.

## Troubleshooting

### Common Issues

1. **Connection Error**: Check if PostgreSQL is running and credentials are correct
2. **Permission Error**: Ensure the database user has proper permissions
3. **Module Import Error**: Make sure you're in the correct directory when running scripts

### Testing Database Connection

```python
from database.connection import engine

try:
    with engine.connect() as connection:
        print("Database connection successful!")
except Exception as e:
    print(f"Connection failed: {e}")
```

## Production Considerations

1. Use environment variables for all sensitive configuration
2. Set up proper database backups
3. Configure connection pooling for high traffic
4. Use database migrations for schema changes
5. Set up database monitoring and logging
