# Optional provider routing

Select capabilities for the approved job, not entire upstream workflows. This reference is the
provider-specific adaptation layer; the constitution, stage owners, budgets and evidence contracts
remain authoritative. Mappings in `registry.json` are pinned provenance, not installation, invocation
or approval. None of these packages or upstream hooks is bundled. Unselected mappings do not block;
a selected missing provider blocks its work and routes to `/plug-it-in`.

## Selection and ownership

| Signal | Capability / provider | Consumer and boundary |
| --- | --- | --- |
| Material executive overview where relationships clarify the decision | `executive-diagram` / diagram-design | Root presents a small evidence-backed diagram; no new control authority |
| Focused security question or small scoped analysis | `security-guidance` / security-audit | Existing assurance role reads relevant guidance; no claim that a full audit ran |
| Requested full security audit, or material auth, trust-boundary or sensitive-data changes needing full audit | `security-audit` / security-audit | Root/architect adds it to approved tickets; independent assurance performs the bounded audit before INTEGRATION |
| Approved ticket benefits from vertical increments | `engineering-increments` / incremental-implementation | Builder uses small testable changes inside ticket scope |
| Behavior change or defect needs a meaningful regression check | `engineering-tdd` / test-driven-development | Builder proves the behavior fails before repair, then passes; no blanket TDD requirement |
| Observed failure needs diagnosis | `engineering-debugging` / debugging-and-error-recovery | Builder collects reproduction and evidence, then makes a bounded repair |
| Existing approved code needs clearer structure without behavior changes | `engineering-simplification` / code-simplification | Builder simplifies only owned scope; cleanup capstone remains Swiper |

At intake/definition, resolve the required audit scope and budget and record capability selections
in each affected ticket's `required_capabilities`. A requested full audit cannot silently become
focused guidance. When scope is already authorized, proceed within it; ask only for a material
unresolved product, cost, execution or data boundary. Tier B uses the same capability resolver without
inventing a Tier C project. Conditional triggers are agent instructions, not an automatic file-change
classifier. An independent reviewer checks that the selected audit depth matches the actual change.

Resolve selected capabilities just in time. For instruction providers, load the installed SKILL.md
and needed supporting references, record the path/version in existing task evidence and apply these
adaptations. Readability alone does not prove those instructions were followed. External audit use
also needs current readiness and actual invocation/output proof. The existing resolver enforces
presence, dependency closure, declared readiness checks, asset hashes and usage context; it does not
certify the truth of a PASS flag, instruction semantics, upstream version or audit completeness.

## Executive visuals and UI

Use diagram-design for one decision, a compact architecture relationship or a meaningful progress
view. Reuse the approved diagram profile and design tokens without repeating onboarding. Default to
self-contained output and system fonts. Prefer editable SVG or a host-native diagram; HTML is optional.
Keep text readable on a phone,
labels concise, contrast accessible and status explicit. Provide an equivalent concise text/table
fallback when rendering fails, rather than adding a renderer or network dependency. Never add fake
approval controls or show invented live progress. Simple fixes remain short text.

Impeccable stays the default product UI design baseline. Its optional polish and 21st catalog/generation
flags remain unchanged, with their existing readiness, stack and use requirements. Diagram styling
does not override the product's approved design guide or cross-page component system. Provider
examples and generated output are illustrative until the actual app is exercised.

## Bounded security audit

The full-audit mapping is **external** even though it uses the same installed `security-audit`
instructions as focused guidance. This marks execution/evidence obligations, not a bundled scanner
or new daemon. An assurance worker is dispatched through the existing execution host and role rules;
Turn Up Time's graph alone does not launch it. No scheduled or background scan is created.

Before dispatch, collect short-lived project/environment readiness with these checks and hashed
supporting evidence in the existing `capability-readiness.json`:

- `audit_scope`: exact source/candidate, attack surfaces, exclusions and source-only versus execution
  mode are explicit; unknown/uncovered areas remain visible.
- `audit_budget`: bounded time/cost, worker ceiling, stop conditions and cancellation owner are set;
  upstream fan-out must fit the existing whole-project budget.
- `independent_review`: audit and finding-validation roles are separate from builders; no self-certification.
- `isolated_output`: reports, temporary artifacts and any proposed PoCs have an authorized output
  location isolated from product source, protected control files, credentials and live data.
- `audit_validators`: required upstream findings/coverage validators and their runtime are available
  from the inspected pin; a readiness smoke is distinct from validation of the actual audit outputs.
- `execution_policy`: source-only review is allowed without target execution; target builds, tests,
  PoCs or exploit execution require real OS-enforced isolation with external networking disabled, a
  sanitized allowlisted environment, resource limits and explicit write/operation limits, as required
  by the upstream target sandbox policy. A worktree, tool label, path convention or claimed PASS is
  not isolation.

Without the needed execution boundary, prohibit target execution. Perform only authorized source
analysis if it meets the agreed scope, labeling dynamic checks unavailable; otherwise block that
scope. Never install hooks, run repository setup scripts or upload code/findings by inference.

During BUILD, the existing independent assurance role follows the upstream audit phases within the
approved budget, records coverage and uncertainty, and validates actual reports using the inspected
upstream validators. It may write reports only through the authorized evidence-output channel, never
repair product code or change control state. A host unable to separate evidence output from protected
writes is not ready. Findings return to the owning builder as repair work, with independent recheck.

Capture invocation and output assets for `security-audit` in the existing usage receipt, tied to the
current assembled candidate. INTEGRATION requires that actual-use proof, not just a successful smoke
probe. Production Audit reviews finding disposition, coverage and validator results on the final
candidate. Source changes after the audit require refreshed affected security checks and current
usage evidence before re-entering INTEGRATION/release. Do not merely relabel an old report with a new
build ID. A clean report does not replace the final judge, accepted-risk owner or release authority.

## Engineering adaptations for Boil

Load only the selected four Addy skills, not `using-agent-skills`, its broad orchestration, hooks or
agent fleet. Existing architecture/tickets own planning; Boil owns dispatch; independent verifiers
own acceptance. Supplementary shared references must be present and inspected at provider intake,
preserving their relative layout or using an explicitly reviewed adapter. Do not silently follow
references into competing planning/shipping workflows.

Use meaningful behavior tests where they address risk. Do not require red/green ceremony for prose,
cosmetic or mechanically verified changes. Upstream per-task commits, separate-PR preferences and
fixed task-size rules are guidance only: the approved ticket, owned files, repository conventions,
whole-project budget and guard determine the actual change boundary. Builders report their checks
but cannot certify their own acceptance. Two materially different failed repairs still escalate.

## Intake, pins and removal

Registry provenance links pin the inspected upstream commits. `/plug-it-in` verifies installed bytes
against those revisions, records file hashes and needed shared references, and checks license,
dependencies, execution permissions and removal before enabling a project pilot. The resolver does
not automatically verify upstream pins or supplementary files; independent intake review does.

- diagram-design: `137b17e0dd611528dfbad44bcac0efadcb30775f`, MIT.
- security-audit-skill: `c1c8a8c1471069fb0e188eeaff69b8e8db6564a8`, MIT.
- agent-skills: `1401c8b8030e023baeebb31781a6653fe8e93026`, MIT.

Keep upstream packages outside core, do not enable auto-update/hooks, and preserve any required
license notices with approved copied material. Removal drops optional mappings/installation using
the existing guard and hash-safe preservation rules; never delete product files or audit evidence.
REA, Serena, Context7 and selected backend/database specialist profiles remain separate follow-on
integration work; this routing change neither installs them nor changes Bandia's worker adapter.
