# Research-scout project pilot

Project-only pilot for improvement
[`IMP-RESEARCH-SCOUT-20261010`](../../.claude/improvement-queue/IMP-RESEARCH-SCOUT-20261010.json).
It adds a read-only `research-scout` assurance agent that answers an owner-approved Research Brief
with cited evidence, using the host's built-in web search first and Perplexity only within the
brief's engines and budget.

Nothing here changes `CLAUDE.md`, the topology, core skills, agents, schemas, hooks or the bundled
capability registry. Premise-auditor remains the only evidence verdict.

## Contract

Perplexity may not research until:

1. the `/grill-me` intake is `READY` or `READY_WITH_DEFERRED_RISK`;
2. the base bot (Claude) writes a Research Brief from it, pinning the intake file's sha256;
3. the owner approves the brief (`status: APPROVED`, `approved_by`, `approved_at`).

The scout then runs only against that brief. Each question has one job:

| Job | Purpose |
|---|---|
| Reuse | existing software and reusable components (claims need `license` and `last_release`) |
| Compare | technical approaches |
| Study | similar apps and user flows; feeds the REA brief |
| Need | must-have versus nice-to-have evidence; the owner decides |

## Files

| File | Purpose |
|---|---|
| `research-brief.schema.json` | brief shape (draft 2020-12) |
| `research-pack.schema.json` | scout output shape; every claim records the engine used |
| `guard.py` | offline checks the root runs: `gate`, `scrub_query`, `filter_pack`, `budget_errors` |
| `research-scout.md` | subagent definition to copy into the pilot project's `.claude/agents/` |
| `examples/notes-app-brief.json` | DRAFT example brief (notes app with a quick-note widget) |

Seeded evals live in `runtime/tests/test_research_scout_pilot.py`.

## Install into a pilot project

1. Copy `research-scout.md` to `<pilot-project>/.claude/agents/research-scout.md`.
2. Copy `guard.py`, both schemas and `examples/` to `<pilot-project>/.claude/research-scout/`.
   `guard.py` loads the schemas from its own directory. It needs Python 3.11+ and `jsonschema`.
3. Set `PERPLEXITY_API_KEY` in the environment that launches Claude Code. Never write the key into
   a project file. The owner-approved spend control is prepaid credit with auto-reload off, capped
   at $50 per month; `budget.monthly_cap_usd` in a brief is the pilot's own lower ceiling.
4. Trust the pilot project folder. Claude Code skips inline MCP servers from a project
   `.claude/agents/` file until the folder is trusted.
5. Restart Claude Code if `.claude/agents/` did not exist when the session started, then confirm the
   `perplexity` server and its four tools appear for the subagent.

### MCP server syntax

The agent file declares the Perplexity server inline in frontmatter. The official subagent docs
(<https://code.claude.com/docs/en/sub-agents>, "Scope MCP servers to a subagent", checked
2026-10-10) define `mcpServers` as a list whose entries are either a configured server name or an
inline definition keyed by server name that "use[s] the same schema as `.mcp.json` server entries".
The frontmatter therefore uses:

```yaml
mcpServers:
  - perplexity:
      type: stdio
      command: npx
      args: ["-y", "@perplexity-ai/mcp-server@1.3.0"]
      env:
        PERPLEXITY_API_KEY: "${PERPLEXITY_API_KEY}"
```

`${VAR}` expansion is documented for `.mcp.json` (<https://code.claude.com/docs/en/mcp>,
"Environment variable expansion in `.mcp.json`"). The subagent page does not state explicitly that
the same expansion runs inside agent frontmatter. Verify it during install: if the server starts but
every call fails authentication, the variable was not expanded. In that case remove the inline entry,
add the same server to the pilot project's `.mcp.json` (where expansion is documented), and replace
the inline entry with the string reference `- perplexity`. Package version 1.3.0 is pinned and
exposes `perplexity_search`, `perplexity_ask`, `perplexity_reason` and `perplexity_research`
(npm registry metadata, checked 2026-10-10, MIT licence).

## How the root session uses the guard

```python
import hashlib, json, importlib.util
spec = importlib.util.spec_from_file_location("guard", ".claude/research-scout/guard.py")
guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)

intake_bytes = open(intake_path, "rb").read()
errors = guard.gate(brief, json.loads(intake_bytes), intake_bytes, {"owner"})
if errors:
    stop(errors)                      # no research; every code starts e.g. "BRIEF_NOT_APPROVED: "
for question in brief["questions"]:
    assert guard.scrub_query(question["question"], brief["off_limits"]) == []
# ... spawn research-scout with the brief path; it returns a pack as JSON ...
accepted, rejected = guard.filter_pack(pack, brief)
spend_errors = guard.budget_errors(pack, brief, month_to_date_usd)
```

Only `accepted` claims go to premise-auditor. `rejected` claims keep their `reasons` for the record.
A non-empty `spend_errors` stops further scout spawns for the brief and goes to the owner.

| Function | Refuses or rejects with |
|---|---|
| `gate` | `BRIEF_SCHEMA_INVALID`, `BRIEF_NOT_APPROVED`, `BRIEF_APPROVER_UNTRUSTED`, `BRIEF_APPROVAL_TIME_INVALID`, `INTAKE_NOT_READY`, `INTAKE_HASH_MISMATCH` |
| `scrub_query` | `SECRET_*` (API key, GitHub, AWS, Slack, JWT, private key), `PRIVATE_*` (email, Windows path, home path, GitHub repo URL, phone), `OFF_LIMITS_TERM`, `QUERY_TOO_LONG`, `QUERY_INVALID` |
| `filter_pack` | `PACK_SCHEMA_INVALID`, `PACK_BRIEF_MISMATCH`, `CLAIM_SCHEMA_INVALID`, `UNKNOWN_QUESTION`, `SOURCE_QUOTE_MISSING`, `SOURCE_NOT_HTTPS`, `NO_SOURCES`, `REUSE_PROVENANCE_MISSING`, `ENGINE_NOT_ALLOWED`, `DEEP_RESEARCH_NOT_ALLOWED`, `INJECTION_SUSPECTED` |
| `budget_errors` | `BUDGET_PER_BRIEF_EXCEEDED`, `BUDGET_CALLS_EXCEEDED`, `BUDGET_MONTHLY_CAP_EXCEEDED`, `MONTH_TO_DATE_INVALID` |

The scout has no Edit or Write tool. It returns the pack in its final report and the root writes it.

## Limitations

- The guard is offline. It cannot prove a URL exists or that a quote really appears at the URL;
  that stays premise-auditor's job, preferably a different model family from the scout.
- `scrub_query` is pattern-based. It blocks the listed shapes; it cannot recognise every private
  fact, so `off_limits` must name project codenames and people.
- Prompt-injection detection is a marker list. It catches the common phrasings and treats all
  results as data; it is not a complete defence.
- The call ceiling is pack-wide (`spend.calls` at most the sum of `max_calls`), because a pack does
  not record calls per question.
- `budget_errors` trusts the month-to-date figure the root supplies. The hard cap is the prepaid
  credit.

## Measurement plan (from the proposal)

Per pilot project, until the 2026-11-10 review:

- named UNKNOWN MUST claims entering gap mode versus leaving SUPPORTED or CONFLICTED;
- citation validity rate judged by premise-auditor (URL exists, quote present, supports the claim,
  applies);
- spawns and wall time spent on discovery repeats, compared with the bandia-project-conversations
  baseline;
- count of auditor rejections of scout claims.

The record goes back to `/its-not-you-its-me` for promote, reject, defer or retire.

## Rollback

Delete the pilot project's `.claude/agents/research-scout.md` and `.claude/research-scout/`, and the
project `.mcp.json` entry if one was added. In this repository, delete `pilots/research-scout/` and
`runtime/tests/test_research_scout_pilot.py`. No global file changes need reverting.
