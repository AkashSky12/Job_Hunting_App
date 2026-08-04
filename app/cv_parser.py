"""CV parsing: extract text from PDF/DOCX/TXT and structure it.

Uses an LLM when OPENAI_API_KEY is set; otherwise falls back to a
lightweight heuristic parser so the app works with no external services.
"""
from __future__ import annotations

import io
import re

from . import ai

SCHEMA_PROMPT = """Extract the CV into JSON with exactly these keys:
{
  "name": string, "email": string, "phone": string,
  "summary": string,
  "skills": [string],
  "experience": [{"company": string, "role": string, "start": string, "end": string, "highlights": [string]}],
  "education": [{"school": string, "degree": string, "year": string}],
  "target_roles": [string]
}
Return ONLY valid JSON. Use empty strings/arrays for anything missing."""

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")

# A pragmatic starter skill dictionary for the heuristic fallback parser.
_SKILL_HINTS = [
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
    "react", "next.js", "node", "fastapi", "django", "flask", "sql", "postgres",
    "mysql", "mongodb", "redis", "docker", "kubernetes", "aws", "azure", "gcp",
    "terraform", "graphql", "rest", "html", "css", "tailwind", "figma",
    "machine learning", "pytorch", "tensorflow", "llm", "nlp", "pandas",
    "numpy", "spark", "kafka", "ci/cd", "git", "linux", "product management",
    "agile", "scrum", "data analysis", "excel", "power bi", "tableau",
]


def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if name.endswith(".docx"):
        from docx import Document

        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    if name.endswith(".txt") or name.endswith(".md"):
        return data.decode("utf-8", errors="ignore")
    raise ValueError("Unsupported CV format. Use PDF, DOCX, TXT, or MD.")


def _heuristic_parse(text: str) -> dict:
    lower = text.lower()
    email = _EMAIL_RE.search(text)
    phone = _PHONE_RE.search(text)

    # Name guess: first non-empty line without an @ or digit.
    name = ""
    for line in text.splitlines():
        s = line.strip()
        if s and "@" not in s and not any(c.isdigit() for c in s) and len(s) < 60:
            name = s
            break

    skills = sorted({s for s in _SKILL_HINTS if s in lower})

    # Summary: first meaningful paragraph.
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    summary = ""
    for p in paragraphs:
        if len(p) > 60:
            summary = " ".join(p.split())[:400]
            break

    return {
        "name": name,
        "email": email.group(0) if email else "",
        "phone": phone.group(0).strip() if phone else "",
        "summary": summary,
        "skills": skills,
        "experience": [],
        "education": [],
        "target_roles": [],
    }


def parse_cv(text: str) -> dict:
    """Return structured CV data. Prefers LLM, falls back to heuristics."""
    if ai.settings.ai_enabled:
        result = ai.chat_json(SCHEMA_PROMPT, text[:12000])
        if result:
            # Ensure required keys exist.
            for key in ("name", "email", "phone", "summary"):
                result.setdefault(key, "")
            for key in ("skills", "experience", "education", "target_roles"):
                result.setdefault(key, [])
            return result
    return _heuristic_parse(text)


def flatten_profile_text(parsed: dict) -> str:
    """Build a single text blob used for embedding / TF-IDF matching."""
    parts: list[str] = [parsed.get("summary", "")]
    parts.extend(parsed.get("skills", []))
    for exp in parsed.get("experience", []):
        parts.append(f"{exp.get('role', '')} {exp.get('company', '')}")
        parts.extend(exp.get("highlights", []))
    parts.extend(parsed.get("target_roles", []))
    return " ".join(p for p in parts if p).strip()
