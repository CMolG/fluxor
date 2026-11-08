# Component reuse and evolution

Read this before creating any component, and whenever an existing component "almost" fits.

## 1. The failure this prevents

Two opposite failures produce the same unmaintainable codebase:

- **Duplication:** `Card`, `InfoCard`, `CardV2`, `CustomCard`, `ProjectCard` with copy-pasted
  markup and four slightly different paddings. Fixing spacing means fixing it five times, and
  nobody does.
- **The god component:** one `Card` with `showHeader`, `headerTitle`, `headerAction`,
  `isCompact`, `isInteractive`, `noPadding`, `variant`, `withImage`, `imagePosition`… Every new
  need adds a flag; every flag multiplies the states nobody tested.

The way out of both is the same: **a few small primitives with variants and slots, composed at
the call site.** Reuse means composing them; evolution means adding to them within limits;
creating means a new composition, not a new copy.

## 2. Search first (this is not optional)

Before writing JSX for anything that has a name — card, panel, list, row, header, empty state,
badge, modal, form field, toolbar — spend thirty seconds finding out whether it exists:

1. List the component folders (`components/ui`, `components/layout`, `components/patterns`,
   `features/*/components`, route-private `_components`).
2. Grep for the noun (`Card`, `EmptyState`, `PageHeader`) and for the class signature you were about
   to type (`rounded-xl border p-`, `flex flex-col gap-`). A match on the class signature with a
   different name is still the same component.
3. Read its props and its parts. Note how it is used by other callers (grep `<Card`).

Then classify what you found: exact fit → reuse; near fit → evolve or compose (below); nothing →
create as a composition of primitives, in the lowest layer that has a second consumer (or
route-private if there is only one).

## 3. Evolve, compose, or create

| The gap is… | Do this | Example |
|---|---|---|
| a visual axis (size / tone / density / emphasis) | **evolve** — add a value to the variants map | `Badge` needs "warning" → add `warning: 'bg-amber-50 text-amber-900'` |
| a missing region | **evolve** — add a slot (`children`, a named node prop, or a part) | `Card` needs actions → `Card.Footer` |
| a missing real state | **evolve** — add the state prop mapped to classes/attributes | `Button` needs `loading` (spinner + `aria-busy` + disabled) |
| a different intent or behavior | **compose** — build the new thing from the existing primitives | a clickable "project card" → `<Card asChild><a …>` or `<Link className={…}><Card/></Link>`; not `Card isInteractive` |
| one caller's special case | **compose at the call site** | one page wants a card without padding → `<Card className="p-0">` once; if it happens thrice, add `padding="none"` |
| the same markup appears a third time with the same purpose | **extract** — a new primitive or pattern | three pages hand-roll title + description + actions → `PageHeader` |

The rule of three applies to *layout markup* (three similar rows → a pattern). It does not apply to
primitives that encode design decisions (spacing, focus rings, sizes, accessibility): those are
extracted immediately, because a second copy with a different padding is already a bug.

## 4. Limits: when evolution must stop

Adding to an existing component stops and composition begins when any of these would become true:

1. **A third boolean prop.** Two booleans give four combinations; three give eight, most of which
   nobody designed. Booleans are for real binary state (`disabled`, `loading`, `selected`,
   `open`). "A different look" is a `variant`; "a different region" is a slot.
2. **A prop only one caller will ever pass.** That caller composes instead.
3. **Two props that need a sentence about how they interact** (`compact` changes what `withImage`
   does). The component is now two components.
4. **More than about a third of the JSX branches on props.** The component has become a router
   between layouts; each layout wants to be its own composition.
5. **The name stops being true.** A `Card` that can render a form with validation is not a card.
6. **Props that mirror layout classes** (`marginTop`, `fullWidth`, `align`). Placement belongs to
   the parent; pass `className` for grid/flex placement only.

Hitting a limit is normal. The move is: extract the common core into a smaller primitive, then build
the old component and the new need on top of it. The old callers keep working; the primitive gets
one more consumer; no fork is created.

## 5. Worked example: a correct evolution

Existing:

```tsx
const TONE = {
  neutral: 'bg-muted text-foreground',
  success: 'bg-emerald-50 text-emerald-900',
  danger: 'bg-red-50 text-red-900',
} as const;
const SIZE = { sm: 'px-2 py-0.5 text-xs', md: 'px-2.5 py-1 text-sm' } as const;

export function Badge({ tone = 'neutral', size = 'md', className, ...props }: BadgeProps) {
  return (
    <span
      className={cn('inline-flex items-center gap-1 rounded-full font-medium', TONE[tone], SIZE[size], className)}
      {...props}
    />
  );
}
```

New need: a "warning" badge with a leading icon. Correct evolution — one line for the axis, and
the icon is already possible through `children` (`gap-1` was there for it):

```tsx
const TONE = { …, warning: 'bg-amber-50 text-amber-900' } as const;

<Badge tone="warning"><TriangleAlert className="size-3" /> Expiring</Badge>
```

Incorrect evolutions for the same need: `<Badge isWarning>` (boolean for a look), `<Badge
icon={TriangleAlert} iconPosition="left">` (config props for a slot the children already provide),
or a new `WarningBadge` file (fork).

## 6. Worked example: a correct refusal to evolve

Existing `Card` renders `rounded-xl border bg-card p-4 sm:p-6` with `Card.Header`, `Card.Body`,
`Card.Footer` parts. New need: a selectable project tile with a cover image, keyboard focus, and a
pressed state.

Evolving `Card` would add `selectable`, `selected`, `onSelect`, `image`, `imageAlt`,
`imagePosition` — two booleans, a callback, three config props, and a branch around the whole
tree. Limits 1, 3, 4 and 5 are hit. Compose instead:

```tsx
export function ProjectTile({ project, selected, onSelect }: ProjectTileProps) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onSelect}
      className={cn(
        'group block w-full text-left outline-none',
        'rounded-xl ring-offset-background focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
      )}
    >
      <Card className={cn('transition-colors', selected && 'border-primary bg-primary/5')}>
        <div className="-mx-4 -mt-4 aspect-video overflow-hidden rounded-t-xl sm:-mx-6 sm:-mt-6">
          <img className="size-full object-cover" src={project.cover} alt="" />
        </div>
        <Card.Body className="min-w-0">
          <h3 className="truncate font-medium">{project.name}</h3>
          <p className="line-clamp-2 text-sm text-muted-foreground">{project.summary}</p>
        </Card.Body>
      </Card>
    </button>
  );
}
```

`Card` is untouched and still a card. The negative margins are a local, documented bleed (the one
legitimate use of margin). If a second "tile with cover" appears, the bleed becomes a `Card.Media`
part — evolution of the primitive, triggered by a second consumer, not a guess.

## 7. Composition mechanics that keep components small

- **Parts over props:** `Card.Header / Card.Body / Card.Footer` instead of `title`, `subtitle`,
  `actions`, `footerContent`. Parts are ordinary components sharing the parent's spacing decisions.
- **`children` is the default slot.** Reach for a named node prop (`icon`, `aside`) only when the
  position is fixed and the parent must style around it.
- **Variants via a map**, one map per axis, values are complete literal class strings, defaults in
  the signature. If the project already uses a variants helper library, use it the same way; do not
  mix both styles in one component.
- **`className` last in `cn()`** so callers can win on placement classes; internal structure is not
  exposed for restyling.
- **Layout primitives carry spacing; feature components carry content.** A feature component
  that types `flex flex-col gap-4` is usually a `Stack` that has not been written yet.
- **Accessibility lives in the primitive** (focus ring, `aria-*` wiring, keyboard handling). A copy
  of the markup without it is the main reason duplication is not allowed.

## 8. Promotion rule (where a component lives)

- First consumer: route-private (`app/…/_components`) or inside the feature folder.
- Second consumer in another route/feature: promote to `components/patterns` (still domain-free) or
  keep in the feature and import across — never copy.
- Domain-free, visual only, used everywhere: `components/ui` or `components/layout`.

Promotion moves the file; imports update; the component is not renamed to signal the move. Copying
it "for now" creates the exact duplication this document exists to prevent.

## 9. Self-check before you add a prop

Ask, in this order: Is this placement? (parent's job.) Is this a look? (variant value.) Is this a
region? (slot/part.) Is this a real binary state? (boolean, if you have fewer than three.) Is this
behavior the component did not have? (compose.) Does one caller need it? (compose at the call
site.) If you got to "boolean" and it is the third one, you are at a limit — extract and compose.
