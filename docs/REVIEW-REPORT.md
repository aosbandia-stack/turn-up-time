# Fresh review report

Reviewer contract: `.claude/agents/fresh-workflow-reviewer.md`. This automated cold pass reads the final tree rather than the build script.

**Verdict: GREEN — 74/74 checks passed.**

## Checks

- [x] `readme-skill-count` — README matches ten skill directories
- [x] `readme-agent-count` — README matches agent inventory
- [x] `lite-combined-researcher` — lite profile provider exists
- [x] `single-constitution` — CLAUDE.md declares itself canonical
- [x] `owner-route-intake` — architecture names owner row for Route/intake
- [x] `owner-discovery` — architecture names owner row for Discovery
- [x] `owner-definition-tickets` — architecture names owner row for Definition/tickets
- [x] `owner-seam-review` — architecture names owner row for Seam review
- [x] `owner-build` — architecture names owner row for Build
- [x] `owner-product-closeout` — architecture names owner row for Product closeout
- [x] `owner-release` — architecture names owner row for Release
- [x] `owner-workflow-closeout` — architecture names owner row for Workflow closeout
- [x] `readonly-architect` — tools=['Bash', 'Glob', 'Grep', 'Read']
- [x] `readonly-backend-systems-researcher` — tools=['Bash', 'Glob', 'Grep', 'Read', 'WebFetch', 'WebSearch']
- [x] `readonly-combined-engineering-researcher` — tools=['Bash', 'Glob', 'Grep', 'Read', 'WebFetch', 'WebSearch']
- [x] `readonly-fresh-release-judge` — tools=['Bash', 'Glob', 'Grep', 'Read']
- [x] `readonly-fresh-workflow-reviewer` — tools=['Bash', 'Glob', 'Grep', 'Read']
- [x] `readonly-frontend-experience-researcher` — tools=['Bash', 'Glob', 'Grep', 'Read', 'WebFetch', 'WebSearch']
- [x] `readonly-functional-qa` — tools=['Bash', 'Glob', 'Grep', 'Read']
- [x] `readonly-integration-lead` — tools=['Bash', 'Glob', 'Grep', 'Read']
- [x] `readonly-irritated-domain-user` — tools=['Bash', 'Glob', 'Grep', 'Read']
- [x] `readonly-premise-auditor` — tools=['Bash', 'Glob', 'Grep', 'Read', 'WebFetch', 'WebSearch']
- [x] `readonly-product-domain-researcher` — tools=['Bash', 'Glob', 'Grep', 'Read', 'WebFetch', 'WebSearch']
- [x] `readonly-security-performance-reviewer` — tools=['Bash', 'Glob', 'Grep', 'Read']
- [x] `readonly-security-privacy-researcher` — tools=['Bash', 'Glob', 'Grep', 'Read', 'WebFetch', 'WebSearch']
- [x] `readonly-ticket-verifier` — tools=['Bash', 'Glob', 'Grep', 'Read']
- [x] `readonly-triage-lead` — tools=['Bash', 'Glob', 'Grep', 'Read']
- [x] `readonly-ux-accessibility-reviewer` — tools=['Bash', 'Glob', 'Grep', 'Read']
- [x] `router-control-plane` — build work routes to turn-up-time
- [x] `router-no-engineering-loop` — retired router absent
- [x] `router-no-direct-omnidex` — router does not bypass control plane
- [x] `router-no-direct-boil` — router does not bypass control plane
- [x] `loop-turn-up-time-EVIDENCE_BLOCKED` — EVIDENCE_BLOCKED
- [x] `loop-turn-up-time-two materially dif` — two materially different repairs
- [x] `loop-turn-up-time-Two failed repair ` — Two failed repair waves
- [x] `loop-omnidex-Repair once` — Repair once
- [x] `loop-omnidex-stop and reframe` — stop and reframe
- [x] `loop-boil-the-ocean-two materially dif` — two materially different repairs
- [x] `loop-boil-the-ocean-at most two waves` — at most two waves
- [x] `loop-easily-irritated-max_rounds` — max_rounds
- [x] `loop-easily-irritated-Terminal states` — Terminal states
- [x] `loop-its-not-you-its-me-Promote or retire` — Promote or retire
- [x] `cap-frontend-operate-eval` — critical-journey-e2e
- [x] `cap-frontend-operate-uninstall` — remove provider mapping; no product files are deleted
- [x] `cap-frontend-marketing-eval` — visual-and-conversion-contract
- [x] `cap-frontend-marketing-uninstall` — remove provider mapping
- [x] `cap-browser-e2e-eval` — seeded-broken-journey-must-fail
- [x] `cap-browser-e2e-uninstall` — remove provider mapping and project-specific tests only with approval
- [x] `cap-ai-regression-eval` — known-regression-must-fail
- [x] `cap-ai-regression-uninstall` — remove provider mapping; preserve baselines
- [x] `cap-workflow-evals-eval` — grader-control-must-fail
- [x] `cap-workflow-evals-uninstall` — not removable while core workflow is active
- [x] `cap-workflow-evals-provider-present` — eval-harness
- [x] `cap-irreversible-write-eval` — missing-backup-must-block
- [x] `cap-irreversible-write-uninstall` — not removable while auto-accept is enabled
- [x] `cap-irreversible-write-provider-present` — guard-before-write
- [x] `install-dry-run-default` — Apply is opt-in
- [x] `install-backup` — conflicts/settings backed up
- [x] `install-preserve-settings` — settings merged, not replaced
- [x] `install-copies-runtime-scripts` — validator/scaffolder installed
- [x] `install-manifest` — exact installed file list recorded
- [x] `install-notify-preserved` — existing notification implementation is not overwritten
- [x] `scan-github_pat` — no match
- [x] `scan-openai_key` — no match
- [x] `scan-aws` — no match
- [x] `scan-private_key` — no match
- [x] `scan-windows_user` — no match
- [x] `scan-company_domain` — no match
- [x] `relative-links` — all resolved
- [x] `schema-ticket.schema` — valid JSON
- [x] `schema-evidence-pack.schema` — valid JSON
- [x] `schema-improvement-proposal.schema` — valid JSON
- [x] `schema-finding.schema` — valid JSON
- [x] `schema-project-ledger.schema` — valid JSON

## Limits

- PowerShell parser and behavior checks require Windows PowerShell 5.1; the included GitHub Actions workflow runs them on `windows-latest`.
- This deterministic pass is not a substitute for a separate model reviewing design judgment. The repository includes a read-only fresh reviewer agent for that cold model pass.
- External capability providers are intentionally not vendored and must be evaluated through `/plug-it-in` before activation.
