"""Truth Engine — /verify + static UI + hardening. Offline, CPU, no keys."""
from __future__ import annotations
import os
import time
import uuid
from collections import defaultdict
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .schemas import (
    Citation, Confidence, FirewallReport, SecurityReport, VerifyRequest, VerifyResponse,
)
from . import retrieval as R
from . import guard as G
from . import security as S

app = FastAPI(title="Truth Engine", version="1.0.0")

origins = [o.strip() for o in os.getenv("CORS_EXTRA_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", *origins] or ["*"],
    allow_methods=["GET", "POST"], allow_headers=["*"])

# simple in-memory rate limit: 60/min per IP, fail-closed on verify only
_BUCKET: dict[str, list[float]] = defaultdict(list)
LIMIT = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

@app.middleware("http")
async def req_id_and_headers(request: Request, call_next):
    rid = str(uuid.uuid4())[:8]
    request.state.rid = rid
    resp: Response = await call_next(request)
    resp.headers["X-Request-ID"] = rid
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Corpus-Version"] = R.corpus_version()
    return resp

def _audit(line: str):
    try:
        with open(Path(__file__).resolve().parents[1] / "audit.log", "a") as f:
            f.write(line + "\n")
    except OSError:
        pass

@app.get("/health")
def health():
    return {"status": "ok", "corpus_version": R.corpus_version()}

@app.get("/corpus/version")
def version():
    return {"corpus_version": R.corpus_version(), "docs": len(R._index())}

@app.post("/api/v1/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest, request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    _BUCKET[ip] = [t for t in _BUCKET[ip] if now - t < 60]
    if len(_BUCKET[ip]) >= LIMIT:
        return VerifyResponse(answer="Rate limited. Retry in a minute.", citations=[],
            confidence=Confidence(score=0, abstain=True, rationale="429"),
            firewall=FirewallReport(status="clean"),
            security=SecurityReport(injection_score=0, injection_blocked=False),
            corpus_version=R.corpus_version(), abstained=True)
    _BUCKET[ip].append(now)

    inj_score, inj_labels = S.scan_injection(req.query)
    redacted_q, pii_types = S.redact_pii(req.query)
    inj_blocked = inj_score >= S.BLOCK_THRESHOLD
    _audit(f"q_len={len(req.query)} juris={req.jurisdiction} inj={inj_score} blocked={inj_blocked} pii={pii_types}")

    if inj_blocked:
        return VerifyResponse(
            answer="Blocked: prompt-injection pattern detected. No retrieval run. No answer generated.",
            answer_simple="Blocked unsafe request.",
            citations=[],
            confidence=Confidence(score=10.0, abstain=True, rationale=f"Injection {inj_score} >= threshold. Fail-closed."),
            firewall=FirewallReport(status="clean"),
            security=SecurityReport(injection_score=inj_score, injection_blocked=True,
                injection_labels=inj_labels, pii_types=pii_types, pii_redacted_query=redacted_q),
            corpus_version=R.corpus_version(), abstained=True,
        )

    cands = R.search(redacted_q, top_k=12)
    kept, fw = G.firewall(req.query, req.jurisdiction, cands)
    top = kept[:4]
    score, abstain, rationale = G.confidence(top)

    if abstain or not top or top[0].score <= 0:
        return VerifyResponse(
            answer="Not sure — no grounding span found. Talk to a human expert instead of guessing.",
            answer_simple="Not sure. Ask a human expert.",
            citations=[],
            confidence=Confidence(score=score, abstain=True, rationale=rationale),
            firewall=FirewallReport(**fw),
            security=SecurityReport(injection_score=inj_score, injection_blocked=False,
                injection_labels=inj_labels, pii_types=pii_types, pii_redacted_query=redacted_q),
            corpus_version=R.corpus_version(), abstained=True,
        )

    lines = [f"> {c.text.strip()}\n— {c.title}, {c.locator}" for c in top[:3]]
    verdict = top[0].title
    answer = f"Answer from {req.jurisdiction} law (top: {verdict}):\n\n" + "\n\n".join(lines)
    if fw["status"] in ("filtered", "leak_warning", "mixed_query") and fw["message"]:
        answer = f"**{fw['message']}**\n\n" + answer
    simple = f"In plain words: top match is {verdict}. Check quotes + links before acting."
    cites = [Citation(title=c.title, locator=c.locator, span_text=c.text,
        deep_link=c.deep_link, version_hash=c.version_hash) for c in top[:3]]
    return VerifyResponse(
        answer=answer, answer_simple=simple, citations=cites,
        confidence=Confidence(score=score, abstain=False, rationale=rationale),
        firewall=FirewallReport(**fw),
        security=SecurityReport(injection_score=inj_score, injection_blocked=False,
            injection_labels=inj_labels, pii_types=pii_types, pii_redacted_query=redacted_q),
        corpus_version=R.corpus_version(), abstained=False,
    )

FRONT = Path(__file__).resolve().parents[1] / "frontend"
if FRONT.exists():
    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(FRONT / "index.html")
