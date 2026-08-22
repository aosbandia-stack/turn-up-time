# Agent compatibility instructions

This file is a compatibility adapter for tools that read `AGENTS.md`. The canonical operating contract
is `CLAUDE.md`; stage procedures live in `.claude/skills/`; role authority lives in agent frontmatter;
and machine state lives in `.claude/projects/<project-id>/project-ledger.json`.

Do not apply generic plan-first, fixed-coverage, default-TDD, automatic fan-out, or unlimited review
loops unless an approved requirement/ticket explicitly needs them.

Route software work through `/turn-up-time`. Use the smallest valid tier, resolve capabilities through
the registry, preserve separation of duties, require schema/transition validation for Tier C, and run
`/guard-before-write` before consequential actions.
