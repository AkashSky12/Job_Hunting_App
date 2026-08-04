"""AI matching engine.

Two-stage design mirroring the blueprint:
  1. Recall/scoring — OpenAI embeddings cosine similarity when available,
     otherwise a dependency-free TF-IDF cosine over profile vs. job text.
  2. Reasoning — a short human-readable explanation (LLM if available,
     otherwise a heuristic based on overlapping skills/keywords).
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter

from . import ai
from .db import get_conn, row_to_dict

_TOKEN_RE = re.compile(r"[a-z0-9+#.]+")
_STOP = {
    "the", "and", "for", "with", "you", "your", "our", "are", "will", "job",
    "role", "team", "work", "have", "this", "that", "from", "into", "who",
    "all", "can", "not", "but", "was", "has", "a", "an", "of", "to", "in",
    "on", "as", "at", "is", "we", "be", "or", "by", "it", "us",
}


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP and len(t) > 1]


def _tfidf_vectors(profile_text: str, docs: list[str]) -> tuple[dict, list[dict], list[dict]]:
    corpus = [profile_text] + docs
    tokenized = [_tokens(d) for d in corpus]
    df: Counter = Counter()
    for toks in tokenized:
        df.update(set(toks))
    n = len(corpus)
    idf = {term: math.log((n + 1) / (freq + 1)) + 1 for term, freq in df.items()}

    def vec(toks: list[str]) -> dict:
        tf = Counter(toks)
        total = sum(tf.values()) or 1
        return {t: (c / total) * idf.get(t, 0) for t, c in tf.items()}

    vectors = [vec(t) for t in tokenized]
    return idf, [vectors[0]], vectors[1:]


def _cosine(a: dict, b: dict) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _cosine_list(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _job_text(job: dict) -> str:
    tags = " ".join(job.get("tags") or [])
    return f"{job['title']} {job['company']} {tags} {job.get('description', '')}"


def _heuristic_reason(profile_skills: list[str], job: dict, score: float) -> str:
    job_blob = _job_text(job).lower()
    overlap = [s for s in profile_skills if s.lower() in job_blob][:6]
    if overlap:
        return f"Strong overlap on {', '.join(overlap)}. Estimated fit {round(score * 100)}%."
    return f"General relevance to your profile. Estimated fit {round(score * 100)}%."


def run_matching(top_k: int = 100) -> int:
    """Score all stored jobs against the current profile. Returns count."""
    with get_conn() as conn:
        profile = row_to_dict(conn.execute("SELECT * FROM profile WHERE id = 1").fetchone())
        job_rows = [row_to_dict(r) for r in conn.execute("SELECT * FROM jobs").fetchall()]

    if not profile or not job_rows:
        return 0

    profile_text = profile.get("profile_text") or profile.get("summary") or ""
    profile_skills = (profile.get("parsed_json") or {}).get("skills", []) if isinstance(
        profile.get("parsed_json"), dict
    ) else []

    scores: list[float] = []

    # Stage 1: scoring
    prof_emb = ai.embed(profile_text) if ai.settings.ai_enabled else None
    if prof_emb:
        for job in job_rows:
            job_emb = ai.embed(_job_text(job))
            scores.append(_cosine_list(prof_emb, job_emb) if job_emb else 0.0)
    else:
        _, prof_vecs, job_vecs = _tfidf_vectors(profile_text, [_job_text(j) for j in job_rows])
        pv = prof_vecs[0]
        scores = [_cosine(pv, jv) for jv in job_vecs]

    ranked = sorted(zip(job_rows, scores), key=lambda x: -x[1])[:top_k]

    with get_conn() as conn:
        conn.execute("DELETE FROM matches")
        for job, score in ranked:
            reasoning = _heuristic_reason(profile_skills, job, score)
            conn.execute(
                "INSERT INTO matches (job_id, score, reasoning) VALUES (?, ?, ?)",
                (job["id"], round(float(score), 3), reasoning),
            )
    return len(ranked)


def generate_cover_letter(job: dict, profile: dict) -> str:
    """Tailored cover letter (LLM if available, else a solid template)."""
    if ai.settings.ai_enabled:
        text = ai.chat_text(
            "You write concise, specific, confident cover letters (<180 words). No clichés.",
            f"Candidate summary: {profile.get('summary', '')}\n"
            f"Skills: {', '.join((profile.get('parsed_json') or {}).get('skills', []))}\n"
            f"Job: {job['title']} at {job['company']}\n"
            f"Description: {job.get('description', '')[:1500]}\n"
            "Write the cover letter.",
        )
        if text:
            return text.strip()

    name = profile.get("full_name") or "Candidate"
    skills = ", ".join((profile.get("parsed_json") or {}).get("skills", [])[:5])
    return (
        f"Dear {job['company']} Hiring Team,\n\n"
        f"I'm excited to apply for the {job['title']} role. My background "
        f"{'in ' + skills if skills else ''} aligns closely with what you're building. "
        f"{profile.get('summary', '')[:200]}\n\n"
        f"I'd welcome the chance to contribute to your team and would love to discuss "
        f"how my experience can help.\n\nBest regards,\n{name}"
    )
