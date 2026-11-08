# Structure

Read this when creating files or folders, bootstrapping a project, or deciding where a component
belongs. Structure is not tidiness: with a file-system router, folders *are* the routing, the
layouts, and the loading/error boundaries, and the layer a component lives in *is* its reuse scope.

## 1. Layers

```
src/
  app/                        routes only
    layout.*                  root shell: html/body, fonts, providers, the viewport owner (document mode by default)
    (marketing)/layout.*      route group: PageShell (document mode)
    (app)/layout.*            route group: AppShell (app-shell mode) — the only other viewport owner
    (app)/dashboard/
      page.*                  composes features + patterns; ~no raw layout classes
      loading.* error.*       same footprint as page.* to avoid layout shift
      _components/            route-private pieces (underscore = never a route)
  components/
    ui/                       primitives: button, input, select, checkbox, badge, card, dialog, tooltip…
                              variants via maps, parts (Card.Header…), accessibility wiring, no domain words
    layout/                   Stack, Cluster, Split, Switcher, Sidebar, AutoGrid, Center, Section, Reel, Cover, PageShell, AppShell, DialogFrame
    patterns/                 composed, domain-free: PageHeader, EmptyState, FormField, FieldGroup, DataTableShell, Toolbar, StatCard
  features/
    <domain>/                 e.g. billing/, projects/, auth/
      components/             domain components composed from ui + layout + patterns
      hooks/  queries/  types.ts
  lib/
    utils.ts                  cn() and small helpers
  hooks/                      cross-domain hooks
  styles/globals.css          theme tokens (colors, spacing additions, fonts), base layer only
```

`src/` is optional; keep whatever the project already uses. What matters is the four layers and
their direction of dependency: **routes → features → patterns → layout/ui**. Never the reverse (a
primitive importing a feature) and never sideways between features (extract to patterns instead).

## 2. What a `layout` file may do

- Own the viewport height: choose document mode (`PageShell`) or app-shell mode (`AppShell`). This
  is the *only* place that decision is made.
- Render persistent chrome (header, sidebar, footer) and providers.
- Render `{children}` inside the shell's scroll region.

What it may not do: render page content, fetch page data, add a second scroll region, or apply
`overflow-hidden` "just in case". A nested layout that needs a fixed toolbar over a scrolling area
converts its slot into a sub-shell (`flex h-full flex-col`, `shrink-0` toolbar, `min-h-0 flex-1
overflow-y-auto` body) and documents it in a comment.

## 3. What a `page` file may do

Compose: `<Section><Center><Stack gap={8}><PageHeader … /><ProjectList … /></Stack></Center></Section>`.
A page with more than a handful of raw utility classes is doing a primitive's job; a page with its
own `flex-1 overflow-y-auto` is doing a layout's job.

## 4. Where a new component goes

| It is… | It lives in… |
|---|---|
| used by one route, contains route-specific wiring | `app/<route>/_components/` |
| domain-specific, used by several routes of the same domain | `features/<domain>/components/` |
| domain-free composition used by ≥ 2 features/routes | `components/patterns/` |
| a visual primitive with variants and no domain words | `components/ui/` |
| a spacing/wrapping/containment decision | `components/layout/` |

Promotion moves the file upward when a second consumer appears; it never copies. Demotion is
rare; if a `ui` component has grown domain words, split the domain part into a feature component
that composes the cleaned primitive.

## 5. Naming and file rules

- One component per file; the file is named after the component in the repo's existing casing
  (do not introduce a second convention). Parts live with their parent (`card.tsx` exports `Card`,
  `CardHeader`, … or the `Card.Header` compound).
- Exports: follow the repo (named vs default). Do not mix within a folder.
- Variant maps live next to the component that uses them; shared tokens live in the theme, not in
  a `constants.ts` of class strings.
- Route-private folders start with `_`; route groups use `(name)`; both are invisible in URLs.
- Tests and stories sit beside the component when the repo colocates them.

## 6. Bootstrapping a new project

1. `lib/utils.ts` with `cn()`.
2. `components/layout/` from `references/layout-primitives.md`.
3. Theme tokens in the global stylesheet (colors, fonts, any spacing additions) — before the first
   feature, so the first feature does not hard-code values.
4. Root `layout` with document mode; an `(app)` group with `AppShell` only if the product has a
   persistent chrome.
5. `components/ui/` primitives as they are needed — button, input, card, dialog first — each with
   variant maps and parts, never with margin.
6. First feature composed from the above; when the second feature appears, promote what is shared.

## 7. Signs the structure is drifting

- A `components/` folder with 200 flat files → split into the layers above.
- `utils`, `helpers`, `common`, `shared`, `misc` folders → rename by what they contain.
- Two files with the same component name in different folders → one is a fork; merge.
- Page files containing `flex-1 overflow-y-auto` → the layout should own it.
- Feature components importing each other across domains → extract a pattern.
- A `ui` component with a domain word in its props (`invoice`, `customer`) → split.
