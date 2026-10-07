"""Truth Engine schemas."""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal

class VerifyRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    jurisdiction: Literal["india", "international"] = "india"
    language: Literal["en", "hi"] = "en"

class Citation(BaseModel):
    title: str
    locator: str
    span_text: str
    deep_link: str = ""
    version_hash: str

class FirewallReport(BaseModel):
    status: Literal["clean", "filtered", "mixed_query", "leak_warning"]
    message: str = ""
    foreign_ratio: float = 0.0

class SecurityReport(BaseModel):
    injection_score: float
    injection_blocked: bool
    injection_labels: list[str] = []
    pii_types: list[str] = []
    pii_redacted_query: str = ""

class Confidence(BaseModel):
    score: float
    abstain: bool
    rationale: str = ""

class VerifyResponse(BaseModel):
    answer: str
    answer_simple: str = ""
    citations: list[Citation] = []
    confidence: Confidence
    firewall: FirewallReport
    security: SecurityReport
    corpus_version: str
    abstained: bool = False
