import shutil
import uuid
from pathlib import Path

from config.settings import MAX_FILE_SIZE, UPLOAD_DIR
from fastapi import HTTPException, UploadFile


def validate_excel_file(file: UploadFile) -> None:
    """Validate uploaded Excel file"""
    # Check file extension
    if not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Only Excel files (.xlsx, .xls) are allowed"
        )

    # Check content type
    allowed_types = [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel'
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an Excel file."
        )


def save_uploaded_file(file: UploadFile) -> Path:
    """Save uploaded file to disk with proper error handling"""
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename or "file.xlsx").suffix
    filename = f"{file_id}_{file.filename}"
    file_path = UPLOAD_DIR / filename

    try:
        # Save file in chunks to handle large files
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Verify file size
        if file_path.stat().st_size > MAX_FILE_SIZE:
            file_path.unlink()  # Delete the file
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
            )

        return file_path

    except Exception as e:
        # Clean up on error
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )
