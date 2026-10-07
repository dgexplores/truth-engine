"""Firewall + confidence. Minimal ports."""
from __future__ import annotations
import re
from .retrieval import Chunk

_INDIA = re.compile(r"\b(india|indian|sec\s*3\(p\)|bda|tkdl|ayush|ayurveda|patents act)\b", re.I)
_INTL = re.compile(r"\b(wipo|gratk|pct|cbd|nagoya|trips|madrid|hague)\b", re.I)

def firewall(query: str, requested: str, chunks: list[Chunk]) -> tuple[list[Chunk], dict]:
    foreign = [c for c in chunks if c.jurisdiction != requested]
    kept = [c for c in chunks if c.jurisdiction == requested]
    mixed = bool(_INDIA.search(query) and _INTL.search(query))
    best_k = max((c.score for c in kept), default=-1.0)
    best_f = max((c.score for c in foreign), default=-1.0)
    if mixed:
        status, msg = "mixed_query", f"Query spans both regimes — answering from {requested} only."
    elif foreign and best_f > best_k:
        status, msg = "leak_warning", f"Top match is other regime — held back, answering from {requested} only."
    elif foreign:
        status, msg = "filtered", f"Removed {len(foreign)} of {len(chunks)} off-jurisdiction candidates."
    else:
        status, msg = "clean", ""
    kept_or_all = kept or list(chunks)
    return kept_or_all, {"status": status, "message": msg, "foreign_ratio": round(len(foreign) / max(1, len(chunks)), 2)}

_EXP = 0.65
def confidence(chunks: list[Chunk], threshold: float = 0.45) -> tuple[float, bool, str]:
    if not chunks:
        return 12.0, True, "No grounding chunks — abstaining."
    top = max(0.0, min(1.0, chunks[0].score))
    if top <= 0.0:
        return 5.0, True, "No span shares a term with question — nothing to ground."
    base = top ** _EXP
    div = len({c.source_type for c in chunks})
    bonus = min(0.15, (div - 1) * 0.07)
    pen = 0 if len(chunks) >= 3 else -0.20
    score = max(5, min(96, round((base + bonus + pen) * 100, 1)))
    abstain = score < threshold * 100
    r = f"Top relevance {top:.2f} over {len(chunks)} chunks, {div} type(s). " + ("Below threshold — abstaining." if abstain else "Grounded.")
    return float(score), abstain, r
