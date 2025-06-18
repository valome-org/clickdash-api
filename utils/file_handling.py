import shutil
import uuid
from pathlib import Path

import pandas as pd
import openpyxl
from config.settings import MAX_FILE_SIZE, UPLOAD_DIR
from fastapi import HTTPException, UploadFile


def validate_excel_file(file: UploadFile) -> None:
    """Comprehensive validation for uploaded Excel files"""

    # Check if file exists and has content
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided"
        )

    # Check file extension
    allowed_extensions = ('.xlsx', '.xls', '.csv')
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format. Only {', '.join(allowed_extensions)} files are supported"
        )

    # Check content type
    allowed_types = [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
        'application/vnd.ms-excel',  # .xls
        'text/csv',  # .csv
        'application/csv',  # .csv alternative
        'application/octet-stream'  # Sometimes browsers send this for Excel files
    ]

    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload a valid Excel or CSV file."
        )

    # Check file size before processing
    if hasattr(file.file, 'seek') and hasattr(file.file, 'tell'):
        # Get current position
        current_pos = file.file.tell()
        # Seek to end to get size
        file.file.seek(0, 2)
        file_size = file.file.tell()
        # Reset to original position
        file.file.seek(current_pos)

        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="File is empty. Please upload a file with data."
            )

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size allowed is {MAX_FILE_SIZE // (1024*1024)}MB, but file is {file_size // (1024*1024)}MB"
            )


def validate_file_content(file_path: Path) -> None:
    """Validate the actual content of the uploaded file"""
    try:
        # Determine file type and try to read it
        file_extension = file_path.suffix.lower()

        if file_extension == '.csv':
            # Try to read CSV
            df = pd.read_csv(file_path)
        elif file_extension in ['.xlsx', '.xls']:
            # First try with openpyxl to catch corruption early
            if file_extension == '.xlsx':
                try:
                    workbook = openpyxl.load_workbook(file_path, read_only=True)
                    sheet_names = workbook.sheetnames
                    workbook.close()

                    if not sheet_names:
                        raise HTTPException(
                            status_code=400,
                            detail="Excel file contains no worksheets"
                        )
                except openpyxl.utils.exceptions.InvalidFileException:
                    raise HTTPException(
                        status_code=400,
                        detail="File appears to be corrupted or is not a valid Excel file"
                    )
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unable to read Excel file: {str(e)}"
                    )

            # Now try to read with pandas
            try:
                df = pd.read_excel(file_path)
            except Exception as e:
                if "corrupted" in str(e).lower() or "invalid" in str(e).lower():
                    raise HTTPException(
                        status_code=400,
                        detail="File appears to be corrupted. Please try uploading again or use a different file."
                    )
                raise HTTPException(
                    status_code=400,
                    detail=f"Unable to process Excel file: {str(e)}"
                )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file extension: {file_extension}"
            )

        # Check if dataframe is empty
        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="File contains no data. Please upload a file with data rows."
            )

        # Check if dataframe has minimal structure
        if len(df.columns) == 0:
            raise HTTPException(
                status_code=400,
                detail="File has no columns. Please ensure your file has proper headers."
            )

        # Check for reasonable data size (at least some rows and columns)
        if len(df) < 1:
            raise HTTPException(
                status_code=400,
                detail="File must contain at least one data row."
            )

        # Warn if file has too many columns (might indicate parsing issues)
        if len(df.columns) > 100:
            # This is a warning, not an error - large datasets might be legitimate
            pass

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error validating file content: {str(e)}"
        )


def save_uploaded_file(file: UploadFile) -> Path:
    """Save uploaded file to disk with comprehensive error handling"""
    # Generate unique filename
    file_id = str(uuid.uuid4())
    filename = f"{file_id}_{file.filename}"
    file_path = UPLOAD_DIR / filename

    try:
        # Ensure upload directory exists
        UPLOAD_DIR.mkdir(exist_ok=True)

        # Save file in chunks to handle large files efficiently
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Verify file was written correctly
        if not file_path.exists():
            raise HTTPException(
                status_code=500,
                detail="Failed to save file to disk"
            )

        # Double-check file size after saving
        actual_size = file_path.stat().st_size
        if actual_size == 0:
            file_path.unlink()  # Delete empty file
            raise HTTPException(
                status_code=400,
                detail="File was saved but appears to be empty"
            )

        if actual_size > MAX_FILE_SIZE:
            file_path.unlink()  # Delete oversized file
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum size limit of {MAX_FILE_SIZE // (1024*1024)}MB"
            )

        # Validate the actual file content
        validate_file_content(file_path)

        return file_path

    except HTTPException:
        # Clean up on validation errors
        if file_path.exists():
            try:
                file_path.unlink()
            except:
                pass  # Best effort cleanup
        raise
    except Exception as e:
        # Clean up on any other error
        if file_path.exists():
            try:
                file_path.unlink()
            except:
                pass  # Best effort cleanup

        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )
