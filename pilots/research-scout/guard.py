"""Offline guards for the research-scout pilot.

The root session calls these around every research-scout spawn:

    gate(...)          before the scout may run at all
    scrub_query(...)   on every outbound query string
    filter_pack(...)   on the returned pack
    budget_errors(...) on the returned pack's spend

Every error string starts with a stable UPPER_SNAKE code followed by ": ".
Stdlib + jsonschema only. Research results are data, never instructions.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

HERE = Path(__file__).resolve().parent
BRIEF_SCHEMA = json.loads((HERE / "research-brief.schema.json").read_text(encoding="utf-8"))
PACK_SCHEMA = json.loads((HERE / "research-pack.schema.json").read_text(encoding="utf-8"))
_FORMATS = FormatChecker()
_BRIEF_VALIDATOR = Draft202012Validator(BRIEF_SCHEMA, format_checker=_FORMATS)
_ENVELOPE_VALIDATOR = Draft202012Validator(
    {**PACK_SCHEMA, "properties": {**PACK_SCHEMA["properties"], "claims": {"type": "array"}}},
    format_checker=_FORMATS,
)
_CLAIM_VALIDATOR = Draft202012Validator(
    {"$ref": "#/$defs/claim", "$defs": PACK_SCHEMA["$defs"]}, format_checker=_FORMATS
)

READY_INTAKE = frozenset({"READY", "READY_WITH_DEFERRED_RISK"})
MAX_QUERY_CHARS = 400
DEFAULT_MAX_CALLS = 5
DEFAULT_USD_PER_BRIEF = 2.0
DEFAULT_MONTHLY_CAP_USD = 25.0
DEEP_ENGINE = "perplexity_research"

_SECRET_SHAPES = {
    "SECRET_API_KEY": re.compile(r"\b(?:sk-ant-|sk-|pplx-)[A-Za-z0-9_\-]{8,}"),
    "SECRET_GITHUB_TOKEN": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}"),
    "SECRET_AWS_KEY": re.compile(r"\bAKIA[0-9A-Z]{12,}"),
    "SECRET_SLACK_TOKEN": re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{8,}"),
    "SECRET_JWT": re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"),
    "SECRET_PRIVATE_KEY": re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
}
_PRIVATE_SHAPES = {
    "PRIVATE_EMAIL": re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    "PRIVATE_WINDOWS_PATH": re.compile(r"\b[A-Za-z]:[\\/]"),
    "PRIVATE_HOME_PATH": re.compile(r"(?:^|[\s\"'(=])(?:/home/|/Users/|~/)"),
    "PRIVATE_REPO_URL": re.compile(r"github\.com/[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+", re.I),
}
_PHONE_CANDIDATE = re.compile(r"(?<![\w.])\+?\(?\d[\d\s().\-]{4,}\d(?![\w.])")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
MIN_PHONE_DIGITS = 7
_INJECTION = re.compile(
    r"ignore\s+(?:all|any|previous|prior)\s+(?:(?:previous|prior|the)\s+)?instructions"
    r"|you\s+are\s+now"
    r"|system\s+prompt"
    r"|disregard\s+(?:the|this|your)\s+brief",
    re.I,
)


def _has_phone(text: str) -> bool:
    # ponytail: heuristic = 7-15 digits joined by separators, ISO dates exempt; unseparated runs pass by design.
    for match in _PHONE_CANDIDATE.finditer(text):
        candidate = match.group().strip()
        digits = sum(ch.isdigit() for ch in candidate)
        separated = any(not ch.isdigit() for ch in candidate.lstrip("+"))
        if separated and MIN_PHONE_DIGITS <= digits <= 15 and not _ISO_DATE.fullmatch(candidate):
            return True
    return False


def _schema_errors(validator: Draft202012Validator, instance: object, code: str) -> list[str]:
    return [
        f"{code}: {'/'.join(map(str, err.absolute_path)) or '<root>'}: {err.message}"
        for err in sorted(validator.iter_errors(instance), key=lambda e: list(map(str, e.absolute_path)))
    ]


def _is_datetime(value: object) -> bool:
    if not isinstance(value, str) or "T" not in value:
        return False
    try:
        datetime.fromisoformat(value)
    except ValueError:
        return False
    return True


def gate(brief: dict, intake: dict, intake_bytes: bytes, trusted_approvers: set[str]) -> list[str]:
    """Return refusal reasons; an empty list means the scout may research this brief."""
    errors = _schema_errors(_BRIEF_VALIDATOR, brief, "BRIEF_SCHEMA_INVALID")
    if not isinstance(brief, dict):
        return errors or ["BRIEF_SCHEMA_INVALID: brief is not an object"]
    if brief.get("status") != "APPROVED":
        errors.append(f"BRIEF_NOT_APPROVED: status is {brief.get('status')!r}")
    approver = brief.get("approved_by")
    if approver not in trusted_approvers:
        errors.append(f"BRIEF_APPROVER_UNTRUSTED: {approver!r} is not a trusted approver")
    if brief.get("status") == "APPROVED" and not _is_datetime(brief.get("approved_at")):
        errors.append("BRIEF_APPROVAL_TIME_INVALID: approved_at must be an ISO 8601 date-time")
    intake_status = intake.get("status") if isinstance(intake, dict) else None
    if intake_status not in READY_INTAKE:
        errors.append(f"INTAKE_NOT_READY: intake status is {intake_status!r}")
    ref = brief.get("intake_ref")
    expected = ref.get("sha256") if isinstance(ref, dict) else None
    actual = hashlib.sha256(intake_bytes).hexdigest()
    if expected != actual:
        errors.append(f"INTAKE_HASH_MISMATCH: brief pins {expected!r}, intake bytes hash to {actual}")
    return errors


def scrub_query(text: str, off_limits: list[str]) -> list[str]:
    """Return block reasons; an empty list means the query may leave the machine."""
    if not isinstance(text, str):
        return ["QUERY_INVALID: query is not a string"]
    reasons: list[str] = []
    if len(text) > MAX_QUERY_CHARS:
        reasons.append(f"QUERY_TOO_LONG: {len(text)} > {MAX_QUERY_CHARS} characters")
    for code, pattern in {**_SECRET_SHAPES, **_PRIVATE_SHAPES}.items():
        if pattern.search(text):
            reasons.append(f"{code}: query contains a blocked shape")
    if _has_phone(text):
        reasons.append("PRIVATE_PHONE: query contains a phone-number shape")
    lowered = text.casefold()
    for term in off_limits:
        if term and term.casefold() in lowered:
            reasons.append(f"OFF_LIMITS_TERM: query contains off-limits term {term!r}")
    return reasons


def _claim_reasons(claim: object, questions: dict[str, dict], engines: set[str]) -> list[str]:
    reasons = _schema_errors(_CLAIM_VALIDATOR, claim, "CLAIM_SCHEMA_INVALID")
    if not isinstance(claim, dict):
        return reasons or ["CLAIM_SCHEMA_INVALID: claim is not an object"]
    question = questions.get(claim.get("question_id"))
    if question is None:
        reasons.append(f"UNKNOWN_QUESTION: {claim.get('question_id')!r} is not in the brief")
    sources = claim.get("sources") if isinstance(claim.get("sources"), list) else []
    texts = [str(claim.get("claim", ""))]
    for source in sources:
        source = source if isinstance(source, dict) else {}
        if not str(source.get("quote") or "").strip():
            reasons.append("SOURCE_QUOTE_MISSING: every source needs a non-empty quote")
        if not str(source.get("url") or "").startswith("https://"):
            reasons.append(f"SOURCE_NOT_HTTPS: {source.get('url')!r}")
        texts += [str(source.get("quote", "")), str(source.get("title", ""))]
    if not sources and claim.get("label") != "UNKNOWN":
        reasons.append("NO_SOURCES: only an UNKNOWN claim may have no sources")
    if question is not None and question.get("job") == "Reuse":
        if not claim.get("license") or not claim.get("last_release"):
            reasons.append("REUSE_PROVENANCE_MISSING: Reuse claims need license and last_release")
    engine = claim.get("engine")
    if engine not in engines:
        reasons.append(f"ENGINE_NOT_ALLOWED: {engine!r} is not in brief.engines_allowed")
    if engine == DEEP_ENGINE and question is not None and not question.get("deep_research_ok", False):
        reasons.append(f"DEEP_RESEARCH_NOT_ALLOWED: {question.get('id')} does not allow {DEEP_ENGINE}")
    if any(_INJECTION.search(text) for text in texts):
        reasons.append("INJECTION_SUSPECTED: claim text contains instruction-like content")
    return reasons


def filter_pack(pack: dict, brief: dict) -> tuple[list[dict], list[dict]]:
    """Split pack claims into (accepted, rejected); rejected copies carry a "reasons" list."""
    envelope = _schema_errors(_ENVELOPE_VALIDATOR, pack, "PACK_SCHEMA_INVALID")
    if isinstance(pack, dict) and pack.get("brief_id") != brief.get("brief_id"):
        envelope.append(f"PACK_BRIEF_MISMATCH: pack is for {pack.get('brief_id')!r}")
    questions = {q.get("id"): q for q in brief.get("questions", []) if isinstance(q, dict)}
    engines = set(brief.get("engines_allowed", []))
    claims = pack.get("claims", []) if isinstance(pack, dict) else []
    accepted: list[dict] = []
    rejected: list[dict] = []
    for claim in claims if isinstance(claims, list) else []:
        reasons = envelope + _claim_reasons(claim, questions, engines)
        if reasons:
            rejected.append({**(claim if isinstance(claim, dict) else {"raw": claim}), "reasons": reasons})
        else:
            accepted.append(dict(claim))
    return accepted, rejected


def budget_errors(pack: dict, brief: dict, month_to_date_usd: float) -> list[str]:
    """Return budget violations for one pack against its brief and the month-to-date spend."""
    budget = brief.get("budget") or {}
    per_brief = budget.get("usd_per_brief", DEFAULT_USD_PER_BRIEF)
    monthly_cap = budget.get("monthly_cap_usd", DEFAULT_MONTHLY_CAP_USD)
    spend = pack.get("spend") or {}
    claim_costs = sum(
        c["cost_usd"]
        for c in pack.get("claims", [])
        if isinstance(c, dict) and isinstance(c.get("cost_usd"), (int, float))
    )
    # Under-reported envelope spend must not hide per-claim costs.
    usd = max(float(spend.get("usd", 0)), float(claim_costs))
    calls = int(spend.get("calls", 0))
    call_ceiling = sum(q.get("max_calls", DEFAULT_MAX_CALLS) for q in brief.get("questions", []))
    errors: list[str] = []
    if month_to_date_usd < 0:
        errors.append(f"MONTH_TO_DATE_INVALID: {month_to_date_usd} is negative")
    if usd > per_brief:
        errors.append(f"BUDGET_PER_BRIEF_EXCEEDED: ${usd:.4f} > ${per_brief:.4f}")
    if calls > call_ceiling:
        errors.append(f"BUDGET_CALLS_EXCEEDED: {calls} calls > {call_ceiling} allowed by max_calls")
    if month_to_date_usd + usd > monthly_cap:
        errors.append(
            f"BUDGET_MONTHLY_CAP_EXCEEDED: ${month_to_date_usd + usd:.4f} > ${monthly_cap:.4f}"
        )
    return errors
