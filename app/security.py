"""Injection + PII scan. Ported minimal from aegis-gateway."""
from __future__ import annotations
import re

_PATTERNS: list[tuple[re.Pattern[str], float, str]] = [
    (re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)", re.I), 0.45, "instruction_override"),
    (re.compile(r"disregard\s+(all\s+)?(previous|prior|your)\s+(instructions|rules)", re.I), 0.45, "instruction_override"),
    (re.compile(r"forget\s+(everything|all)\b", re.I), 0.40, "instruction_override"),
    (re.compile(r"reveal\s+your\s+(instructions|prompt|rules)|system\s*prompt", re.I), 0.40, "system_prompt_extraction"),
    (re.compile(r"(repeat|print|output|show)\s+(everything|the text|your prompt|instructions)\s+(above|before)", re.I), 0.45, "context_exfiltration"),
    (re.compile(r"pretend\s+(you\s+)?(are|to\s+be)\s+.*(no|without)\s+(restrictions|filters)", re.I), 0.35, "jailbreak"),
    (re.compile(r"\bDAN\b|\bdeveloper mode\b|do\s+anything\s+now", re.I), 0.30, "jailbreak"),
    (re.compile(r"(show|print|reveal|give|list)\s+(me\s+)?(your\s+)?(api[\s_-]?keys?|secrets?|passwords?|tokens?)", re.I), 0.35, "credential_probe"),
    (re.compile(r"</?(system|assistant)>", re.I), 0.30, "role_tag_injection"),
    (re.compile(r"(send|forward|post|upload)\b.{0,60}\b(\w+@\w+\.\w+|https?://)", re.I), 0.30, "exfil_channel"),
]

_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]{2,}\b")
_PHONE = re.compile(r"(?<!\w)(?:\+?91[\s.-]?)?[6-9]\d{9}(?!\w)")
_AADHAAR = re.compile(r"(?<!\d)[2-9]\d{3}[\s\-]?\d{4}[\s\-]?\d{4}(?!\d)")
_PAN = re.compile(r"(?<![A-Z0-9])[A-Z]{5}[0-9]{4}[A-Z](?![A-Z0-9])")
_CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")
_UPI = re.compile(r"(?<!\w)[a-zA-Z0-9.\-_]{2,64}@[a-zA-Z]{2,64}\b")

BLOCK_THRESHOLD = 0.35

def scan_injection(text: str) -> tuple[float, list[str]]:
    total = 0.0
    labels: set[str] = set()
    for pat, w, label in _PATTERNS:
        if pat.search(text or ""):
            labels.add(label)
            total += w
    return round(min(total, 0.98), 3), sorted(labels)

def redact_pii(text: str) -> tuple[str, list[str]]:
    types: list[str] = []
    out = text or ""
    for pat, name in [(_EMAIL, "EMAIL"), (_PAN, "PAN"), (_AADHAAR, "AADHAAR"), (_PHONE, "PHONE"), (_CARD, "CARD"), (_UPI, "UPI")]:
        if pat.search(out):
            if name not in types:
                types.append(name)
            out = pat.sub(f"«{name}»", out)
    return out, types
