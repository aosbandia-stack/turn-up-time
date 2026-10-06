"""Shared local evidence checks. Hashes prove file integrity, not reviewer honesty."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

SCHEMAS = Path(__file__).resolve().parents[1] / 'schemas'


def read_contract(path: Path, schema_name: str, errors: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        schema = json.loads((SCHEMAS / schema_name).read_text(encoding='utf-8'))
        failures = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value), key=lambda e: str(list(e.path)))
        for failure in failures:
            errors.append(f'INVALID {path}:{".".join(map(str, failure.path)) or "<root>"}: {failure.message}')
        return value if not failures else None
    except (OSError, ValueError) as exc:
        errors.append(f'UNREADABLE {path}: {exc}')
        return None


def local_path(project: Path, reference: str, errors: list[str]) -> Path | None:
    if not isinstance(reference, str) or not reference.strip():
        errors.append('EVIDENCE_REFERENCE_REQUIRED')
        return None
    relative = PurePosixPath(reference)
    if relative.is_absolute() or '..' in relative.parts or "\\" in reference or ':' in reference:
        errors.append(f'EVIDENCE_OUTSIDE_PROJECT unsafe portable path: {reference}')
        return None
    path = (project / reference).resolve()
    if Path(reference).is_absolute() or not path.is_relative_to(project.resolve()):
        errors.append(f'EVIDENCE_OUTSIDE_PROJECT {reference}')
        return None
    if not path.is_file():
        errors.append(f'MISSING_EVIDENCE {reference}')
        return None
    return path


def check_assets(project: Path, references: list[dict[str, str]], errors: list[str]) -> None:
    for reference in references:
        path = local_path(project, reference['path'], errors)
        if path and hashlib.sha256(path.read_bytes()).hexdigest() != reference['sha256']:
            errors.append(f'EVIDENCE_HASH_MISMATCH {reference["path"]}')


def timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timezone required')
    return parsed


def check_identity(value: dict[str, Any], project: Path, build: str | None, errors: list[str], label: str) -> None:
    if value.get('project_id') != project.name:
        errors.append(f'PROJECT_ID_MISMATCH {label}')
    if not build or value.get('build_identity') != build:
        errors.append(f'BUILD_IDENTITY_MISMATCH {label}')
    if value.get('checked_at') and timestamp(value['checked_at']) > datetime.now(timezone.utc):
        errors.append(f'FUTURE_EVIDENCE {label}')


def check_proof(project: Path, reference: str, build: str | None, errors: list[str], check_id: str | None = None) -> dict[str, Any] | None:
    path = local_path(project, reference, errors)
    if not path:
        return None
    proof = read_contract(path, 'verification-receipt.schema.json', errors)
    if proof:
        check_identity(proof, project, build, errors, reference)
        if proof['status'] != 'PASS':
            errors.append(f'FAILED_EVIDENCE {reference}')
        if check_id and proof['check_id'] != check_id:
            errors.append(f'CHECK_ID_MISMATCH {reference} expected={check_id}')
        check_assets(project, proof['evidence_refs'], errors)
    return proof
