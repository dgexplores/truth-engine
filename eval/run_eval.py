"""Eval gate: posts golden set to /verify, exits non-zero on fail."""
from __future__ import annotations
import json, sys
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app

def main() -> int:
    gold = json.loads((Path(__file__).parent / "golden_set.json").read_text())
    c = TestClient(app)
    fails: list[str] = []
    for g in gold:
        r = c.post("/api/v1/verify", json={"query": g["q"], "jurisdiction": g["jurisdiction"]})
        assert r.status_code == 200, g["q"]
        d = r.json()
        exp = g["expect"]
        if exp == "blocked" and not d["security"]["injection_blocked"]:
            fails.append(f"not blocked: {g['q']}")
        if exp == "abstain" and not d["abstained"]:
            fails.append(f"not abstained: {g['q']}")
        if exp in ("answer", "answer_pii") and d["abstained"]:
            fails.append(f"wrong abstain: {g['q']}")
        if exp in ("answer", "answer_pii") and g.get("must_cite"):
            titles = " ".join(x["title"] for x in d["citations"])
            if g["must_cite"].lower() not in titles.lower():
                fails.append(f"wrong cite {g['q']}: {titles}")
            # quote-verbatim: every > line must be substring of a cited span
            for line in d["answer"].splitlines():
                if line.startswith("> "):
                    q = line[2:].strip()
                    if q and not any(q in x["span_text"] for x in d["citations"]):
                        fails.append(f"non-verbatim quote: {q[:60]}")
        if exp == "answer_pii" and not d["security"]["pii_types"]:
            fails.append("PII not detected")
    print(f"{len(gold)-len(fails)}/{len(gold)} pass")
    for f in fails:
        print("FAIL:", f)
    return 1 if fails else 0

if __name__ == "__main__":
    raise SystemExit(main())
