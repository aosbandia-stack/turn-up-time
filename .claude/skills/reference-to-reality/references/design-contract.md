# Design contract prompts

Use these prompts inside the current project guide. This is not a required second document or a new
schema. Fill only the sections relevant to the change. Keep decisions concrete enough for a builder
who has not seen the original conversation.

## Outcome and references

- User, primary task, target platform/viewport, critical journey and non-goals.
- Current app/branch inspected, retained components and data contracts.
- Approved direction in one sentence and acceptance already provided by the user.
- Reference inventory: source/path, observed or supplied status, trait, ADOPT/ADAPT/REJECT and reason.
- Missing references or interactions and what cannot be concluded from them.
- Asset/font provenance, permitted use, local paths, credits and loading fallback.

## Visual roles

| Role | Decide explicitly |
| --- | --- |
| Type | Display/body/label/number family, size range, weight, line height, wrapping and emphasis |
| Space | Shared edges, gutters, internal versus section spacing, compact versus expressive screens |
| Surface | Background, content surface, floating layer, border/shadow purpose and readable contrast |
| Color | Brand accent and separate semantic status colors; text labels accompany color |
| Imagery | Route assignment when useful, focal point, aspect/crop, scrim and text placement |
| Components | Shared header, nav, cards, lists, inputs, dialogs, owner and reuse location |
| Motion | Triggers, duration/easing, prior-value behavior, interruption and reduced-motion fallback |

Prefer native scrolling and stable geometry. Do not introduce scroll interception or persistent
background animation merely to make the product feel expensive. Use motion to communicate state.

## Behavior and integration

- Each visible control's action and loading/empty/error/success states.
- Which views share a source of truth, which scopes are separate, and what recalculates on mutation.
- Fixture versus real data; date/timezone assumptions; estimate assumptions and units.
- Storage/persistence, existing-data migration, reset/undo boundaries and integration adapter points.
- Keyboard, focus, large text, safe-area and long-content behavior.
- Required proof, permitted tools, candidate/build identity and known verification limitations.

## Example: the approved Adams direction

This is an example, not a universal theme. The user preferred real scenic imagery, a dark calm
background, purple identity, serif headings with a sans-serif reading face, clear financial figures,
and short transitions. Implementation kept the photographs/fonts, made the screen scrollable, wired
interactions to shared demo state, then refined type, spacing, surfaces and motion without changing
the direction. Different routes received distinct real photos with consistent treatment.

The later debt interaction improved utility: card balances, APRs, minimum and planned payments, and
payment history replaced a static illustrative date with an explained estimate. Browser-local data
and simplified forecasts remained explicitly limited. No visual-browser success was claimed when
browser tools were unavailable. Carry forward that fidelity and honesty, not that color palette or
that verification gap.
