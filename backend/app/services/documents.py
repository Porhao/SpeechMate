"""Plain text from uploaded documents (resumes, decks), best effort."""

import re
import subprocess
import zipfile
from io import BytesIO

from app.schemas.live import MAX_RESUME_CHARS


def pdf_text(data: bytes) -> str:
    """pdftotext's layout-preserving text (pages separated by form feeds). Raises ValueError."""
    try:
        return subprocess.run(["pdftotext", "-layout", "-", "-"], input=data, capture_output=True,
                              timeout=120, check=True).stdout.decode("utf-8", "replace")
    except (OSError, subprocess.SubprocessError) as e:
        raise ValueError(f"Couldn't read the PDF ({e})") from e


def tidy_lines(text: str) -> str:
    """One line per text line, the column padding collapsed, blank lines dropped."""
    return "\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip())


def extract_resume_text(data: bytes, filename: str) -> str:
    """Plain text from a PDF, DOCX or TXT resume (best effort, truncated)."""
    name = filename.lower()
    text = ""
    if name.endswith(".pdf"):
        text = pdf_text(data)
    elif name.endswith(".docx"):
        try:
            with zipfile.ZipFile(BytesIO(data)) as z:
                xml = z.read("word/document.xml").decode("utf-8", "replace")
        except (zipfile.BadZipFile, KeyError) as e:
            raise ValueError("That doesn't look like a valid .docx file") from e
        xml = re.sub(r"</w:p>", "\n", xml)
        text = re.sub(r"<[^>]+>", "", xml)
    elif name.endswith((".txt", ".md")):
        text = data.decode("utf-8", "replace")
    else:
        raise ValueError("Upload the resume as PDF, DOCX or TXT")
    text = tidy_lines(text)
    if not text:
        raise ValueError("No text could be read from the resume (is it a scanned image?)")
    return text[:MAX_RESUME_CHARS]
