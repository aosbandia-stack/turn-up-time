"""Strict local contracts for triage and gauntlet components; never grant authority."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path, PurePosixPath
from jsonschema import Draft202012Validator, FormatChecker

SCHEMAS = Path(__file__).resolve().parents[1] / 'schemas'
LIMIT = 2 * 1024 * 1024

def strict_json(raw: bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('DUPLICATE_JSON_KEY ' + key)
            result[key] = value
        return result
    if len(raw) > LIMIT:
        raise ValueError('DOCUMENT_TOO_LARGE')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))

def validate(value, schema):
    document = strict_json((SCHEMAS / schema).read_bytes())
    errors = list(Draft202012Validator(document, format_checker=FormatChecker()).iter_errors(value))
    if errors:
        raise ValueError('SCHEMA_INVALID ' + '; '.join(e.message for e in errors[:5]))
    return value

def confined(root: Path, name: str) -> Path:
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name or str(p) != name:
        raise ValueError('UNSAFE_PATH ' + name)
    target = root.resolve()
    for part in p.parts:
        target = target / part
        if target.is_symlink() or (hasattr(target, 'is_junction') and target.is_junction()):
            raise ValueError('LINK_PATH ' + name)
    if not target.resolve().is_relative_to(root.resolve()) or not target.is_file():
        raise ValueError('MISSING_OR_ESCAPING_PATH ' + name)
    return target

def read(root: Path, reference: dict, schema: str | None = None):
    path = confined(root, reference['path'])
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != reference['sha256']:
        raise ValueError('HASH_MISMATCH ' + reference['path'])
    value = strict_json(raw)
    return validate(value, schema) if schema else value

def assets(root: Path, references: list):
    seen = set()
    for ref in references:
        if ref['path'].casefold() in seen:
            raise ValueError('DUPLICATE_ASSET ' + ref['path'])
        seen.add(ref['path'].casefold())
        if hashlib.sha256(confined(root, ref['path']).read_bytes()).hexdigest() != ref['sha256']:
            raise ValueError('HASH_MISMATCH ' + ref['path'])

def unique(values, label):
    if len(values) != len(set(values)):
        raise ValueError('DUPLICATE_' + label)
