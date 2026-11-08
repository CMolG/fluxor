---
name: layout-discipline
description: Build, generate, refactor, and review UI so that elements breathe (a real spacing hierarchy), nothing collapses or overlaps at any width, overflowing content always wraps, truncates, or scrolls, and components are reused or evolved instead of duplicated. Use this skill EVERY time you write or edit any component, page, layout, shell, form, card, list, table, modal, drawer, sidebar, navigation, or dashboard in a component-based, utility-first stack — even if the user never mentions spacing, responsiveness, overflow, scrolling, or DRY. Also trigger on complaints like "looks cramped", "no space between", "text spills out", "cut off", "doesn't scroll", "breaks on mobile", "overlaps", "collapses", and whenever you are about to create a new component (check for an existing one first). It owns the structural mechanics (containment, scroll ownership, spacing rhythm, responsive strategy, utility-class discipline, component reuse); visual direction and web vitals belong elsewhere.
---

# Layout Discipline

## Why this skill exists

A human fixes a layout by looking at it. You cannot: you emit code without rendering it, and the
browser's defaults are the opposite of what an application layout needs. Every rule below is a
substitute for the eyes you do not have. The recurring failures all come from a handful of causes:

1. **"Content wins" defaults.** Flex and grid items have `min-width: auto` (and `min-height: auto`
   in columns), so a long word or a wide table makes the item refuse to shrink and it spills out of
   its parent. `1fr` is really `minmax(auto, 1fr)`. `overflow` is `visible`, so nothing scrolls
   unless you build an explicit, unbroken height chain.
2. **Nobody owns the space between siblings.** Components generated one at a time carry their own
   margins, which collide, collapse, or vanish, and the "gap" between elements ends up accidental.
3. **Happy-path content.** Examples are written with short strings and three items. Real content
   is long, empty, unbroken (URLs, hashes, emails), translated, or 200 items long.
4. **Fixed sizes feel concrete.** `h-[600px]`, `w-64`, `h-screen` are easy to emit and brittle at
   every width but the one you imagined.
5. **Spacing by feel.** Off-scale values (`p-[13px]`), mixed `space-*` and margins, and no hierarchy
   between "inside" and "between" produce a page where nothing breathes even with lots of padding.
6. **Reuse blindness.** Writing `Card2` costs fewer tokens than reading `Card`. The result is a
   codebase of near-duplicates with slightly different spacing.

## Assumptions and vocabulary

The rules apply to any component-based UI with utility-first styling. Examples use JSX-style
components and utility classes (`flex gap-4 min-w-0`), a static class scanner (only complete literal
class strings are generated), a spacing scale, viewport variants (`sm: md: lg:`), container variants
(`@container` on the parent, `@md:` on descendants), a file-system router with nested `layout`
files, and a class-merge helper `cn()` that joins conditional classes and resolves conflicting
utilities (the later class wins). Color tokens in examples (`bg-background`, `text-muted-foreground`,
`border-primary`) stand for the project's own theme tokens. If the project already has equivalents
for any of this, use those names.

## The seven invariants

Every layout you deliver satisfies all of these. They are not style preferences; each one closes a
specific failure mode from the list above.

1. **Parents own spacing.** Siblings are separated with `gap-*` on the container. Components never
   carry outer margins (`m-*`, `mt-*`, `mb-*`) — a component that positions itself cannot be reused
   anywhere else. The only exception is typographic flow inside a prose block.
2. **Every flexible child gets a min-size reset.** Any flex or grid item that holds text, media, a
   table, or another flexible layout gets `min-w-0` (row axis) or `min-h-0` (column axis). Custom
   grid tracks use `minmax(0,1fr)`, never a bare `1fr`. This is what lets `truncate`, wrapping, and
   inner scroll regions work at all.
3. **One viewport owner, explicit scroll regions.** In *document mode* the body is `min-h-dvh` and
   the page scrolls. In *app-shell mode* the body is `h-dvh overflow-hidden` and every scrolling area
   is an explicit `flex-1 min-h-0 overflow-y-auto` element connected to the owner by an unbroken
   chain of `flex flex-col min-h-0` ancestors. Never `h-screen` (use `dvh`), never `h-full` without a
   definite-height parent, never two scroll regions on the same axis by accident.
4. **Every horizontal arrangement declares its narrow-width strategy** — wrap, stack, auto-fit,
   horizontal scroll, truncate, or clamp — and it is written mobile-first. Content boxes have no fixed
   widths (`w-full max-w-*` instead); fixed sizes are reserved for icons, avatars, rails, and the
   viewport owner.
5. **Spacing comes from the scale and follows a hierarchy:** inside a component < between
   components < between sections. Paragraph text has a measure (`max-w-prose`) and rows whose text
   can wrap align to `items-start`.
6. **Utilities are literal, merged, and varied through maps.** Class names are complete literal
   strings (the scanner cannot see `bg-${color}-500`), merged with `cn()`, and varied through a
   variants map keyed by `variant`/`size`/`tone` props — not through free-form `className`
   restyling, template strings, or `!` important flags.
7. **Search before you create; evolve before you duplicate; compose before you bloat.** No
   `CardV2`, `NewModal`, `CustomButton`, or copy-pasted component with tweaks. Evolution has limits
   (below), and when a limit is hit the answer is composition on top of the existing primitive, not
   a fork.

## Workflow for every UI task

**Step 0 — Decide the mode and the owner.** Is this screen a document (marketing page, article,
settings form: the page scrolls) or an app shell (fixed chrome with scrolling panes)? The decision
lives in the nearest `layout` file, once. Everything below it inherits the height chain.

**Step 1 — Inventory before writing JSX.** List the component directories, grep for the noun
(`Card`, `EmptyState`, `PageHeader`, `Dialog`) and for the class signature you were about to type
(`flex flex-col gap-`). Read the props of what you find. Decide: reuse as-is → evolve → compose →
create. See `references/component-reuse.md` for the decision procedure and the limits.

**Step 2 — Build with layout primitives, not ad-hoc flex soup.** Spacing, wrapping, and
responsiveness live in a small set of primitives (`Stack`, `Cluster`, `Split`, `Switcher`,
`Sidebar`, `AutoGrid`, `Center`, `Section`, `Reel`, `Cover`, plus the two shells). Feature components compose primitives and
pass content; they do not re-type `flex flex-col gap-4` in forty files. If the project lacks them,
add them once under the layout components folder from `references/layout-primitives.md`.

**Step 3 — Apply containment.** Walk every flex/grid child you wrote: does it hold text, an image,
a table, or another flexible container? Then it gets `min-w-0`/`min-h-0`. Walk every horizontal row:
which narrow-width strategy did you give it? Walk every fixed height: is it the viewport owner, an
icon, or a rail? If not, make it `min-h-*`.

**Step 4 — Stress-test before you call it done.** Mentally (or in a browser if one is available,
screenshots at 320, 768, and 1440 wide, and once at a short ~480px-tall viewport) run the content and
viewport matrix in `references/responsive-strategies.md`: 3× longer strings, one unbroken 60+
character token, zero items, 200 items, a narrow sidebar slot.

**Step 5 — Run the audit.** `python scripts/audit_layout.py <changed files or dirs>`. Fix every
error and warning, or justify the exception with a `layout-ok: <reason>` comment on that line
(the audit then skips it). Errors are real bugs; warnings are almost always bugs; info items are
review prompts.

**Step 6 — Deliver.** When the shell decisions are not obvious from the code, state them in one or
two lines (which element owns the viewport, where the scroll region is, which breakpoints matter).

## Spacing: the hierarchy that makes things breathe

"Not enough space" is rarely fixed by more padding; it is fixed by a hierarchy of gaps. Use the scale
(4px base: `1 = 4px, 2 = 8, 3 = 12, 4 = 16, 6 = 24, 8 = 32, 12 = 48, 16 = 64, 24 = 96`) at these
tiers, and keep every inner gap strictly smaller than the gap around it:

| Tier | Typical pair | Default |
|---|---|---|
| Micro (inside a control) | icon ↔ label, badge padding | `gap-1.5`, `px-2.5 py-1` |
| Tight (related pair) | label ↔ input, title ↔ subtitle, avatar ↔ name | `gap-1.5` to `gap-2` |
| Component internal | fields in a form, lines in a card body | `gap-3` to `gap-4` |
| Component padding | card, panel, dialog, popover | `p-4 sm:p-6` (compact `p-3`, spacious `p-8`) |
| Between components | cards in a grid, list items, form groups | `gap-4` to `gap-6` |
| Between sections | blocks of a page | `gap-8`–`gap-12`; section rhythm `py-12 sm:py-16 lg:py-24` |
| Page gutter | container padding | `px-4 sm:px-6 lg:px-8` |

Further rules:

- Spacing between siblings is `gap`. Margin is for the rare intentional offset; `space-*` only for
  prose flows. Never both on the same relationship.
- Rows whose text can wrap use `items-start` and let the control `self-center` if needed;
  `items-center` on a row with a three-line title looks broken.
- Body copy gets a measure: `max-w-prose` (≈65ch). Headings get `text-balance`, paragraphs
  `text-pretty`. Heading-to-body distance is a Stack gap, not `mb-*` on the heading.
- `justify-between` still needs a `gap`: when both sides are long they must not touch.
- Interactive targets: `min-h-11` (44px) on touch surfaces; pad the hit area, not just the glyph.
- Scale a few tokens with the viewport, not everything: padding of shells and sections, gutters,
  and heading sizes grow at `sm:`/`lg:`; internal component gaps usually stay constant.

Read `references/spacing-and-rhythm.md` when a screen "feels off" and you cannot say why.

## Containment and scroll: the collapse/overflow fixes

The canonical shapes. Copy them; do not improvise variants.

```tsx
{/* Text next to an action: the text shrinks, the action never does */}
<div className="flex items-start gap-4">
  <div className="min-w-0 flex-1">
    <h3 className="truncate font-medium">{title}</h3>
    <p className="text-pretty text-sm text-muted-foreground">{description}</p>
  </div>
  <Button className="shrink-0">Edit</Button>
</div>

{/* Custom grid tracks: minmax(0,1fr) or the column refuses to shrink */}
<div className="grid grid-cols-[minmax(0,1fr)_auto] gap-4">…</div>

{/* Unbroken tokens (URLs, hashes): wrap-anywhere also lowers the min-content size */}
<p className="min-w-0 wrap-anywhere">{url}</p>

{/* Tables never shrink below readability; the wrapper scrolls */}
<div className="overflow-x-auto"><table className="w-full min-w-[40rem]">…</table></div>

{/* Media in a row: fixed box, never squished */}
<img className="size-12 shrink-0 rounded-full object-cover" … />
```

The two shells (this decision lives in a `layout` file):

```tsx
{/* Document mode: the page scrolls, footer sits at the bottom of short pages */}
<body className="flex min-h-dvh flex-col">
  <Header />
  <main className="flex-1">{children}</main>
  <Footer />
</body>

{/* App-shell mode: fixed chrome, explicit scroll regions, unbroken min-h-0 chain */}
<body className="flex h-dvh flex-col overflow-hidden">
  <Header className="shrink-0" />
  <div className="flex min-h-0 flex-1">
    <Sidebar className="w-64 shrink-0 overflow-y-auto" />
    <main className="min-h-0 min-w-0 flex-1 overflow-y-auto">{children}</main>
  </div>
</body>
```

A modal is a tiny app shell: `max-h-[calc(100dvh-2rem)] flex flex-col`, header and footer
`shrink-0`, body `min-h-0 flex-1 overflow-y-auto overscroll-contain`. `overflow-hidden` is a clip,
not a fix: use it only when clipping is the design (rounded media, marquee). When content might
exceed its box, choose wrap, `overflow-auto`, or remove the fixed size.

Symptom → cause → fix, for triage:

| Symptom | Usual cause | Fix |
|---|---|---|
| Text pushes its sibling out; child wider than parent | flex/grid item `min-width:auto` | `min-w-0` on the item; `minmax(0,1fr)` |
| Horizontal scrollbar on mobile | fixed width, `w-screen`/`100vw`, un-wrapped row, long token | `w-full max-w-*`, wrap/stack, `wrap-anywhere` |
| Content cut off, no scrollbar | `overflow-hidden`, or a fixed-height box with no scroll region | region `min-h-0 overflow-y-auto` on an unbroken chain, or drop the fixed height |
| Nothing scrolls; page grows; footer off-screen | `h-full`/`h-screen` without definite parents; broken chain | `h-dvh` on the owner, `flex flex-col min-h-0` every level, `flex-1 min-h-0 overflow-y-auto` on the region |
| Two scrollbars | nested scroll regions | one region per axis |
| Elements touch | no `gap`; component margins colliding or collapsing | `gap-*` on the parent; delete outer margins |
| Row wobbles when text wraps | `items-center` on wrapping text | `items-start` (+ `self-center` on the control) |
| Modal taller than screen, footer unreachable | no `max-h` and no inner scroll | `max-h-[calc(100dvh-2rem)] flex flex-col` + scrolling body |
| Component breaks inside a sidebar | viewport breakpoints in a reusable component | `@container` + `@md:` |
| Sticky header does not stick | wrong scroll ancestor, or `overflow` on an in-between ancestor | make the scroll container the sticky's ancestor |
| Styles missing in production | class names built at runtime | literal class map |

Read `references/containment-and-scroll.md` for the mechanics (why `min-width:auto` exists, how the
height chain resolves, sticky, scrollbar gutters, scroll chaining).

## Responsive: every row has a plan

Write the mobile layout as the base classes and add `sm:`/`md:`/`lg:` to expand — never desktop
first with `max-md:` patches. Reusable components respond to their container (`@container` on the
wrapper, `@md:` inside; container breakpoints are smaller than viewport ones, `@md` ≈ 28rem); page
shells respond to the viewport (`md:`).

| Situation | Strategy | Shape |
|---|---|---|
| Chips, tags, buttons, meta | wrap | `flex flex-wrap gap-2` |
| Two blocks side by side | stack → row | `flex flex-col gap-6 md:flex-row`, children `min-w-0 flex-1` |
| Cards / tiles | auto-fit grid | `grid gap-6 grid-cols-[repeat(auto-fit,minmax(min(100%,16rem),1fr))]` |
| Rail + fluid content | sidebar | `md:flex` with `w-64 shrink-0` and `min-w-0 flex-1`, or the wrapping `Sidebar` primitive |
| Tabs, chip rows, tables | horizontal scroll | wrapper `overflow-x-auto`, children `shrink-0` |
| Single-line metadata | truncate | `min-w-0 truncate` |
| Multi-line descriptions | clamp | `line-clamp-2` |
| Anything that may sit in a narrow slot | container query | `@container` + `@md:` variants |

Fixed widths are allowed only for icons/avatars (`size-*`), rails (`w-64 shrink-0` with a `min-w-0`
partner), and max constraints (`max-w-*`). Fixed heights only for the viewport owner, icons, and
rails; content boxes use `min-h-*`. Media boxes declare `aspect-*` + `object-cover` instead of a
height. Read `references/responsive-strategies.md` for the full test matrix and the sidebar/switcher
wrapping math.

## Utility-class discipline

- Values come from the scale. Arbitrary values (`p-[13px]`, `w-[420px]`) are a smell: either the
  token belongs in the theme (add it once) or the design is wrong. Legitimate arbitrary values are
  formulas (`max-h-[calc(100dvh-2rem)]`, `grid-cols-[minmax(0,1fr)_auto]`).
- Never construct class names at runtime. Map props to complete literal strings:
  `const TONE = { info: 'bg-blue-50 text-blue-900', danger: 'bg-red-50 text-red-900' } as const`.
- Merge with `cn(base, VARIANT[variant], SIZE[size], className)`. Accept `className` for placement
  in the parent (`col-span-2`, `self-end`), not for restyling internals; if callers keep passing
  visual overrides, that is a missing variant.
- Boolean props are for real binary state (`disabled`, `loading`, `selected`), never for "a
  different look" — that is a `variant`.
- Prefer `gap` to `space-*`, `size-*` to `w-* h-*` pairs, `py-4` to `pt-4 pb-4`, `min-h-dvh` to
  `min-h-screen`, `w-full` to `w-screen` (which includes the scrollbar and causes horizontal
  overflow).
- No `!` important flags and no `@apply` to escape a specificity fight; fix the merge order or the
  variant instead.
- Keep class lists short and grouped in a stable order (layout → sizing → spacing → typography →
  color/border → effects → states → responsive). If the project has a class-sorting formatter, run it.

## Component reuse and evolution

Before writing a component, search for it (Step 1). When you find one that almost fits, classify
the gap and act:

| The gap is… | Action |
|---|---|
| a visual axis (size, tone, density, emphasis) | **Evolve:** add one value to the variants map |
| a missing region (footer, actions, media, aside) | **Evolve:** add a slot (`children` or a named node prop, or a `Card.Footer` part) |
| a missing state (loading, empty, error, selected) | **Evolve:** add the state prop, mapped to classes/attributes |
| a different intent or behavior (static → interactive, display → form, inline → page-level) | **Compose:** build the new thing on top of the existing primitives |
| a one-caller special case | **Compose** at the call site; do not add a prop nobody else will use |

Stop evolving and compose instead when any of these would become true — this is the guard against
the infinite-props component:

- it would need a **third boolean prop**, or a prop that only one caller uses;
- two props would need documentation about how they combine;
- more than roughly a third of the JSX would branch on props;
- the component's name would no longer describe what it renders.

When you hit a limit, extract the shared core into a smaller primitive and build both callers on it.
Duplicating two lines of utility classes is fine; duplicating a component with behavior, spacing
decisions, or accessibility wiring is not. Expose parts (`Card`, `Card.Header`, `Card.Body`) rather
than configuration props (`showHeader`, `headerTitle`, `headerAction`). Read
`references/component-reuse.md` for worked examples of a correct and an incorrect evolution, and for
the promotion rule (route-private → shared).

## Structure

Routes are thin; layouts own shells; components live in layers that map to reuse scope:

```
app/                       routes only: layout.* owns the shell (height chain), page.* composes
  (group)/                 route groups per shell (marketing, app, auth)
  dashboard/_components/   route-private pieces; promote when a second route needs them
components/
  ui/                      primitives: button, input, card, dialog… variants, no domain knowledge
  layout/                  Stack, Cluster, Split, Switcher, Sidebar, AutoGrid, Center, Section, Reel, Cover, shells
  patterns/                composed, domain-free: PageHeader, EmptyState, FormField, DataTableShell
features/<domain>/         domain components + hooks, composed from ui/layout/patterns
lib/utils.*                cn() and small helpers
```

One component per file, file name equals component name, `layout` files are the only places that
own viewport height, and a component moves up a layer only when a second consumer appears (promote;
never copy). Read `references/structure.md` when creating files or bootstrapping a project.

## Pre-delivery checklist

- [ ] Viewport owner decided in a `layout` file; document or app-shell mode, not both.
- [ ] Every flex/grid child holding text/media/tables has `min-w-0` (or `min-h-0`); custom tracks use `minmax(0,1fr)`.
- [ ] Every horizontal row has a declared narrow strategy; no fixed widths on content boxes.
- [ ] Every scroll region is `min-h-0 overflow-y-auto` on an unbroken `flex flex-col min-h-0` chain.
- [ ] No outer margins on components; all sibling spacing is `gap` on the parent; inner gap < outer gap.
- [ ] Rows with wrapping text use `items-start`; paragraphs have a measure.
- [ ] No runtime-built class names; variants via maps; `className` merged with `cn()`.
- [ ] Searched for an existing component first; evolutions stayed within the limits; no forks.
- [ ] Stress-tested with long/empty/many content and at 320 / 768 / 1440 widths and a short viewport.
- [ ] `scripts/audit_layout.py` reports no errors; warnings fixed or justified inline.

## References

- `references/containment-and-scroll.md` — mechanics of `min-width:auto`, the height chain, scroll owners, modals, tables, sticky, scrollbar gutter, scroll chaining. Read when anything overflows, clips, or refuses to scroll, and when building shells, dialogs, or data tables.
- `references/spacing-and-rhythm.md` — the scale, tiers, ownership rules, typography measure, and how to diagnose "cramped" or "floaty" screens.
- `references/responsive-strategies.md` — the strategy catalogue, container queries, sidebar/switcher math, and the stress-test matrix.
- `references/component-reuse.md` — search procedure, evolve/compose/create decision, evolution limits with worked examples, promotion rule.
- `references/layout-primitives.md` — copy-ready `Stack`, `Cluster`, `Split`, `Switcher`, `Sidebar`, `AutoGrid`, `Center`, `Section`, `Reel`, `Cover`, `PageShell`, `AppShell`, and `DialogFrame`.
- `references/structure.md` — folder layers, colocation, promotion, naming, what a `layout` file may and may not do.
- `scripts/audit_layout.py` — static audit for the anti-patterns above; run on changed files before delivering.
