from pathlib import Path
from typing import Optional
from docx import Document
from fastapi import HTTPException

def extract_text_from_txt(path: Path) -> str:
    """Extracts text from TXT file with encoding fallbacks."""
    for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="Could not decode the TXT file with standard text encodings.")

def extract_text_from_docx(path: Path) -> str:
    """Extracts text from DOCX preserving paragraphs and table contents."""
    try:
        doc = Document(str(path))
        lines = []
        for paragraph in doc.paragraphs:
            text = paragraph.text
            if text:
                lines.append(text)
            else:
                # keep blank lines for spacing
                lines.append("")

        # Also extract table text if questions were in tables
        for table in doc.tables:
            for row in table.rows:
                row_text = "\t".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    lines.append(row_text)

        return "\n".join(lines)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read DOCX file: {str(e)}")

def extract_text_from_file(path: Path, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".txt":
        return extract_text_from_txt(path)
    elif ext == ".docx":
        return extract_text_from_docx(path)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format '{ext}'. Only .txt and .docx are supported.")
