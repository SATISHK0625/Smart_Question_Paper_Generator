import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
TEMP_BASE_DIR = (BACKEND_DIR / "temp_files").resolve()
TEMP_BASE_DIR.mkdir(parents=True, exist_ok=True)

REFERENCES_DIR = TEMP_BASE_DIR / "references"
REFERENCES_DIR.mkdir(parents=True, exist_ok=True)

def get_reference_path(reference_id: Optional[str] = None, reference_pdf_path: Optional[str] = None) -> Optional[Path]:
    """
    Safely resolves the path to an uploaded reference PDF.
    Checks reference_id, reference_pdf_path, and latest_reference.pdf.
    """
    if reference_id:
        p = REFERENCES_DIR / f"{reference_id}.pdf"
        if p.exists() and p.is_file() and p.stat().st_size > 100:
            return p
    if reference_pdf_path:
        p = Path(reference_pdf_path)
        if p.exists() and p.is_file() and p.stat().st_size > 100:
            return p
    latest = REFERENCES_DIR / "latest_reference.pdf"
    if latest.exists() and latest.is_file() and latest.stat().st_size > 100:
        return latest
    return None

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024 # 15 MB

ALLOWED_PDF_EXTENSIONS = {".pdf"}
ALLOWED_QUESTION_EXTENSIONS = {".txt", ".docx"}

def validate_file_size(file: UploadFile, max_size_bytes: int = MAX_FILE_SIZE_BYTES) -> None:
    # Check content-length header if provided
    content_length = file.headers.get("content-length")
    if content_length and int(content_length) > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size of {max_size_bytes // (1024*1024)}MB"
        )

def sanitize_filename(filename: Optional[str]) -> str:
    if not filename:
        return "unnamed_file"
    # Basic sanitization, remove directory paths
    clean = Path(filename).name
    # Keep only safe characters
    clean = "".join(c for c in clean if c.isalnum() or c in "._- ")
    return clean.strip() or "unnamed_file"

def save_upload_to_temp(file: UploadFile, allowed_extensions: set) -> Tuple[Path, str]:
    validate_file_size(file)
    original_name = sanitize_filename(file.filename)
    ext = Path(original_name).suffix.lower()
    
    if ext not in allowed_extensions:
        allowed_str = ", ".join(allowed_extensions)
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed formats: {allowed_str}"
        )
    
    unique_id = uuid.uuid4().hex
    temp_path = TEMP_BASE_DIR / f"{unique_id}_{original_name}"
    
    bytes_written = 0
    with open(temp_path, "wb") as buffer:
        while chunk := file.file.read(1024 * 64):
            bytes_written += len(chunk)
            if bytes_written > MAX_FILE_SIZE_BYTES:
                buffer.close()
                temp_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"Uploaded file exceeds {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB limit."
                )
            buffer.write(chunk)
            
    return temp_path, original_name

def cleanup_file(path: Optional[Path]) -> None:
    if path and path.exists():
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass

def cleanup_old_temp_files(max_age_seconds: int = 3600) -> None:
    import time
    now = time.time()
    try:
        for item in TEMP_BASE_DIR.glob("*"):
            if item.is_file():
                if now - item.stat().st_mtime > max_age_seconds:
                    item.unlink(missing_ok=True)
    except Exception:
        pass
