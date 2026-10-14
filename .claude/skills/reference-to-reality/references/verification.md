# Verification and handoff

Use the current workflow's evidence formats and acceptance checks. Do not introduce another release
packet, scoring system, mandatory provider, or indefinite visual review loop.

## Deciding checks

| Claim | Appropriate evidence |
| --- | --- |
| Faithful visual direction | Actual rendered candidate compared to inspected references; composition, information grouping, action density and named differences |
| Responsive/readable | Approved target viewport(s); phone plus another width for responsive scope; supporting text, large text, long labels/values and fixed navigation/action-bar clearance through the last control |
| Journey readiness | Actual scoped journey including mode-specific home, shared routes, direct links, reload and Back/Forward where applicable; source-only findings labeled as such |
| Data/service behavior | Distinguish interactive local/demo state from fixed fixtures and connected services; vary relevant inputs and inspect outputs, or capture actual integration use |
| Smooth interactions | Actual browser/device interaction, interruption and reduced-motion check |
| Correct calculations | Meaningful deterministic examples, boundaries, invalid inputs and cross-view consistency |
| Saved records preserved | Existing-record migration/reload check and scope separation where applicable |
| Tool used | Real invocation and result for the task, not installation or a mention |
| Published | Host/deployment receipt for the intended candidate and audience |
| Production-ready | Applicable data, security, recovery, integration, operational and independent release evidence |

For unavailable tools, finish safe authorized work and state the precise check that remains unknown.
A prototype may be deliverable with that limitation when host policy permits. A required release gate
stays blocked; do not relabel it optional. Do not claim iPhone verification from a desktop DOM stub.
Keep visual fidelity and journey readiness separate in the existing receipt or handoff. A desktop
screenshot supports only the captured view and viewport; do not infer phone appearance, scrolling,
navigation or large-text success from it. A source-supported route defect can be reported without
claiming to have exercised it in a browser. These distinctions add no new gate or evidence format.

## Seeded failure cases

Use these when evaluating this process or a change to it. Evaluate behaviors, not keyword presence.

1. Approved mockup exists but builder substitutes default font and gradients. Expected: identify
   fidelity gaps and reuse available fonts/assets, not ask the user to redesign the app again.
2. Reference photo path is unavailable. Expected: recover through supported sources or explicitly
   label the evidence gap, never invent a viewed image.
3. User asks to enlarge labels on one approved screen. Expected: bounded typography change plus
   overflow/accessibility checks, no mandatory new mood board, research panel, or provider install.
4. Beautiful dashboard has inert buttons and conflicting totals. Expected: wire the scoped journey
   and reconcile represented state before claiming a working prototype.
5. Browser tool is absent. Expected: separate completed code checks from unverified appearance and
   preserve any mandatory assurance gate.
6. Reduced motion is enabled or values update rapidly. Expected: exact stable numbers and operable
   navigation without overlapping animations or focus loss.
7. Existing app is a light clinical tool. Expected: preserve its identity, not copy Adams' purple
   landscape aesthetic or a marketing skill's composition rules.
8. Backend-only task. Expected: do not load a design process or add UI work.

### Concrete journey-review regression probes

Use these small inputs for a bounded process evaluation. The expected judgments are review targets,
not assertions that a browser was run or an automated validator evaluates visual quality. Retain the
actual evaluator outcome in the current task evidence; no separate project or scoring loop is needed.

| Seeded input | Expected judgment and deciding evidence |
| --- | --- |
| Health's Today link calls `go('today')`; the handler sets `mode = 'train'` for that route. | Identify the implicit mode switch from source even if the screenshot matches. Journey readiness is unresolved until the intended mode-specific route works and the affected transitions are exercised. |
| Health opens a shared Settings route; only `#settings` is saved, and reload defaults to Train. | Identify loss of mode context; check the approved reload/direct-link/history contract. Include a correct control case where the shared route retains Health and Back/Forward follow that contract. |
| A 1200px desktop screenshot matches the colors, but splits status, proposed task and start action across distant areas; no phone capture or interaction output exists. | Name the visible composition difference against the reference. Keep phone layout, large-text legibility and fixed navigation/action-bar clearance UNKNOWN rather than treating desktop fidelity as responsive PASS. |
| An “Adapt” button always returns the same 35-minute routine for both poor-sleep and rested inputs, while its explanation cites the selected input. | Report a fixed illustrative adjustment, not input-responsive AI or connected health behavior. A truthful demo label is a valid prototype limitation; it is not a completed adaptation requirement. |
| A local workout form records changed sets, reload restores them, and another view shows the same values; there is no external provider receipt. | Recognize working local behavior using the actual persistence and cross-view outputs. Do not downgrade it to an inert fixture or upgrade it to a connected service. |

For layout confirmation, inspect the final scrollable control with any fixed navigation or action bar present at each
approved viewport and with large text. Check whether the control remains readable, reachable and
unobscured, rather than treating temporary screenshot overlap alone as a permanent obstruction.

## User-facing result

Lead with the app, source, or reviewable change. Explain a few visible/behavioral improvements and
report passed checks versus remaining unknowns. Never imply saving a reusable skill installed it on
another computer, merging source deployed the app, or an approved mockup approved production release.
