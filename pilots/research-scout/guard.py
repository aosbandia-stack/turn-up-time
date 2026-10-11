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
import math
import re
import unicodedata
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
OWNER_MONTHLY_CAP_USD = 25.0  # owner-loaded prepaid credit; a brief may only lower it
DEFAULT_MONTHLY_CAP_USD = OWNER_MONTHLY_CAP_USD
DEEP_ENGINE = "perplexity_research"

_SECRET_SHAPES = {
    "SECRET_API_KEY": re.compile(r"\b(?:sk-ant-|sk-|pplx-)[A-Za-z0-9_\-]{8,}"),
    "SECRET_GITHUB_TOKEN": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}"),
    "SECRET_AWS_KEY": re.compile(r"\bAKIA[0-9A-Z]{12,}"),
    "SECRET_SLACK_TOKEN": re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{8,}"),
    "SECRET_JWT": re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"),
    "SECRET_PRIVATE_KEY": re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
    "SECRET_BEARER_TOKEN": re.compile(r"\b[Bb]earer\s+[A-Za-z0-9._~+/\-]{20,}"),
}
# A key split by one whitespace char is re-joined and must then be 20+ chars with a digit.
MIN_SPLIT_SECRET_CHARS = 20
_PRIVATE_SHAPES = {
    "PRIVATE_EMAIL": re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    "PRIVATE_WINDOWS_PATH": re.compile(r"\b[A-Za-z]:[\\/]"),
    "PRIVATE_UNC_PATH": re.compile(r"(?:^|[\s\"'(=])\\\\[\w.$\-]+\\[\w.$\-]+"),
    "PRIVATE_HOME_PATH": re.compile(r"(?:^|[\s\"'(=])(?:/home/|/Users/|~/)"),
    "PRIVATE_REPO_URL": re.compile(r"github\.com/[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+", re.I),
}
_PHONE_CANDIDATE = re.compile(r"(?<![\w.])\+?\(?\d[\d\s().\-]{4,}\d(?![\w.])")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
MIN_PHONE_DIGITS = 7
# ponytail: marker list, not a complete defence; add phrasings as auditors report misses.
# Word boundaries and continuation lookaheads keep ordinary prose ("ignore the above-the-fold
# banner", "apps that act as admin require UAC", "if you're now using Tauri") from matching.
_ROLE = r"(?:the\s+|an?\s+)?(?:system|developer|admin(?:istrator)?|assistant|root)\b"
_PERSONA = r"(?-i:[A-Z]{2,})\b(?=\s*(?:[.,;:!?]|$|and\b))"  # all-caps name such as DAN
_SENTENCE_START = r"""(?:^|[.!?;:\n"'(>])\s*(?:(?:please|now|and)\s+)*"""
_INJECTION = re.compile(
    r"ignore\s+(?:all|any|previous|prior)\s+(?:(?:previous|prior|the)\s+)?instructions\b"
    r"|ignore\s+(?:the\s+)?(?:above|prior)\b(?!-)"
    r"|you(?:['’]|\s+a)re\s+now\b(?!\s+(?:able|ready|\w+ing)\b)"
    r"|system\s+prompt\b"
    r"|disregard\s+(?:the|this|your)\s+brief\b"
    r"|disregard\s+(?:(?:all|any|the)\s+)?(?:prior|previous|above|earlier)\s+"
    r"(?:instructions|guidance|rules|context)\b"
    r"|forget\s+(?:everything|all)\s+(?:above\b|(?:before|prior)\b"
    r"(?=\s*(?:[.!?:;,]|$|(?:this|that|here|now|instructions|guidance|rules|context)\b)))"
    r"|new\s+instructions\s*:"
    r"|override\s+the\s+(?:brief\b|(?:instructions|rules)\b(?!\s+(?:field|file|property|template"
    r"|section|key|attribute|option|setting|panel|array|object|list)s?\b))"
    r"|<\s*/?\s*system\s*>"
    + rf"|{_SENTENCE_START}act\s+as\s+(?:{_ROLE}(?!\s+(?:tray|icon|clock|font|bar|menu|settings)\b)|{_PERSONA})",
    re.I,
)


def _strip_format(text: str) -> str:
    """Drop invisible format characters (Unicode Cf: zero-width, BOM, soft hyphen)."""
    return "".join(ch for ch in text if unicodedata.category(ch) != "Cf")


def _is_blank(text: str) -> bool:
    return not "".join(_strip_format(text).split())


def _finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _non_finite_errors(value: object, code: str, path: str = "") -> list[str]:
    """jsonschema accepts NaN/inf as numbers; report each non-finite float as schema-invalid."""
    if isinstance(value, float) and not math.isfinite(value):
        return [f"{code}: {path or '<root>'}: {value!r} is not a finite number"]
    items = value.items() if isinstance(value, dict) else enumerate(value) if isinstance(value, list) else ()
    return [err for key, item in items for err in _non_finite_errors(item, code, f"{path}/{key}".lstrip("/"))]


def _secret_codes(text: str) -> set[str]:
    codes = {code for code, pattern in _SECRET_SHAPES.items() if pattern.search(text)}
    runs = text.split()
    # ponytail: re-joins one split per token pair; keys split twice or more still pass.
    for joined in (left + right for left, right in zip(runs, runs[1:])):
        for code, pattern in _SECRET_SHAPES.items():
            match = pattern.search(joined)
            token = match.group() if match else ""
            if len(token) >= MIN_SPLIT_SECRET_CHARS and any(ch.isdigit() for ch in token):
                codes.add(code)
    return codes


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


def _duplicate_question_errors(brief: dict) -> list[str]:
    """Question IDs are lookup keys, so even otherwise-valid duplicates are ambiguous."""
    questions = brief.get("questions", [])
    seen: set[str] = set()
    duplicates: set[str] = set()
    for question in questions if isinstance(questions, list) else []:
        question_id = question.get("id") if isinstance(question, dict) else None
        if not isinstance(question_id, str):
            continue  # malformed IDs are the brief schema's responsibility
        if question_id in seen:
            duplicates.add(question_id)
        seen.add(question_id)
    return [f"BRIEF_DUPLICATE_QUESTION_ID: {question_id!r} occurs more than once" for question_id in sorted(duplicates)]


def _is_datetime(value: object) -> bool:
    if not isinstance(value, str) or "T" not in value:
        return False
    try:
        datetime.fromisoformat(value)
    except ValueError:
        return False
    return True


def _parse_intake(intake_bytes: object) -> tuple[object, list[str]]:
    if not isinstance(intake_bytes, (bytes, bytearray)):
        return None, ["INTAKE_UNPARSEABLE: intake_bytes is not bytes"]
    try:
        return json.loads(intake_bytes), []
    except ValueError as exc:  # JSONDecodeError and UnicodeDecodeError
        return None, [f"INTAKE_UNPARSEABLE: {exc}"]


def gate(
    brief: dict, intake: dict | None, intake_bytes: bytes, trusted_approvers: set[str]
) -> list[str]:
    """Return refusal reasons; an empty list means the scout may research this brief.

    The intake status is read from intake_bytes, the same bytes the brief's sha256 pins. `intake`
    is optional; when given it must equal the parsed bytes or the gate refuses with INTAKE_MISMATCH.
    """
    errors = _schema_errors(_BRIEF_VALIDATOR, brief, "BRIEF_SCHEMA_INVALID")
    errors += _non_finite_errors(brief, "BRIEF_SCHEMA_INVALID")
    if not isinstance(brief, dict):
        return errors or ["BRIEF_SCHEMA_INVALID: brief is not an object"]
    errors += _duplicate_question_errors(brief)
    if brief.get("status") != "APPROVED":
        errors.append(f"BRIEF_NOT_APPROVED: status is {brief.get('status')!r}")
    approver = brief.get("approved_by")
    if approver not in trusted_approvers:
        errors.append(f"BRIEF_APPROVER_UNTRUSTED: {approver!r} is not a trusted approver")
    if brief.get("status") == "APPROVED" and not _is_datetime(brief.get("approved_at")):
        errors.append("BRIEF_APPROVAL_TIME_INVALID: approved_at must be an ISO 8601 date-time")
    parsed, parse_errors = _parse_intake(intake_bytes)
    errors += parse_errors
    if intake is not None and intake != parsed:
        errors.append("INTAKE_MISMATCH: supplied intake dict differs from the parsed intake bytes")
    intake_status = parsed.get("status") if isinstance(parsed, dict) else None
    if intake_status not in READY_INTAKE:
        errors.append(f"INTAKE_NOT_READY: intake status is {intake_status!r}")
    ref = brief.get("intake_ref")
    expected = ref.get("sha256") if isinstance(ref, dict) else None
    actual = hashlib.sha256(intake_bytes).hexdigest() if isinstance(intake_bytes, (bytes, bytearray)) else None
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
    visible = _strip_format(text)
    secrets = _secret_codes(visible)
    reasons += [f"{code}: query contains a blocked shape" for code in _SECRET_SHAPES if code in secrets]
    for code, pattern in _PRIVATE_SHAPES.items():
        if pattern.search(visible):
            reasons.append(f"{code}: query contains a blocked shape")
    if _has_phone(visible):
        reasons.append("PRIVATE_PHONE: query contains a phone-number shape")
    lowered = " ".join(visible.split()).casefold()
    for term in off_limits:
        needle = " ".join(_strip_format(term).split()).casefold() if isinstance(term, str) else ""
        if needle and needle in lowered:
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
        if _is_blank(str(source.get("quote") or "")):
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
    texts += [str(claim.get("license", "")), str(claim.get("tool_preset", ""))]
    if "cost_usd" in claim and not _finite(claim["cost_usd"]):
        reasons.append(f"CLAIM_COST_INVALID: cost_usd {claim['cost_usd']!r} is not a finite number")
    if any(_INJECTION.search(_strip_format(text)) for text in texts):
        reasons.append("INJECTION_SUSPECTED: claim text contains instruction-like content")
    return reasons


def filter_pack(pack: dict, brief: dict) -> tuple[list[dict], list[dict]]:
    """Split pack claims into (accepted, rejected); rejected copies carry a "reasons" list.

    If there are no claims to annotate, pack/brief errors produce one reasons-only rejection.
    A valid empty pack remains ([], []). Duplicate question IDs reject the entire pack.
    """
    envelope = _schema_errors(_ENVELOPE_VALIDATOR, pack, "PACK_SCHEMA_INVALID")
    if isinstance(pack, dict):
        envelope += _non_finite_errors(pack.get("spend"), "PACK_SCHEMA_INVALID", "spend")
    if isinstance(pack, dict) and pack.get("brief_id") != brief.get("brief_id"):
        envelope.append(f"PACK_BRIEF_MISMATCH: pack is for {pack.get('brief_id')!r}")
    claims = pack.get("claims", []) if isinstance(pack, dict) else []
    claims = claims if isinstance(claims, list) else []
    duplicate_errors = _duplicate_question_errors(brief)
    if duplicate_errors:
        # Never select one of several conflicting policies for the same question.
        reasons = envelope + duplicate_errors
        return [], [
            {**(claim if isinstance(claim, dict) else {"raw": claim}), "reasons": list(reasons)}
            for claim in claims
        ] or [{"reasons": reasons}]
    if not claims:
        return [], [{"reasons": envelope}] if envelope else []
    questions = {q.get("id"): q for q in brief.get("questions", []) if isinstance(q, dict)}
    engines = set(brief.get("engines_allowed", []))
    accepted: list[dict] = []
    rejected: list[dict] = []
    for claim in claims:
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
    claims = pack.get("claims", [])
    costs = {i: c["cost_usd"] for i, c in enumerate(claims) if isinstance(c, dict) and "cost_usd" in c}
    numbers = {
        "month_to_date_usd": month_to_date_usd,
        "spend.usd": spend.get("usd", 0),
        "spend.calls": spend.get("calls", 0),
        "budget.usd_per_brief": per_brief,
        "budget.monthly_cap_usd": monthly_cap,
        **{f"claims[{i}].cost_usd": cost for i, cost in costs.items()},
    }
    invalid = [
        f"BUDGET_NUMBER_INVALID: {name} is {value!r}" for name, value in numbers.items() if not _finite(value)
    ]
    if invalid:
        return invalid  # fail closed: NaN compares False against every limit
    # Under-reported envelope spend must not hide per-claim costs.
    usd = max(float(spend.get("usd", 0)), float(sum(costs.values())))
    calls = int(spend.get("calls", 0))
    call_ceiling = sum(q.get("max_calls", DEFAULT_MAX_CALLS) for q in brief.get("questions", []))
    errors: list[str] = []
    if monthly_cap > OWNER_MONTHLY_CAP_USD:
        errors.append(
            f"BRIEF_CAP_ABOVE_OWNER_LIMIT: ${monthly_cap:.4f} > ${OWNER_MONTHLY_CAP_USD:.4f} owner ceiling"
        )
        monthly_cap = OWNER_MONTHLY_CAP_USD
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
