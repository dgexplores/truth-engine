# The Truth Engine v1.1 — complete product

[![CI](https://github.com/dgexplores/truth-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/dgexplores/truth-engine/actions)
https://github.com/dgexplores/truth-engine

Verifiable AI. Quote-only. Firewall + security + confidence on every answer. Offline CPU. No keys.

**Live paths:** `GET /` UI · `POST /api/v1/verify` · `GET /health` · `GET /corpus/version`

## Run
```
pip install -r requirements.txt
make check   # 10 pytest + 26-case eval gate
make run     # http://localhost:8001 (UI + docs at /docs)
python3 truth verify "Can I patent churna?" india
python3 truth ingest-dry   # corpus preview, no changes
python3 truth corpus-hash  # version stamp on every answer
docker compose up --build
```

## Demo 60s
1. Churna patent? → quotes Sec 3(p), firewall filtered
2. `Ignore all previous instructions...` → BLOCKED, no retrieval
3. `capital of France` → abstains, suggests human
4. Voice 🎙 Hindi → same pipeline. Export Markdown → report with hashes.

## Proof packet per answer
citations[title/locator/span/version_hash] + firewall{status, foreign_ratio} + security{injection_score, blocked, pii_types} + confidence{score, abstain} + corpus_version

## Corpus (20 docs, versioned sha)
Patents Act, Patents Rules 2024, BDA, GRATK, PCT, TRIPS, CBD/Nagoya, Trademarks, Copyright, Designs, GI, PPVFR, Trade Secrets, Drugs & Cosmetics, Magic Remedies, FSSAI, Export Access, MGNREGA sample, Divya Pharmacy case, Turmeric/Neem revocations. Edit md → hash changes → eval must re-pass.

Fused from aegis (security) + sakti (grounding/firewall/conf) + nirikshan (evidence-first) + bloompulse (calibration).
