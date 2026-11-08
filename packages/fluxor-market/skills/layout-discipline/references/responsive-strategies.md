# Responsive strategies

Read this for any multi-column or horizontal arrangement, for reusable components that may live in
slots of unknown width, and for the stress-test matrix before delivery.

## 1. Mobile first, always

Base classes describe the narrowest layout; `sm:`, `md:`, `lg:` add columns and space as room
appears. Desktop-first code with `max-md:` patches fails in the gaps between the breakpoints you
happened to test and forgets the layouts you did not test. If a screen needs a distinct mobile
structure (e.g. a bottom tab bar instead of a sidebar), render both and toggle with `hidden md:flex`
/ `md:hidden`, keeping the DOM order sensible for keyboard users.

## 2. Viewport vs container

- **Viewport variants** (`md:`) belong to the shell: number of columns on the page, whether the
  sidebar is visible, gutters, section rhythm, hero type sizes.
- **Container variants** belong to reusable components. Put `@container` on the wrapper the
  component controls and use `@md:`/`@lg:` inside. The component then reads the width it actually
  has — a card is stacked in a 300px sidebar and side-by-side in a 900px main column, with the same
  code. Container breakpoints are smaller than viewport ones (`@sm` 24rem, `@md` 28rem, `@lg` 32rem,
  `@xl` 36rem, `@2xl` 42rem, …); pick by the component's own needs, not by the page's breakpoints.
- Name containers only when nesting requires targeting a specific ancestor (`@container/panel`
  and `@md/panel:`). Otherwise the nearest container wins.

```tsx
export function MediaCard(props) {
  return (
    <div className="@container">
      <article className="flex flex-col gap-4 @md:flex-row @md:gap-6">
        <div className="aspect-video w-full shrink-0 overflow-hidden rounded-lg @md:w-48">…</div>
        <div className="min-w-0 flex-1">…</div>
      </article>
    </div>
  );
}
```

## 3. The strategy catalogue

Every horizontal arrangement gets exactly one of these, chosen by what the content is:

| Content | Strategy | Shape | Notes |
|---|---|---|---|
| Small, independent items (chips, tags, buttons, meta) | **wrap** | `flex flex-wrap items-center gap-2` | never `whitespace-nowrap` on the row |
| Two or three content blocks | **stack → row** | `flex flex-col gap-6 md:flex-row`; children `min-w-0 flex-1` (or `md:basis-1/3`) | gap stays the same in both directions |
| Repeated tiles of similar size | **auto-fit grid** | `grid gap-6 grid-cols-[repeat(auto-fit,minmax(min(100%,16rem),1fr))]` | `min(100%,…)` prevents overflow below the min tile width; `auto-fit` stretches, `auto-fill` keeps empty tracks |
| Known column counts | **explicit grid** | `grid gap-6 sm:grid-cols-2 lg:grid-cols-3` | built-in `grid-cols-N` already uses `minmax(0,1fr)` |
| Rail + fluid content | **sidebar** | see §4 | main column always `min-w-0` |
| Long horizontal sequences (tabs, chip rows, carousels) | **horizontal scroll (reel)** | wrapper `flex gap-3 overflow-x-auto [scrollbar-gutter:stable] snap-x`; children `shrink-0 snap-start` | add visible affordance (fade or arrows); keyboard reachable |
| Data tables | **scroll wrapper** | `overflow-x-auto` around `min-w-[40rem]` table | sticky first column: `sticky left-0 bg-background` |
| Single-line metadata | **truncate** | `min-w-0 truncate` | show the full value in a `title` or tooltip |
| Multi-line descriptions | **clamp** | `line-clamp-2` | pair with a details view |
| Absolutely-positioned overlays | **contain** | parent `relative overflow-hidden`; child `inset-0` | never position relative to the viewport for in-component overlays |

A row that has none of these will overflow at some width. If you cannot choose, the default is
"stack → row".

## 4. Sidebar and switcher math

**Breakpoint sidebar** (simple, viewport-driven, fine for shells):

```tsx
<div className="flex flex-col gap-6 md:flex-row">
  <aside className="md:w-64 md:shrink-0">…</aside>
  <div className="min-w-0 flex-1">…</div>
</div>
```

**Wrapping sidebar** (content-driven, no breakpoint; the rail sits beside the content while the
content can keep at least half the width, and drops below it otherwise):

```tsx
<div className="flex flex-wrap gap-6">
  <aside className="min-w-0 grow basis-64">…</aside>        {/* wants 16rem, may grow */}
  <div className="min-w-[50%] basis-0 grow-[999]">…</div>    {/* takes the rest; wraps under when < 50% */}
</div>
```

**Switcher** (N equal columns that all drop to a stack at once, instead of leaving a lonely third
column): use a container query — `@container` on the wrapper, `flex flex-col gap-4 @2xl:flex-row`
on the row, `min-w-0 flex-1` on each child. The children never "stagger" because they switch
together.

**Rail widths** are fixed on purpose (`w-64`, `w-72`) and are the one place a fixed width is fine —
always paired with `shrink-0` on the rail and `min-w-0 flex-1` on its sibling, so the sibling
absorbs all the flexibility.

## 5. Sizes that are allowed to be fixed

| Allowed | Not allowed |
|---|---|
| icons, avatars, thumbnails: `size-4`, `size-10`, `size-12` | content boxes: `w-[420px]` → `w-full max-w-md` |
| rails: `w-64 shrink-0` | text columns: `w-1/2` without `min-w-0` |
| max constraints: `max-w-md`, `max-w-5xl`, `max-w-prose` | heights on content: `h-[300px]` → `min-h-[300px]` or `aspect-*` |
| viewport owner: `h-dvh` | `h-screen`, `w-screen` (scrollbar overflow), `100vw` |
| media boxes: `aspect-video`, `aspect-square` + `object-cover` | images with hard `w-* h-*` and no `object-fit` |
| control heights: `h-9/10/11` | `min-h-11` for touch targets — required, not optional |

## 6. The stress-test matrix

Run this before you deliver. Mentally at minimum; with real screenshots when a browser tool exists.

**Viewports**

| Width | What breaks here |
|---|---|
| 320 | unwrapped rows, fixed widths, tables, long tokens, gutters too large |
| 375 | the same, plus multi-column grids that should still be one column |
| 768 | stack → row transitions; sidebars appearing; container queries in narrow slots |
| 1024 | three-column layouts; rails + content + inspector |
| 1440+ | measure (paragraphs too wide), grids with too many columns, hero scale |

**Heights**: ~480px tall (landscape phone, or keyboard open) — modals must scroll, app shells must not
push the footer/actions below the fold. ~900px tall for the default.

**Content**

| Case | What breaks here |
|---|---|
| Every string 3× longer | `items-center` rows, missing `min-w-0`, `justify-between` without gap |
| One unbroken 60+ character token (URL, hash, email) | anything without `wrap-anywhere`/`truncate`/`min-w-0` |
| Zero items | empty states, `justify-between` with one child, collapsed panels |
| One item | grids that assume ≥ 2; centered vs aligned single card |
| 200 items | scroll regions, virtualization needs, sticky headers, performance |
| Translated copy 30–40% longer | buttons, tabs, navigation labels; use `min-w-*` on buttons and wrap on tab rows |
| Missing optional fields | conditional rendering that removes a sibling and changes the gap logic |

**Interaction states**: loading (skeleton same size as content to avoid layout shift), error inline
(reserve space or let it push content, never overlap), focus visible at every width, hover styles
harmless on touch.

## 7. Recording the decision

When a component makes a non-obvious responsive choice, write it where the next reader looks: a
one-line comment on the row (`{/* stacks under @lg; cards keep 16rem min */}`) or the primitive's
prop (`<Switcher threshold="2xl">`). Undocumented breakpoints are the first thing a future edit
breaks.
