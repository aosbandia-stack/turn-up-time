# Architecture

## Conveyor ownership

| Stage | Owner | Input | Output | May edit product? |
|---|---|---|---|---|
| Route/intake | `/turn-up-time` root skill | User ask + repo state | Ledger + Intake Card | No |
| Clarification | `/grill-me` root skill | Human-owned unknowns | Ratified intake | No |
| Discovery | Four research agents | Intake + current state | Evidence packs | No |
| Premise audit | `premise-auditor` | Evidence packs | EVIDENCE_READY/BLOCKED | No |
| Definition/tickets | `/omnidex` + architect | Approved evidence | DoG + architecture + tickets | No |
| Seam review | `integration-lead` | Tickets/contracts | SEAMS_SOUND/BLOCKED | No |
| Build | `/boil-the-ocean` + engineers | Approved tickets | Implemented ticket receipts | Yes, ticket scope only |
| Product closeout | `/easily-irritated` | Build + DoG + journeys | Findings, repairs, verdict | Auditors no; repairers yes |
| Release | `/production-audit` + guard | Release candidate | Release receipt or block | Operational only |
| Workflow closeout | `/its-not-you-its-me` | Project traces | Improvement proposals | No automatic workflow edit |

## Loop map

| Loop | New input required | Exit | Escalate when |
|---|---|---|---|
| Clarification | Human answer | Intake complete | Six questions still leave a material fork |
| Discovery | New source or targeted gap | EVIDENCE_READY | MUST remains conflicted/unknown |
| OmniDex repair | Auditor/seam finding | Tickets approved | Same defect survives one repair |
| Ticket repair | Failing deterministic check | Checks pass | Same failure survives two distinct repairs |
| Integration repair | New integrated build | SEAMS_SOUND | Same seam survives two waves |
| EI audit/repair | Changed build + fresh audit team | Terminal state | Max rounds or decision/environment block |
| Visual polish | New screenshots | Confirmed pass | Second pass still reveals structural problem |
| Workflow improvement | New project evidence | Promote/reject/defer/retire | No measurable benefit or unacceptable ceremony |

## State

The project ledger stores facts, not chat transcripts. Evidence files and tickets are referenced by
path and hash. On resume, compare current repository identity and affected artifact hashes. Rerun only
premises whose substrate changed.

## Capability providers

Provider skills are loaded through `.claude/capabilities/registry.yaml`. A provider is not part of the
constitution. It is an implementation library with a declared stage, input, output, conflicts, eval,
and uninstall path.

## Tier C project workspace

```text
.claude/projects/<project-id>/
  project-ledger.json
  intake-readiness.yaml
  evidence/
    product.yaml
    engineering.yaml        # lite only
    frontend.yaml           # standard/full
    backend.yaml            # standard/full
    security.yaml           # standard/full
    premise-verdict.yaml
  definition-of-good.yaml
  architecture.md
  traceability.yaml
  tickets/
  receipts/
  integration/
  closeout/
  release/
```

The root session is the designated writer for the ledger. Agents return structured output; they do not
race project state. Artifact hashes are recorded in `project-ledger.json` before a stage transition.

## Independent model-review execution

Claude Code supports project/user custom subagents and launching a full session with
`claude --agent <name>`. Print mode (`claude -p`) supports scripted review with budget and turn caps.
The included `scripts/run-fresh-model-review.ps1` uses those mechanics to create a genuinely cold model
pass after the deterministic review.
