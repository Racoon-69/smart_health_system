"""PDF/TXT extraction and educational keyword analysis."""

from pathlib import Path

from pypdf import PdfReader

from .health_rules import analyze_text


def extract_report(path: Path) -> str:
    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def analyze_report(text: str) -> dict:
    return analyze_text(text)
