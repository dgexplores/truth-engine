# PRODUCT — The Truth Engine

Problem: LLM answers hallucinate sections, mix jurisdictions, leak PII, fall for injections.
User: student, villager, small business owner asking law/data questions in Hindi/English, offline, no keys.
Promise: every answer quoted verbatim + firewall verdict + injection/PII report + confidence + corpus hash. Abstains when unsure.

Non-goals: free-text generation, login/auth, paid models, DB required. DB optional later.
Inputs: query text/voice, jurisdiction toggle. Outputs: answer + 3 citations + scores.
Gates: 20-case eval must pass. Quote-verbatim enforced. Injection blocked fail-closed.

# ARCHITECTURE

browser UI (voice local) -> POST /api/v1/verify -> security scan -> IDF lexical search (corpus/*.md) -> firewall filter -> confidence gate -> quote-stitch answer. No LLM at runtime. Deterministic. CPU <300ms. Version hash = sha256 of corpus.

# OPERATIONS

make check = pytest + eval. make run port 8001. Docker + render.yaml ready. Audit.log appends q_len/juris/inj. Rate 60/min IP. CORS via CORS_EXTRA_ORIGINS. Corpus edit -> version hash changes, eval re-runs. Rollback = git revert + redeploy.
