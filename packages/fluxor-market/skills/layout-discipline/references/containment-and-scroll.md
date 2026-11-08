# Containment and scroll — the mechanics

Read this when something overflows, clips, refuses to shrink, or refuses to scroll, and before
building shells, dialogs, drawers, data tables, or sticky headers.

## 1. Why children refuse to shrink: `min-width: auto`

Flex items and grid items get an *automatic minimum size* equal to their min-content size. The
spec authors chose this deliberately: they preferred an item that overflows its container over an
item that silently squashes its own content. The consequence is that a long word, an email, a URL,
a `<pre>`, a table, an image without `max-width`, or a `white-space: nowrap` label makes the item
refuse to go narrower than that content, and the item — not the text — spills out of the parent.

Three things disable the automatic minimum on an item:

1. `min-w-0` (row axis) / `min-h-0` (column axis) — the explicit reset. Default choice.
2. Any `overflow` other than `visible` on the item (`overflow-hidden`, `overflow-auto`,
   `overflow-clip`) — also resets it, as a side effect. Use when you actually want clipping or
   scrolling on that item.
3. A definite `width`/`flex-basis` in some cases — not reliable across engines; do not depend on it.

Grid has the same rule per track: `1fr` means `minmax(auto, 1fr)`. The utility `grid-cols-3` already
expands to `repeat(3, minmax(0, 1fr))`, which is why simple grids behave; custom templates written
with a bare `1fr` (`grid-cols-[1fr_auto]`) do not. Write `grid-cols-[minmax(0,1fr)_auto]`.

Rule of thumb: **every flex/grid child that holds text, media, a table, a code block, or another
flexible layout gets `min-w-0`** (and `min-h-0` when it is a flex-column child that must scroll).
It is harmless when unnecessary and decisive when necessary.

```tsx
<li className="flex items-start gap-3">
  <Avatar className="size-10 shrink-0" />
  <div className="min-w-0 flex-1">              {/* ← without this, a long name widens the row */}
    <p className="truncate font-medium">{name}</p>
    <p className="wrap-anywhere text-sm">{email}</p>
  </div>
  <time className="shrink-0 text-xs">{when}</time>
</li>
```

### Wrapping long tokens

- `break-words` (`overflow-wrap: break-word`) breaks an unbreakable token *after* layout, so it does
  **not** lower the min-content size — inside a flex item you still need `min-w-0`.
- `wrap-anywhere` (`overflow-wrap: anywhere`) is considered when computing min-content, so the item
  can shrink on its own. Prefer it for URLs, hashes, emails, and user-generated strings. If the
  utility does not exist in the project's version, use the arbitrary property `[overflow-wrap:anywhere]`.
- `break-all` breaks inside every word; only for hashes/identifiers where readability is irrelevant.
- `truncate` (nowrap + hidden + ellipsis) only works on an element with a constrained width, which
  means its flex/grid ancestor item needs `min-w-0` or an explicit width. `line-clamp-N` for
  multi-line.

### Media

Images in the reset are already `max-width: 100%; height: auto`, so a bare `<img>` in a block will
scale. Inside a flex row give media a fixed box and `shrink-0`; give free-flowing media an
`aspect-*` box with `object-cover` instead of a height:

```tsx
<div className="aspect-video w-full overflow-hidden rounded-lg">
  <img className="size-full object-cover" … />
</div>
```

### Tables and code

Neither can wrap sensibly. Wrap them in a scrolling box and protect their minimum readable width:

```tsx
<div className="overflow-x-auto [scrollbar-gutter:stable]">
  <table className="w-full min-w-[40rem] text-sm">…</table>
</div>
<pre className="overflow-x-auto rounded-md bg-muted p-4 text-sm">…</pre>
```

The wrapper must itself be a `min-w-0` flex/grid child if it lives in a row, or the table's
`min-w` propagates up as the row's minimum and the page grows a horizontal scrollbar.

## 2. Why nothing scrolls: the height chain

`overflow-y-auto` only produces a scrollbar when the element's height is **constrained** and its
content is taller. Height is constrained only if the element has a definite height itself, or is a
flex/grid item in a container with a definite height, and so on up to something definite (the
viewport). One `height: auto` in the chain and the constraint disappears: the element just grows,
the page grows, and the footer ends up off-screen.

The reliable pattern is a chain of flex columns:

```
viewport owner        h-dvh overflow-hidden flex flex-col     ← the only definite height
  chrome              shrink-0
  content row         flex min-h-0 flex-1                     ← min-h-0 on EVERY level
    rail              w-64 shrink-0 overflow-y-auto
    scroll region     min-h-0 min-w-0 flex-1 overflow-y-auto  ← the scrollbar appears here
```

Why `min-h-0` on every level: each intermediate element is itself a flex item (of a column
container), so it has `min-height: auto`, so it refuses to be shorter than its content, so the
scroll region below it is never constrained. `flex-1` alone does not reset it. The chain breaks at the
first level you forget.

`h-full` (`height: 100%`) works only when the parent has a *definite* height. Inside a flex column
the parent's height is usually indefinite, so `h-full` resolves to `auto`. Use `flex-1 min-h-0`
instead of `h-full` inside flex chains; reserve `h-full` for children of an element with `h-dvh`,
`h-64`, or a grid track with a fixed row size.

`h-screen` (`100vh`) is the wrong unit on mobile: the browser's collapsing toolbar makes `100vh`
taller than the visible area, so the bottom of the shell is hidden behind the toolbar. `dvh` follows
the visible viewport. Use `h-dvh`, `min-h-dvh`, `max-h-dvh`, `calc(100dvh-…)`.

### Document mode vs app-shell mode

Decide once, in the nearest `layout` file, and never mix the two on the same screen:

- **Document mode** — content is a page. `body: flex min-h-dvh flex-col`, `main: flex-1`, no
  `overflow` anywhere in the chain. The viewport scrolls; long pages just get longer. Sticky headers
  are `sticky top-0` on the `body` scroller. Use for marketing, articles, settings, most forms.
- **App-shell mode** — chrome stays put, panes scroll. `body: flex h-dvh flex-col overflow-hidden`
  and the chain above. Use for dashboards, editors, inboxes, chat, anything with a persistent
  sidebar and its own scroll position.

Two scroll regions on the same axis nested inside each other (a scrolling page containing a
scrolling panel that contains a scrolling list) are almost always a bug: the user's wheel gets
trapped in whichever one is under the pointer. One region per axis per screen; if a panel must
scroll independently, the page must not.

### Scroll chaining and gutters

- `overscroll-contain` on modals, drawers, and independent panes so reaching the end of the pane
  does not start scrolling the page behind it.
- `[scrollbar-gutter:stable]` on regions whose content toggles between short and long, so the
  appearance of a scrollbar does not shift the layout.
- Prefer `overflow-auto` (scrollbar on demand) to `overflow-scroll` (always reserves the bar).

## 3. Dialogs, drawers, popovers

A dialog is a miniature app shell: it must never exceed the viewport, and its body scrolls while
its header and footer stay reachable.

```tsx
<div role="dialog" aria-modal className="fixed inset-0 z-50 grid place-items-center p-4">
  <div className="flex max-h-[calc(100dvh-2rem)] w-full max-w-lg flex-col rounded-xl bg-background shadow-lg">
    <header className="shrink-0 border-b p-6">…</header>
    <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-6">…</div>
    <footer className="flex shrink-0 justify-end gap-3 border-t p-6">…</footer>
  </div>
</div>
```

- The `p-4` on the overlay plus `calc(100dvh-2rem)` keeps a 1rem margin at every viewport height.
- Side drawers use `h-dvh` on the panel itself (it is a new viewport owner) with the same
  header/body/footer chain.
- Popovers and menus need `max-h-[min(24rem,calc(100dvh-4rem))] overflow-y-auto` on the list, and
  a positioning strategy that flips near edges (usually provided by the library in use).

## 4. Sticky

`position: sticky` sticks relative to the **nearest scrolling ancestor**. It fails when:

- an ancestor between the sticky element and the scroller has `overflow` set (even `overflow-x-auto`
  or `overflow-hidden`) — that ancestor becomes the (non-scrolling) scroll context;
- the sticky element's parent is exactly as tall as the sticky element, so there is nothing to stick
  within (common in tables: make `thead` sticky inside the scrolling wrapper, not the wrapper itself);
- in a grid, the sticky item stretches to the row height; add `self-start` so it has room to move.

## 5. Quick verification procedure

For each new flex/grid container you wrote, answer three questions:

1. **Shrink:** which children hold text/media/tables? Do they have `min-w-0` (or an intentional
   `overflow-*`)? Do the ones that must not shrink have `shrink-0`?
2. **Wrap:** what happens at 320px wide? Which strategy (wrap / stack / auto-fit / scroll /
   truncate / clamp) did you declare?
3. **Height:** if anything here scrolls, trace the chain up to the viewport owner and check for a
   missing `min-h-0` or a stray `h-full`/`h-screen`.

If you can render, load the screen at 320 × 480 and at 1440 × 900 with the longest realistic
content. The horizontal scrollbar at 320 and the missing vertical scrollbar at 480 tall are the two
things to look for.
