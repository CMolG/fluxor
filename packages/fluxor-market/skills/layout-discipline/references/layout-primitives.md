# Layout primitives

Copy-ready building blocks. They are the only place where spacing values, wrapping strategies,
and containment resets get typed; feature components compose them and pass content. If the project
already has equivalents (any name), use those instead of adding these — the point is one set, not
two.

Conventions used below:

- `cn()` joins conditional classes and resolves conflicting utilities (later wins).
- Every prop that changes classes maps to a **complete literal class string** through a `const`
  map, so the static scanner sees every class.
- Row-like primitives apply `*:min-w-0` (direct children) so children can shrink by default;
  `shrink-0` on a child opts out.
- The element-props type is aliased once; adapt the import to the framework in use.

```tsx
// components/layout/primitives.tsx  (or one file per primitive, matching the project's convention)
import type { ComponentPropsWithoutRef, ReactNode } from 'react'; // adapt to your framework's element-props type
import { cn } from '@/lib/utils';

type DivProps = ComponentPropsWithoutRef<'div'>;

export const GAP = {
  1: 'gap-1', 1.5: 'gap-1.5', 2: 'gap-2', 3: 'gap-3', 4: 'gap-4', 6: 'gap-6', 8: 'gap-8', 12: 'gap-12',
} as const;
export type Gap = keyof typeof GAP;
```

## Stack — vertical rhythm

```tsx
export function Stack({ gap = 4, className, ...props }: DivProps & { gap?: Gap }) {
  return <div className={cn('flex flex-col', GAP[gap], className)} {...props} />;
}
```

Use for anything vertical: form fields (`gap={4}`), title + subtitle (`gap={1.5}`), page sections
(`gap={12}`). Headings inside a Stack get no `mb-*`.

## Cluster — things that wrap

```tsx
const JUSTIFY = { start: 'justify-start', center: 'justify-center', end: 'justify-end', between: 'justify-between' } as const;

export function Cluster({
  gap = 2, justify = 'start', align = 'center', className, ...props
}: DivProps & { gap?: Gap; justify?: keyof typeof JUSTIFY; align?: 'start' | 'center' | 'baseline' }) {
  return (
    <div
      className={cn(
        'flex flex-wrap *:min-w-0',
        align === 'start' ? 'items-start' : align === 'baseline' ? 'items-baseline' : 'items-center',
        GAP[gap], JUSTIFY[justify], className,
      )}
      {...props}
    />
  );
}
```

Tags, chips, button groups, metadata rows, toolbar items. `justify="between"` still gets a gap.

## Split — content beside an action

The single most common row: something that may be long on one side, something that must keep its
size on the other.

```tsx
export function Split({ aside, gap = 4, align = 'start', className, children, ...props }:
  DivProps & { aside: ReactNode; gap?: Gap; align?: 'start' | 'center' }) {
  return (
    <div className={cn('flex', align === 'center' ? 'items-center' : 'items-start', GAP[gap], className)} {...props}>
      <div className="min-w-0 flex-1">{children}</div>
      <div className="shrink-0">{aside}</div>
    </div>
  );
}
```

`align="center"` only when the content is single-line by construction.

## Switcher — columns that collapse together

```tsx
const AT = { md: '@md:flex-row', lg: '@lg:flex-row', xl: '@xl:flex-row', '2xl': '@2xl:flex-row', '3xl': '@3xl:flex-row' } as const;

export function Switcher({ at = '2xl', gap = 6, className, ...props }: DivProps & { at?: keyof typeof AT; gap?: Gap }) {
  return (
    <div className="@container">
      <div className={cn('flex flex-col *:min-w-0 *:flex-1', AT[at], GAP[gap], className)} {...props} />
    </div>
  );
}
```

Two or three content blocks that should sit side by side when the *container* is wide enough and
stack otherwise, switching all at once. Container breakpoints: `@md` 28rem, `@lg` 32rem, `@xl` 36rem,
`@2xl` 42rem, `@3xl` 48rem.

## Sidebar — rail beside fluid content, no breakpoint

```tsx
const RAIL = { sm: 'basis-56', md: 'basis-64', lg: 'basis-72' } as const;

export function Sidebar({
  aside, side = 'left', rail = 'md', gap = 6, className, children, ...props
}: DivProps & { aside: ReactNode; side?: 'left' | 'right'; rail?: keyof typeof RAIL; gap?: Gap }) {
  const railEl = <div className={cn('min-w-0 grow', RAIL[rail])}>{aside}</div>;
  return (
    <div className={cn('flex flex-wrap', GAP[gap], className)} {...props}>
      {side === 'left' && railEl}
      <div className="min-w-[50%] basis-0 grow-[999]">{children}</div>
      {side === 'right' && railEl}
    </div>
  );
}
```

The rail wants its basis; the content takes everything else and drops below the rail as soon as it
would get less than half the width. No media query, works in any slot.

## AutoGrid — tiles that fit

```tsx
const TILE = {
  sm: 'grid-cols-[repeat(auto-fit,minmax(min(100%,12rem),1fr))]',
  md: 'grid-cols-[repeat(auto-fit,minmax(min(100%,16rem),1fr))]',
  lg: 'grid-cols-[repeat(auto-fit,minmax(min(100%,20rem),1fr))]',
} as const;

export function AutoGrid({ tile = 'md', gap = 6, className, ...props }: DivProps & { tile?: keyof typeof TILE; gap?: Gap }) {
  return <div className={cn('grid *:min-w-0', TILE[tile], GAP[gap], className)} {...props} />;
}
```

`min(100%, …)` keeps a tile from forcing horizontal overflow when the container is narrower than
the tile minimum. Use `auto-fill` in the map instead of `auto-fit` when you want empty tracks to
remain (e.g. a fixed-looking gallery).

## Center — the page container

```tsx
const MEASURE = { prose: 'max-w-prose', md: 'max-w-3xl', lg: 'max-w-5xl', xl: 'max-w-7xl' } as const;

export function Center({ size = 'lg', gutter = true, className, ...props }:
  DivProps & { size?: keyof typeof MEASURE; gutter?: boolean }) {
  return <div className={cn('mx-auto w-full', MEASURE[size], gutter && 'px-4 sm:px-6 lg:px-8', className)} {...props} />;
}
```

The only component that knows the page gutter. `size="prose"` for reading columns.

## Section — vertical rhythm between page blocks

```tsx
const RHYTHM = { sm: 'py-8 sm:py-12', md: 'py-12 sm:py-16 lg:py-24', lg: 'py-16 sm:py-24 lg:py-32' } as const;

export function Section({ rhythm = 'md', className, ...props }: ComponentPropsWithoutRef<'section'> & { rhythm?: keyof typeof RHYTHM }) {
  return <section className={cn(RHYTHM[rhythm], className)} {...props} />;
}
```

Usage: `<Section><Center><Stack gap={8}>…</Stack></Center></Section>`. Sections own the
between-section space; nothing inside them has outer margin.

## Reel — horizontal scroll with snap

```tsx
export function Reel({ gap = 4, className, ...props }: DivProps & { gap?: Gap }) {
  return (
    <div
      className={cn('flex snap-x overflow-x-auto overscroll-x-contain [scrollbar-gutter:stable] *:shrink-0 *:snap-start', GAP[gap], className)}
      {...props}
    />
  );
}
```

Tab rows, chip rows, carousels, thumbnails. Give it a visible affordance (fade edge or arrows) and
keep items keyboard-reachable.

## Cover — full-height with a centered principal

```tsx
export function Cover({ className, ...props }: DivProps) {
  return <div className={cn('flex min-h-dvh flex-col', className)} {...props} />;
}
// Principal child gets `my-auto`; optional header/footer children sit at the ends:
// <Cover><Header/><div className="my-auto">…</div><Footer/></Cover>
```

Hero screens, auth pages, empty full-page states. `min-h-dvh`, never `h-screen`.

## PageShell — document mode

```tsx
export function PageShell({ header, footer, children }: { header?: ReactNode; footer?: ReactNode; children: ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col">
      {header}
      <main className="flex-1">{children}</main> {/* layout-ok: grows with content; the page scrolls */}
      {footer}
    </div>
  );
}
```

The page scrolls. Sticky headers: `sticky top-0 z-40` on the header element.

## AppShell — app-shell mode

```tsx
export function AppShell({ header, sidebar, children }: { header?: ReactNode; sidebar?: ReactNode; children: ReactNode }) {
  return (
    <div className="flex h-dvh flex-col overflow-hidden"> {/* layout-ok: the shell clips; panes scroll */}
      {header && <div className="shrink-0">{header}</div>}
      <div className="flex min-h-0 flex-1">
        {sidebar && <aside className="hidden w-64 shrink-0 overflow-y-auto border-r md:block">{sidebar}</aside>}
        <main className="min-h-0 min-w-0 flex-1 overflow-y-auto [scrollbar-gutter:stable]">{children}</main>
      </div>
    </div>
  );
}
```

The chain is `h-dvh` → `min-h-0 flex-1` → `min-h-0 overflow-y-auto`. Pages rendered inside `main`
must not add another vertical scroll region; they use `Stack`/`Section` and let `main` scroll. A
page that needs its own fixed toolbar renders `flex h-full flex-col` (here `h-full` is legal because
`main` has a constrained height) with `shrink-0` toolbar and `min-h-0 flex-1 overflow-y-auto` body —
and then `main` itself should get `overflow-hidden` for that route (a layout-level decision).

## DialogFrame — a miniature app shell

```tsx
export function DialogFrame({ header, footer, children, className }:
  { header?: ReactNode; footer?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <div className={cn('flex max-h-[calc(100dvh-2rem)] w-full max-w-lg flex-col rounded-xl bg-background shadow-lg', className)}>
      {header && <div className="shrink-0 border-b p-6">{header}</div>}
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-6">{children}</div>
      {footer && <div className="flex shrink-0 flex-wrap justify-end gap-3 border-t p-6">{footer}</div>}
    </div>
  );
}
```

Mount inside an overlay with `fixed inset-0 grid place-items-center p-4`.

## What is deliberately not here

- No `Row` that does not wrap: a non-wrapping row without a plan is the bug this skill exists to
  prevent. Use `Cluster` (wrap), `Split` (content + action), `Switcher` (stack → row), `Reel`
  (scroll).
- No `Spacer` component: spacing is the parent's `gap`.
- No `Box` with margin props: placement is the parent's job; pass `className` for grid/flex
  placement.
