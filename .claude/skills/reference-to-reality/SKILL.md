---
name: reference-to-reality
description: Turn app screenshots, approved mockups, and product references into polished working interfaces without losing their visual direction. Use for new app UI, material redesigns, or requests to make an implementation match a concept, feel more premium, improve typography, spacing or motion, or preserve an approved design during refinement. Reuse the current guide for small changes; skip backend-only work. Works with an existing stack and design system; does not replace project orchestration or release gates.
---

# Reference to Reality

Deliver the approved experience in working code. Treat visual fidelity, functional states, and truthful
verification as one job. A pleasing screenshot is a reference, not a completed app.

## Authority and scope

- Follow the current repository/workflow and your assigned role. In Turn Up Time, enter through
  `/turn-up-time`; this is UI craft guidance inside its existing stages, not another controller.
  Keep the registry-resolved provider plan and project guide authoritative; Impeccable remains
  TUT's default baseline, subject to authorized project overrides.
- Carry forward the user's accepted choices. Do not ask them to approve the same direction again.
  Ask only when a material product/design decision remains unresolved; do reversible preparation first.
- Scale the process: a small typography or motion edit reuses the guide and runs affected checks.
  A new app or material redesign needs the full reference-to-first-journey sequence.
- Preserve the stack, real data contracts, ownership, and installed components. Do not turn a UI
  polish request into authentication, bank sync, AI, or an architecture rewrite.

## 1. Inspect what is real

Read current source, routes, styling, fonts, assets, and data/state boundaries before prescribing.
Inspect the actual supplied images or current app when available. Recover missing files from the
supported source; if unavailable, identify the missing evidence and continue with usable references.
Never claim to have inspected a screenshot, repo, external tool output, or browser you could not access.

Separate three things in the existing task record:
- **Keep:** approved identity, visual choices, working behavior, and integration contracts.
- **Improve:** concrete visible or code-supported weaknesses, with the evidence kind identified.
- **Unknown:** unavailable screens, states, device behavior, and assumptions needing validation.

Use at most three relevant reference products for a new direction. Study composition and behavior,
not just colors. Reference-app analysis may explain visible interaction patterns; it cannot establish
private algorithms, hardware protocols, or the user's needs from screenshots.

## 2. Translate references into an implementation contract

Distinguish the brief: for a requested clone, reproduce the observable reference closely within the
approved scope. For an original app, use references to establish its own identity, then sharpen the
working result rather than copying a single product. In either case, preserve accepted decisions;
refinement should improve the direction, not reset it.

Create or update one authoritative project design guide. Under TUT use the existing
`ui.design_reference`, its approved reference evidence and shared component ownership, not a second
competing specification. For a narrow edit append only the relevant decision.

Use [the guide prompts](references/design-contract.md) to capture:
- the primary user task and one critical journey;
- exact reference assets and which traits are adopted, adapted, or rejected;
- typography roles, spacing rhythm, surface hierarchy, imagery crops/scrims, and shared components;
- responsive composition, which information and primary action appear together, states, accessibility,
  and motion; preserve useful action density when adapting a phone reference to a wider screen;
- demo versus live data, integration seams, and an observable finish line.

Specify what makes this app distinctive in one sentence. Avoid adjectives without implementation
consequences: replace “premium” with decisions such as readable editorial headings, aligned figures,
restrained surface contrast, intentional photography, and fewer competing accents.

Use photos only when they serve the approved direction. If real photography is requested, retrieve
and inspect real images, verify permitted use, save permitted assets locally, and retain attribution.
Do not substitute generated imagery or unrelated filler. Give routes distinct imagery only when
requested or justified, with a consistent treatment and contrast. Do not hard-code Adams' purple,
landscapes, dark mode, serif type, or floating navigation into unrelated apps.

## 3. Build one complete vertical journey

Implement the first meaningful screen and its primary interaction before expanding all routes.
Make it scrollable and usable at the target device size. Reuse actual fonts/assets and intentional
image crops; do not approximate the reference with generic gradients or default system typography.

Use coherent, labeled fixture data when building a prototype. Connect all views that claim to share
a measure. Preserve saved records across revisions. Show empty, invalid, success, and recovery states.
A visible control must work, have a real destination, or explicitly explain why unavailable.
Separate fixture dates, estimates and illustrative goals from real calculations. Never make a fixed
promise look like a calculated date or a browser-local record look like synchronized household data.

For apps with modes or workspaces, keep mode, route and shared state consistent. Define what each
mode's Home/Today means, how shared routes retain their originating mode, and the intended behavior
of direct links, reload, and Back/Forward. Exercise those transitions within the scoped journey;
an intentional mode switch must be explicit rather than a side effect of a shared route name.
Distinguish interactive local/demo behavior, fixed illustrative outputs, and connected services.
A working button does not prove a recommendation responds to its inputs or that an external service
was used. Verify those claims with input/output or actual integration evidence, as applicable.

Before route fanout, verify the first journey with the approved browser/native tool when available.
If verification is blocked, record the exact missing capability and do not claim it passed. Under TUT,
required assurance remains a gate: code checks or a user's visual preference do not replace it.

## 4. Refine in an intentional order

Use one batched refinement pass and at most one confirmation by default. Keep any tighter existing
budget; use a longer design loop only through the project's approved mechanism.

1. **Hierarchy and space:** make the main answer obvious, align related content, remove redundant
   containers, reduce oversized working-screen headers, and leave enough space for reading and touch.
   Compare the reference's information grouping and distance to the primary action, not only its
   palette. Wider layouts should not scatter one decision across unrelated areas.
2. **Typography:** usually two complementary families at most; use distinct display, body, label,
   and number roles. Keep supporting text readable, use tabular figures for money, test long values,
   large text and wrap behavior. On mobile web, use 16px form inputs where appropriate to avoid zoom.
3. **Surfaces and imagery:** preserve the approved identity; quiet repeated gradients, glows and
   borders so the key content and photography carry the design. Maintain contrast across every crop.
4. **Interaction and motion:** retain native scrolling. Use short transform/opacity transitions,
   persistent navigation highlights, reliable dialog focus, and clear pressed/focus feedback.
   Respect reduced motion; never hide essential content until an animation completes.
5. **Detail and utility:** add information that helps a decision, not decorative metrics or filler.
   Explain what totals include, what an action changes, and what remains an estimate.

For count-up/down requests, animate changes from the previous value to the new value briefly, then
settle on the exact formatted result. Keep canonical values in state, not animated DOM text. Do not
replay from zero on every navigation, animate errors, spam screen readers with frame updates, or
animate under reduced motion. Rapid updates must cancel/replace old animations cleanly.

Use Taste's existing-project redesign guidance selectively when requested/available. Do not apply
its marketing-page rules blindly to app screens. Stitch may supply concepts, REA may supply observed
reference behavior, and component tools may supply pieces. None replaces the approved guide, working
implementation, or independent assurance. Installation, availability, and actual use are separate facts;
do not install tools, trigger paid calls, or export private designs without applicable authorization.

## 5. Verify against the actual direction

Compare rendered output with the reference at the approved target viewport(s). For responsive UI,
include a phone size and another relevant width; do not add mobile support to desktop-only scope.
Use the existing project's permitted browser/native tooling. Check font loading, image crops,
contrast, text scaling, long labels and amounts, safe areas, fixed navigation/action-bar clearance, keyboard and
focus behavior, scrolling, reduced motion, and the critical journey's success/error states.

Capture deciding evidence and concrete differences, then fix the highest-impact ones within budget.
Report visual fidelity and journey readiness separately in existing evidence. A matching screenshot
can support composition at its captured viewport; it cannot prove navigation, responsive behavior,
or mobile readability. A passing interaction check cannot establish visual fidelity either.
Do not assign a visual score from source code. Source/DOM-stub checks are useful but do not prove
rendering or on-device behavior. Read [verification and handoff](references/verification.md) before
claiming completion. Keep independent evaluation when the governing workflow requires it.

## 6. Deliver and preserve

Use the host/repository's authorized save, review, and publication path. Keep a working app and its
integration-ready source, real assets/fonts, fixtures, and concise instructions when requested.
Preserve the design guide so the next agent can continue without reconstructing the look from prose.

Report the usable deliverable first, the meaningful changes, checks actually passed, and remaining
limitations. Distinguish designed, implemented, tested, saved, merged, installed, and live. An attractive
prototype is not production readiness. When asked about release, prioritize connected data, persistence,
real dates, recovery and device verification before additional polish; defer unrelated features.
