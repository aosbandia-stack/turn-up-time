#!/usr/bin/env python3
"""OWNER-ONLY utility. Run outside the worker's OS account/container.

A private key is never installed in the runtime. Read and inspect the request
before signing it. A signature approves only the exact request, not deployment
of later or different code. The trusted owner configures the public trust file.
"""
from __future__ import annotations

import argparse
import base64
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--key-id", required=True)
    parser.add_argument("--approver", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lifetime-minutes", type=int, default=60)
    args = parser.parse_args()
    if not 1 <= args.lifetime_minutes <= 1440:
        parser.error("approval lifetime must be between 1 and 1440 minutes")
    request = json.loads(args.request.read_text(encoding="utf-8-sig"))
    if request.get("approved_by") != args.approver or not request.get("event_id"):
        parser.error("request must name this approver and a stable event ID")
    key = serialization.load_pem_private_key(args.private_key.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        parser.error("an Ed25519 private key is required")
    now = datetime.now(timezone.utc)
    approval_id = str(uuid.uuid4())
    statement = {"approval_id": approval_id, "approver": args.approver, "request": request,
                 "issued_at": now.isoformat(), "expires_at": (now + timedelta(minutes=args.lifetime_minutes)).isoformat()}
    content = json.dumps(statement, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    envelope = {"key_id": args.key_id, "approval_id": approval_id, "statement": statement,
                "signature": base64.b64encode(key.sign(content)).decode("ascii")}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Never silently replace an existing approval.
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(envelope, handle, indent=2)
        handle.write("\n")
    print(f"Signed exact request {request['event_id']} -> {args.output}")


if __name__ == "__main__":
    main()
