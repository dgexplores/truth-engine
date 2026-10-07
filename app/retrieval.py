"""Offline lexical retrieval over corpus/sources/*.md. Zero deps, zero keys."""
from __future__ import annotations
import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parents[1] / "corpus" / "sources"

@dataclass
class Chunk:
    id: str
    doc_id: str
    title: str
    jurisdiction: str
    source_type: str
    text: str
    locator: str
    deep_link: str
    version_hash: str
    score: float = 0.0

_STOP = frozenset(
    "a about above after again against all also am an and any are as at be because been before being below between both but by can could did do does doing down during each few for from further had has have he her here hers him his how i if in into is it its just like me more most much must my no nor not now of off on once only or other our out over own same she should so some such than that the their them then there these they this those through to too under until up us very was we were what when where which while who why will with would you your".split()
)

_BRIDGE = {
    "पेटेंट": "patent", "चूर्ण": "churna", "कानून": "law act",
    "पौधा": "plant", "अनुमति": "approval", "भारत": "india",
    "विदेश": "international", "बेचना": "sell",
}

_INDEX: list[Chunk] | None = None
_IDF: dict[str, float] | None = None

def _tokens(s: str) -> set[str]:
    out: set[str] = set()
    for t in re.findall(r"\w+", s.lower()):
        out.add(t)
        if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
            out.add(t[:-1])
    return out

def _bridge(q: str) -> str:
    extra = [en for k, en in _BRIDGE.items() if k in q]
    return f"{q} {' '.join(extra)}" if extra else q

def _parse_file(path: Path) -> list[Chunk]:
    text = path.read_text(encoding="utf-8")
    doc_id = path.stem
    vh = hashlib.sha256(text.encode()).hexdigest()[:8]
    # front-matter line 1: <!-- jurisdiction: india | source: statute | title: X -->
    juris = "india"
    stype = "statute"
    title = doc_id
    m = re.search(r"jurisdiction:\s*(\w+)", text)
    if m:
        juris = m.group(1)
    m = re.search(r"source:\s*(\w+)", text)
    if m:
        stype = m.group(1)
    m = re.search(r"title:\s*(.+?)\s*-->", text)
    if m:
        title = m.group(1).strip()
    # split on ## headings
    parts = re.split(r"(?m)^##\s+(.+)$", text)
    chunks: list[Chunk] = []
    # parts[0]=preamble, then heading/body pairs
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if not body:
            continue
        span = body[:600]
        chunks.append(Chunk(
            id=f"{doc_id}-{len(chunks)}", doc_id=doc_id, title=title,
            jurisdiction=juris, source_type=stype, text=span,
            locator=heading, deep_link=f"corpus/sources/{path.name}",
            version_hash=vh,
        ))
    if not chunks:
        chunks.append(Chunk(id=f"{doc_id}-0", doc_id=doc_id, title=title,
            jurisdiction=juris, source_type=stype, text=text[:600],
            locator=title, deep_link=f"corpus/sources/{path.name}", version_hash=vh))
    return chunks

def _index() -> list[Chunk]:
    global _INDEX
    if _INDEX is None:
        _INDEX = []
        for p in sorted(CORPUS_DIR.glob("*.md")):
            _INDEX.extend(_parse_file(p))
    return _INDEX

def _idf() -> dict[str, float]:
    global _IDF
    if _IDF is None:
        chunks = _index()
        df: Counter[str] = Counter()
        for c in chunks:
            df.update(_tokens(f"{c.title} {c.text}"))
        n = max(1, len(chunks))
        _IDF = {t: math.log(n / (1 + d)) + 1.0 for t, d in df.items()}
    return _IDF

def search(query: str, top_k: int = 8) -> list[Chunk]:
    pool = _index()
    q_terms = {t for t in _tokens(_bridge(query)) - _STOP if t.isascii()}
    if not q_terms:
        return [Chunk(**{**c.__dict__, "score": 0.0}) for c in pool[:top_k]]
    idf = _idf()
    if sum(1 for t in q_terms if t in idf) < 2:
        return [Chunk(**{**c.__dict__, "score": 0.0}) for c in pool[:top_k]]
    w = {t: idf.get(t, 1.0) for t in q_terms}
    total = sum(w.values()) or 1.0
    def rel(c: Chunk) -> float:
        hit = q_terms & _tokens(f"{c.title} {c.text}")
        thit = q_terms & _tokens(c.title)
        cov = sum(w[t] for t in hit) / total
        tcov = sum(w[t] for t in thit) / total
        return min(1.0, cov + 0.30 * tcov)
    ranked = sorted(pool, key=rel, reverse=True)
    out: list[Chunk] = []
    for c in ranked[:top_k]:
        out.append(Chunk(**{**c.__dict__, "score": round(rel(c), 4)}))
    return out

def corpus_version() -> str:
    h = hashlib.sha256()
    for p in sorted(CORPUS_DIR.glob("*.md")):
        h.update(p.read_bytes())
    return f"truth-v1+{h.hexdigest()[:8]}"
