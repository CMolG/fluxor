# Spacing and rhythm

Read this when choosing spacing values, when a screen feels cramped or floaty, or when two
components look like they belong together but should not (or vice versa).

## 1. The idea: spacing is hierarchy, not quantity

People read grouping from proximity (Gestalt): whatever is closer together is read as one thing.
A screen "breathes" when the distances encode the structure — small inside a unit, larger between
units, larger still between sections — and it feels cramped or confusing when they do not, no
matter how much padding is sprinkled around. So the rule is relational: **every inner gap is
strictly smaller than the gap around it.** A card with `gap-4` inside sits in a grid with `gap-6`;
a section with `gap-8` inside sits in a page with `py-16` between sections.

The scale (4px base) gives you enough steps to express three or four levels of hierarchy without
inventing values:

| Token | px | Use |
|---|---|---|
| 0.5 / 1 | 2 / 4 | optical alignment, badge padding, icon-to-text in tiny controls |
| 1.5 / 2 | 6 / 8 | inside controls; tight pairs (label ↔ input, title ↔ subtitle) |
| 3 / 4 | 12 / 16 | inside components (form fields, card body lines); compact padding |
| 6 | 24 | default component padding; between components |
| 8 | 32 | spacious padding; between groups |
| 12 / 16 | 48 / 64 | between sections (mobile / desktop) |
| 20 / 24 | 80 / 96 | hero and section rhythm on large screens |

Off-scale values (`p-[13px]`, `mt-[7px]`) are how a scale dies. If a design token is missing
(e.g. a `4.5` step you need everywhere), add it to the theme once; do not inline it.

## 2. Tiers, with the classes you actually type

| Tier | Typical pair | Default | Notes |
|---|---|---|---|
| Micro | icon ↔ label; badge padding | `gap-1.5`; `px-2 py-0.5` (badge), `px-2.5 py-1` (chip) | keep icons `size-4` in text-sm, `size-5` in text-base |
| Tight | label ↔ input; title ↔ subtitle; avatar ↔ name | `gap-1.5`–`gap-2` | this is a `Stack gap={1.5}` or `gap={2}` |
| Component internal | fields; lines of a card body; list rows inside a panel | `gap-3`–`gap-4` | `gap-4` for forms, `gap-3` for dense data |
| Component padding | card / panel / dialog / popover | `p-4 sm:p-6` | compact `p-3`; spacious `p-8`; dialog `p-6` |
| Between components | cards in a grid; list items; form groups | `gap-4`–`gap-6` | must exceed the components' internal gap |
| Between sections | blocks of a page | inside `gap-8`–`gap-12`; between `py-12 sm:py-16 lg:py-24` | scale with viewport |
| Page gutter | horizontal container padding | `px-4 sm:px-6 lg:px-8` | in the `Center` primitive only |
| Control sizing | buttons / inputs | `h-9 px-3 text-sm` (sm), `h-10 px-4` (md), `h-11 px-5` (lg) | touch targets `min-h-11` |

A well-formed card, for reference:

```tsx
<article className="flex flex-col gap-4 rounded-xl border p-4 sm:p-6">   {/* padding: component tier */}
  <header className="flex items-start justify-between gap-4">            {/* between: gap-4 */}
    <div className="min-w-0 flex flex-col gap-1">                          {/* tight: gap-1 */}
      <h3 className="truncate font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground">{subtitle}</p>
    </div>
    <Badge className="shrink-0">{status}</Badge>
  </header>
  <p className="text-pretty text-sm">{body}</p>
  <footer className="flex flex-wrap items-center gap-2">…</footer>          {/* micro: gap-2 */}
</article>
```

And a grid of them at `gap-6` — larger than the `gap-4` inside — so the eye groups each card
before it groups the grid.

## 3. Ownership: who is allowed to create space

- **Parents create space between siblings** with `gap-*`. That is the only mechanism for sibling
  spacing in components.
- **Components create space inside themselves** with padding. They never carry outer margin: a
  component with `mb-6` baked in cannot be dropped into a grid, a row, or a dialog without fighting
  it, and two of them in a column produce a margin that may collapse, double, or vanish depending on
  context. Delete `m-*` from component roots; move the spacing to the parent's gap.
- **Margin is for deliberate offsets**: pulling an element out of the flow (`-mx-4` to bleed a
  list to the card edge), `mt-auto` to push a footer down inside a flex column, `mx-auto` to center
  a fixed-width block. Each of these is a local decision, never a spacing system.
- **`space-y-*` / `space-x-*`** are margin-based and break with wrapping, reordering, and hidden
  children. Use them only for a run of prose elements; everywhere else `gap`.
- `justify-between` is not spacing. Add a `gap` too; when both sides grow the gap is what keeps
  them apart.

## 4. Alignment

- Rows whose text can wrap: `items-start`. Center-aligning a control next to a title that wraps to
  three lines makes the control float in the middle of the paragraph. Let the control opt in with
  `self-center` if it is small and the text is short by construction (a single-line label).
- Rows of single-line controls (toolbar, button group): `items-center`.
- Baseline-align mixed text sizes on one line (`items-baseline`): price + unit, heading + count.
- Grids of cards: `items-stretch` (default) so cards in a row share a height; push footers down
  inside each card with `mt-auto` on the footer or a `flex-1` spacer, so actions line up across
  cards.

## 5. Typography breathing room

- Body copy has a measure: `max-w-prose` (≈65 characters). A paragraph stretched across a 1440px
  container is unreadable even with perfect spacing. Apply the measure to the text block, not to the
  page — the page container can be wider than the reading column.
- Line-height: default body line-height is already 1.5; large headings use `leading-tight`
  (`text-3xl` and up), UI labels `leading-none` only when vertically centered by a flex parent.
- Heading → body distance is a Stack gap (`gap-2` for title/subtitle, `gap-4`–`gap-6` for
  section title/content), not `mb-*` on the heading — except inside a prose block, where the
  typographic flow owns its own margins.
- `text-balance` on headings (even line lengths), `text-pretty` on paragraphs (no orphans).
- Headings scale with the viewport, body rarely does: `text-2xl sm:text-3xl lg:text-4xl` vs
  `text-base`. Never let text sizes jump more than one or two steps between breakpoints.

## 6. Diagnosing "it feels off"

| Feeling | Look for | Fix |
|---|---|---|
| Cramped | inner gap equal to or larger than outer gap; padding smaller than the gap it contains | restore the hierarchy: reduce inner gap or increase outer |
| Floaty / disconnected | related elements separated by section-tier spacing; label far from its input | tighten to the tight tier; group with a Stack |
| Wall of text | no measure; paragraphs at 100% width; missing heading gaps | `max-w-prose`, Stack gaps around headings |
| Uneven | margins on components + gap on parents; `space-y` mixed with `gap`; off-scale values | one mechanism (gap), on-scale values |
| Busy | too many borders/backgrounds compensating for missing space | remove a border, add a tier of space |
| Misaligned rows | `items-center` with wrapping text; mixed text sizes without baseline alignment | `items-start` / `items-baseline` |

When you cannot name what is wrong, print the gap values from the outside in (page → section →
component → inside) and check that they strictly decrease. Nine times out of ten that is the bug.
