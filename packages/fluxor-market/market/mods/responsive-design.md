# responsive-design: Mobile-First Responsive Layout

Forces mobile-first, fluid layouts with container queries and relative units; forbids fixed pixel widths that break on resize. Every UI surface generated under this modifier must degrade gracefully from the narrowest width the product supports to a full-screen viewport. A component rarely controls the space it is rendered in (a sidebar, a card, a split view, an embed, a resizable panel), so there is no safe assumption about available width.

## Rules

1. **Design mobile-first, then enhance upward.** Write base styles for the smallest target width first and layer complexity upward with `min-width` breakpoints or container query ranges. Never begin from a desktop assumption and strip down.

2. **Fluid units for layout — no fixed pixel widths.** Use `%`, `rem`, `ch`, `fr`, and `clamp()` for widths, font sizes, and spacing. Hard-coded `px` widths on layout elements are forbidden. The exceptions, where `px` is the right unit: minimum touch-target sizes (rule 6), borders, outlines, and shadow blur values.

3. **Prefer container queries for component-level responsiveness.** Use `@container` rules to let components respond to their own available space rather than the global viewport. Viewport media queries are a last resort for page-level structural shifts only.

4. **Responsive images with `srcset` and `sizes`.** Every `<img>` that is not a decorative icon must declare `srcset` and `sizes` attributes so the browser fetches the appropriately sized asset. Use `width` and `height` attributes to prevent layout shift.

5. **Zero horizontal overflow at any viewport width ≥ 320 px.** No element may cause a horizontal scrollbar on any screen at or above 320 px. Use `overflow-x: hidden` only as a last resort and only on a scoping wrapper, never on `body`.

6. **Tap targets must be at least 44 × 44 CSS px.** All interactive elements — buttons, links, toggles, menu items — must meet the WCAG 2.5.5 target-size minimum. This is a minimum size, not a layout width, which is why it is an exception to rule 2. Apply `min-height`/`min-width` or padding rather than expanding the visual footprint where design demands compactness.

7. **Test layout from the narrowest width to full screen.** Verify the component at 320 px, at each breakpoint and container-query threshold the product defines (in its styles or design tokens), and at full screen before considering the implementation complete. Include comments that document tested breakpoints when non-obvious container-query thresholds are used.

8. **Avoid layout patterns that collapse badly.** Multi-column grids must define a sensible `min-width` per column so they reflow to a single column rather than overflow. Absolute-positioned elements must be accounted for in mobile stacking order.

## Behavioral Overrides

- The agent must audit every layout-affecting CSS rule it produces for hardcoded pixel widths and replace any found with fluid equivalents before finalizing output; the exceptions of rule 2 stay in `px`.
- If an existing component uses fixed widths, the agent migrates the values to fluid units on the lines its change already touches and reports the rest instead of rewriting them.
- When a design token or variable resolves to a fixed pixel width at the theme level, the agent must flag the token as a blocker and propose a fluid replacement rather than silently inheriting the breakage.
