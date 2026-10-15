# Changelog

## Unreleased

- Add a narrow, fully backed-up ledger-v2 risk-severity migration and preserve WITHDRAWN decisions
  as explicitly non-authoritative history.
- Add audited owner-approved spawn ceiling amendments without refunding consumed work or granting
  stage approval; preserve normal journal idempotence, locking and recovery.
- Reject checkpoint resumes bound to a different workspace before any graph node runs.

## 1.0.0

- Added the official LangGraph stage topology.
- Added human interrupts, bounded loops, SQLite checkpoints, ledger alignment, and append-only events.
- Added install/uninstall ownership and Windows PowerShell 5.1 support.
