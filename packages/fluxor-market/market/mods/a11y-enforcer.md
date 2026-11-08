# a11y-enforcer: WCAG 2.2 Accessibility Enforcement Modifier

When this modifier is active, all generated UI elements must meet WCAG 2.2 Level AA, measured. AA is the floor. A project whose design contract declares AAA applies the AAA thresholds listed with each rule instead. Accessibility is not a feature: it is a non-negotiable requirement, verified by measurement, never assumed.

## Rules

1. **ARIA labels required.** Every interactive element (button, link, input, select, checkbox, radio) must have an accessible name via visible text content, `aria-label`, or `aria-labelledby`. No unnamed interactive elements.
2. **Semantic HTML first.** Use native HTML elements (`<button>`, `<nav>`, `<main>`, `<article>`, `<header>`) before reaching for ARIA roles. A `<div onClick>` is never acceptable — use `<button>`.
3. **Focus management.** All interactive elements must be keyboard-accessible via Tab/Shift+Tab. Custom focus order is set via `tabIndex` only when the DOM order is insufficient. Focus traps are implemented for modals and dialogs. Focus is always visible and never fully hidden by sticky or overlaying content (SC 2.4.7, 2.4.11); with AAA, no part of the focused element is hidden (SC 2.4.12) and the indicator meets SC 2.4.13.
4. **Color contrast, measured per state.** AA: normal text at least 4.5:1, large text (18pt+ or 14pt+ bold) at least 3:1, and UI components and meaningful graphics at least 3:1 against what they sit on (SC 1.4.3, 1.4.11). AAA, when the project declares it: 7:1 and 4.5:1 for text (SC 1.4.6). The ratio is calculated from computed colors in every interactive state (rest, hover, focus-visible, active) and on every surface the element appears on; disabled controls are exempt, as WCAG states. A token's name is not evidence.
5. **No information by color alone.** Color must not be the only means of conveying information. Use icons, patterns, text labels, or underlines in addition to color.
6. **Screen reader compatibility.** Dynamic content changes must be announced via `aria-live` regions. Form errors must be associated with their inputs via `aria-describedby`. Loading states must be communicated via `aria-busy`.
7. **Motion and animation.** Respect `prefers-reduced-motion`. All animations must have a reduced-motion alternative that conveys the same information without movement.
8. **Target size.** AA: every pointer target is at least 24x24 CSS pixels, or keeps a 24 px spacing circle clear of other targets (SC 2.5.8). AAA, when the project declares it: 44x44 CSS pixels (SC 2.5.5). Measured from the rendered box, at every width the layout is checked at. The SC's own exceptions still apply (a link inline in a sentence, a target with an equivalent control that meets the size, a size the user agent sets, an essential presentation): a finding names which one exempts the target, or the target fails.
9. **Composite widgets follow WAI-ARIA Authoring Practices exactly.** For grids, listboxes, comboboxes, menus, tabs, tree views, and date pickers:
   - Mark selectable items with `aria-selected` (or `aria-checked`) — a screen reader must be able to tell which items are selected. Missing `aria-selected` on a selected cell is a hard failure.
   - Use **roving `tabindex`**: exactly one tab stop for the whole widget, with arrow keys (and Home/End/PageUp/PageDown where appropriate) moving focus inside it.
   - Use **semantic headings** (`<h1>`–`<h6>`), never `role="heading"` on a `<div>`.
   - Avoid `role="application"` unless you fully reimplement browser keyboard semantics; it traps assistive-tech navigation otherwise.
   - Every ARIA state you style in CSS must actually be set in JS — no dead `aria-*` rules.
10. **Landmark uniqueness.** Exactly one `<main>` per page, and one top-level banner `<header>` / `contentinfo` `<footer>`. When an app shell already renders the `<main>` (or header/footer) landmark, page components render `<section>`s INSIDE it — never nest a second `<main>` or emit a duplicate top-level `<header>`, which breaks landmark navigation and the skip-link target. Exactly one `<h1>` per page.

## Behavioral Overrides

- The agent audits every UI element it creates or modifies against the configured level (AA unless the project declares AAA) before committing, and attaches the measured results; an unmeasured criterion is reported as not verified, never as passing.
- If an existing component the agent is modifying fails accessibility standards, the agent fixes the violations on the lines its change already touches and reports the rest instead of fixing them.
- The agent must test keyboard navigation flow after every UI change and verify logical tab order.
