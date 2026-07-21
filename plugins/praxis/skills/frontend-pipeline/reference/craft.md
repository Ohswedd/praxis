# Craft — the difference between compliant and designed

The playbook makes an interface *correct*: tokens, states, contrast, semantics,
budgets. Correct is not the same as good. An interface can satisfy every rule in
§9 and still look like it was generated — because the rules constrain the
mistakes, they do not supply the judgement.

This file supplies the judgement. Read it before writing markup or styles, and
again during the Phase 5 craft pass.

The premise: **generic is a decision too, and it is almost always the wrong
one.** Reaching for the most common solution to every question produces an
interface that says nothing about the product it belongs to. Every default you
accept without a reason is a place the design stopped.

---

## 1. The tells

These are the recurring signatures of generated UI. Each is a default that got
accepted because no decision was made. If your work contains one, you have not
designed that part yet.

| Tell | Why it reads as generated | Design it instead |
| --- | --- | --- |
| Everything centered | Centering is the choice you make when you have not decided what leads. Symmetry with no focal point flattens hierarchy. | Center a hero if the composition earns it; left-align body content and dense UI. Pick one focal element and let the layout point at it. |
| A gradient hero (indigo→violet, teal→blue) | It is the stock "tech" costume. It carries no meaning and belongs to no brand. | Derive the palette from the brief's personality adjectives. If you use a gradient, it must do a job — depth, direction, product colour continuity — and appear once. |
| Three equal cards in a row | Content forced into a grid it did not ask for. Equal weight means nothing is important. | Let content decide the count and the shape. Uneven weight is honest: the primary item is larger, first, or visually distinct. |
| Generic icons above every heading (rocket, lightning, shield, sparkles) | Decoration standing in for evidence. A rocket does not explain the feature. | Cut the icon, or replace it with the real thing: a screenshot, a number, a diagram, a code sample, a before/after. |
| Emoji as UI icons | Inconsistent metrics, uncontrollable colour, platform-dependent rendering. | A real icon set, sized on the type scale, aligned optically to the text baseline. |
| Purple/indigo accent by default | The framework's starter colour, untouched. | Choose from the brief. If the product has a brand, use it; if not, pick a hue with a reason and note the reason in the design system. |
| Default `box-shadow` on every card | Elevation applied as texture, not as meaning. Ten floating things float nowhere. | Elevation encodes layering: what is above what, and why. Most cards need a border or a background shift, not a shadow. |
| Unmotivated glassmorphism / blur | An effect used because it is available. | Only where there is something behind to see through and a reason to see it. |
| System font stack everywhere | No typographic voice at all. | One deliberate family (two at most). If the system stack is genuinely right, say so in the design system — as a decision, not a default. |
| Full-width text | Long measure destroys readability regardless of contrast. | 60–75ch for prose. Constrain the text, not necessarily the section. |
| Identical vertical padding on every section | Uniform rhythm removes the pacing that guides a reader. | Vary spacing by narrative weight — the hero breathes, related blocks tighten. |
| "Lorem ipsum", "Feature One", "Your Company" | Placeholder content is unshipped content, and it hides real layout problems. | Real copy from the brief's messaging, at realistic length. |
| Three fake testimonials with generic avatars | Fabricated social proof is worse than none — it is a lie in the UI. | Use real proof or design the honest empty state. Never invent a customer, quote, logo, rating, or metric. |

## 2. Hierarchy — one thing leads

On every screen, name the single element the user should see first. If you cannot
name it, the screen has no hierarchy yet.

- Rank every element: primary, supporting, ambient. Three tiers, not seven.
- Enforce the rank with more than one signal — size *and* weight *and* position
  *and* colour. A single signal is fragile.
- One primary action per view. A second button of equal weight halves the first.
  Secondary actions are visually quieter; tertiary actions are text.
- **The squint test:** blur the screen. What remains legible should be exactly
  the order you intended. If everything blurs to the same grey, the hierarchy is
  decorative.
- **The headings test:** read only the headings top to bottom. They should tell
  the whole story on their own.

## 3. Typography — the largest surface you control

- Use the scale's *steps*, not its neighbours. If the heading and the body differ
  by 2px, the reader sees an accident. Jump: body 16 → heading 31, not 16 → 18.
- Line-height moves inversely to size: tight for display (1.05–1.2), open for
  body (1.5–1.7). A heading with body line-height looks unset.
- Weight carries hierarchy more cheaply than size. Prefer a weight change to
  another size step when space is tight.
- Letter-spacing: negative for large display text (−0.01 to −0.03em), none for
  body, positive only for small uppercase labels.
- Set numerals in tables to tabular figures so columns align.
- Never uppercase a whole sentence for emphasis; it destroys word shape.

## 4. Space — the design is mostly space

- Space is the primary grouping signal. **Proximity beats borders:** if two
  things belong together, move them closer before you draw a box around them.
- The gap between groups must exceed the gap within them, visibly — not by 2px.
- Padding is asymmetric more often than people expect: optical centring in a
  button or card usually needs slightly less space below than above.
- Whitespace is not waste. Crowding to fill the viewport is the most common
  self-inflicted damage in generated layouts.
- Alignment: fewer alignment edges is better. Every new edge is a line the eye
  has to track.

## 5. Colour — restraint reads as confidence

- Neutrals do ~90% of the work. The accent is a spotlight; used everywhere, it
  lights nothing.
- One accent, used for the primary action and the things that share its meaning.
  A second accent needs an explicit job (e.g. a distinct semantic axis).
- Never encode meaning in hue alone — pair it with an icon, label, or shape, for
  colour-blind users and for greyscale printing.
- Build the neutral ramp with a consistent perceptual step; a ramp mixed from
  unrelated greys looks muddy. Neutrals that carry a slight hue from the accent
  feel intentional; pure `#888` looks unset.
- Dark mode is not an inversion. Re-derive it: reduce contrast of large
  surfaces, raise elevation with lighter surfaces rather than heavier shadows,
  desaturate accents that vibrate on dark backgrounds.

## 6. Depth, borders, and edges — earn every one

- Ask what each border, shadow, and radius *communicates*. Separation? Elevation?
  Interactivity? If it communicates nothing, delete it.
- Pick one separation strategy per surface — borders or background shifts or
  shadows — and stay with it. All three at once is noise.
- Radii should be consistent in *feel*: a nested rounded element inside a rounded
  container needs a smaller radius (inner = outer − padding) or the curves fight.
- Hairline borders benefit from a colour with alpha rather than a solid grey; it
  survives being placed on different backgrounds.

## 7. Motion — a budget, not a garnish

- Motion exists to explain change: where something came from, what is loading,
  what just succeeded. Motion that explains nothing is latency you added on
  purpose.
- 150ms for state changes, 200–300ms for entrances and layout shifts. Anything
  over 400ms in an interface feels broken.
- Ease-out for things arriving, ease-in for things leaving. Never linear for
  anything spatial.
- Animate `transform` and `opacity`. Animating layout properties causes jank.
- Nothing animates on page load except what the user's attention should follow.
- Everything decorative is removed under `prefers-reduced-motion`.

## 8. Content-shaped, not content-shaped-to-fit

- Design with real content from the brief, at real lengths — including the long
  German product name and the user with no avatar.
- Every state gets designed with content, not left to the framework:
  - **Empty:** what belongs here, why it is empty, and the action that fills it.
    Never a bare "No data".
  - **Loading:** skeletons that match the real layout's shape, so nothing jumps.
  - **Error:** what happened, in the user's terms, and the way out. Never a raw
    status code or stack trace.
  - **Partial/stale:** what is shown and how old it is.
- Test at 0, 1, and 200 items. A layout tuned for exactly three items is not a
  layout.
- Copy is design: headlines state the value, not the category ("Ship without
  breaking things", not "Features"). Buttons state the action ("Create project",
  not "Submit"). Errors say what to do next.

## 9. The detail pass

The last 5% is what separates professional work. Before shipping, check:

- Optical alignment beats mathematical: icons next to text usually need a
  fractional nudge; a triangle in a play button is never centred by its box.
- Hover, focus, and active are all distinct and all deliberate. Focus is visible
  on *every* interactive element, including custom ones, and survives dark mode.
- Interactive targets are ≥44px on touch, and the hit area is at least the
  visible area.
- Text does not shift on hover (a weight change reflows — use a different signal
  or reserve the space).
- Images have intrinsic dimensions so nothing reflows when they load.
- The scrollbar's appearance/disappearance does not shift the layout.
- Nothing overflows at 320px; nothing stretches absurdly at 2560px.
- Test at 200% browser zoom — reflow, not clipping.
- Disabled elements explain *why* they are disabled (tooltip or adjacent text).
- The first paint at each breakpoint is composed, not merely non-broken.

## 10. Craft checklist (Phase 5 — before recording the report)

Run this in addition to the two UI auditors. Every "no" is a finding.

1. Can I name the one focal element of each screen, and does the squint test
   confirm it?
2. Do the headings alone tell the page's story?
3. Is every value from a token, and every token from a decision I can justify
   from the brief?
4. Would this be recognisable as *this* product with the logo removed?
5. Is there a single tell from §1 anywhere in the change?
6. Does every animation explain a change?
7. Are empty, loading, error, and long-content states designed — with copy?
8. Is all copy real, specific, and free of invented proof?
9. Does the detail pass (§9) come back clean at 320px, 768px, 1440px, and 200%
   zoom?
10. If a designer reviewed this, what is the first thing they would change? Do
    that now, rather than shipping it.
