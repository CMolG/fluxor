# Component catalog

One entry per archetype. Each one covers: the **dominant mechanism** (what's at stake
psychologically), the **critical invariants** (the ones most often broken here), **levers**,
**acceptance criteria** (testable) and **warning signs** (what gives a problem away when you look at
the code or the screen).

Contents: [Forms](#forms-and-sign-up) · [Onboarding](#onboarding-and-first-run) ·
[Navigation](#navigation-and-information-architecture) · [Consent](#consent-and-permissions) ·
[Cancellation](#cancellation-unsubscribing-and-downgrades) · [Checkout](#checkout-and-payment) ·
[Destructive actions](#destructive-and-irreversible-actions) · [Notifications](#notifications-and-interruptions) ·
[States](#states-loading-empty-and-error) · [AI/LLM](#ai-and-llm-interfaces) ·
[Tables](#dense-tables-and-dashboards) · [Learning](#learning-and-gamification)

---

## Forms and sign-up

**Dominant mechanism.** Poorly sequenced intrinsic load + dependence on working memory. Every field
is a decision, and every ambiguous decision is a drop-off point.

**Critical invariants:** INV-01 (fields nobody uses), INV-02 (data that's already known),
INV-05 (validation without feedback), INV-07 (a label that doesn't describe what's being asked for).

**Levers:** PRO-03 (group into meaningful steps), PRO-06 (simplify before motivating),
PRO-05 (validation at the right moment).

**Acceptance criteria**
- Every field has an owner who can justify why it's requested and what happens if it's missing.
- Always a visible label; the *placeholder* never doubles as the label (it disappears as you type
  and forces you to remember what went there).
- Correct `autocomplete` on every personal-data field; never block pasting.
- Validate when the user leaves the field, not when they press submit; the message says how to fix
  it, not just that it's wrong.
- Errors don't wipe what was typed or reorder the form.
- Formats are accepted flexibly (spaces in card numbers, dashes in phone numbers) and normalized
  internally.
- Visible, honest progress if there's more than one step; users can go back without losing data.

**Warning signs:** more than 7 ungrouped fields · asterisks with no legend · "required field" as the
only message · the same data requested twice in the flow · a captcha before the price is known.

## Onboarding and first run

**Dominant mechanism.** New users have no automated schemas: their real cognitive cost is far higher
than that of the team that built the product. This is where they either build a correct mental model
or one that will cause errors for months.

**Critical invariants:** INV-01, INV-03 (modal tours that hijack attention), INV-04 (plain language).

**Levers:** PRO-04 (conventions), PRO-03 (progressive disclosure), PRO-08 (desirable difficulty if
the tool is complex: doing, not watching), PRO-07.

**Acceptance criteria**
- The user achieves a real, useful result (not a tour) within the first minute.
- No chained modal tutorials; contextual help available at the point of use.
- Everything can be skipped and found again later.
- What's taught gets practiced (active retrieval) instead of only being shown.
- The initial empty state is the best teacher: it explains what this is and what the first action is.

**Warning signs:** a 5-screen welcome carousel · permission requests before showing any value ·
a mandatory video · no "don't show this again".

## Navigation and information architecture

**Dominant mechanism.** The dorsal pathway and spatial memory. A predictable structure becomes
automatic and frees up resources; an unpredictable one forces users to consciously remap the screen
on every visit.

**Critical invariants:** INV-06 (stability), INV-07 (labels that promise what's behind them),
INV-04 (unlabeled icons).

**Levers:** PRO-04, PRO-07 (Gestalt groupings), PRO-01.

**Acceptance criteria**
- Navigation elements sit in the same position across all views and states.
- Categories use the user's vocabulary, not the company's org chart.
- Always visible: where I am, how I get back, what else is at the same level.
- No icon without a label except universal ones (close, search, back), and even those get an
  `aria-label`.
- Reasonable depth: better a few clear branches than a perfect tree nobody walks.

**Warning signs:** the menu changes between sections · routes that don't match the menu names ·
search used as a patch for a broken taxonomy (a spike in searches right after entering a section).

## Consent and permissions

**Dominant mechanism.** Decision fatigue and visual hierarchy. Regulated territory: asymmetry here is
exactly what the regulations target.

**Critical invariants:** INV-09 (parity), INV-11 (neutral wording), INV-08 (withdrawing consent as
easy as giving it), INV-03.

**Acceptance criteria**
- "Accept all" and "Reject all" are the same type of control, same size, same contrast, same level
  in the hierarchy, on the first layer of the dialog.
- No pre-checked boxes for non-essential purposes.
- One plain sentence explains what is collected and why before asking for the decision.
- Changing your mind later costs at most the same as deciding the first time.
- System permission requests (location, notifications, camera) are preceded by context and happen
  at the moment they add value, never at launch.

**Warning signs:** reject is a gray link · "Manage preferences" leads to 40 toggles while accepting
is one click · the banner comes back on every visit until you accept.

## Cancellation, unsubscribing and downgrades

**Dominant mechanism.** Load asymmetry (*roach motel*). It's the point where accumulated trust gets
destroyed the most and where regulatory exposure is highest.

**Critical invariants:** INV-08, INV-11, INV-10, INV-05.

**Acceptance criteria**
- Count the sign-up steps and the cancellation steps: cancellation ≤ sign-up. Write the number in
  the worksheet.
- The cancel option can be found from the account area, with no search or support in between.
- At most one retention offer, declinable in one click, never repeated.
- Clear confirmation that the cancellation is complete, with the effective date and consequences
  (what happens to the data, whether there's a refund, how long access lasts).
- No "call us to cancel" if the sign-up was online.

**Warning signs:** a mandatory survey before canceling · a gray-on-gray cancel button ·
"Are you sure?" three times · a discount that only applies if you restart the process.

## Checkout and payment

**Dominant mechanism.** Fluency and trust: every incongruent or unexpected element reads as risk.
Loss aversion is at its peak, and any surprise triggers abandonment.

**Critical invariants:** INV-07 (price promised = price charged), INV-10 (real urgency),
INV-02, INV-05, INV-12 (payment is irreversible: a microboundary and a summary before confirming).

**Acceptance criteria**
- Total cost (taxes, shipping, fees) visible from the first step, with no surprises at the end.
- Order summary visible at the moment of confirmation, with the exact verb on the button
  ("Pay €49.90", not "Continue").
- Guest checkout allowed; account creation is offered after the purchase, not before.
- A single goal per screen: no cross-promotions or coupons that open new tabs.
- Unambiguous payment states, including pending or partially failed payments, and an immediate
  receipt.

**Warning signs:** a "your cart expires" countdown · a subscription checked by default on a one-time
purchase · shipping costs that show up on step 4 · insurance added automatically.

## Destructive and irreversible actions

**Dominant mechanism.** Automaticity. A repeated confirmation dialog gets answered without reading
within a few weeks: it stops protecting and only adds cost.

**Critical invariants:** INV-12, INV-05, INV-07.

**Acceptance criteria**
- Reversible → **undo** for a sufficient window, with the notice anchored to the action, no dialog.
- Irreversible → a microboundary proportional to the harm: typing the object's name for severe cases,
  an explicit two-step flow for serious ones, a summary of consequences always.
- The dialog says **exactly what gets deleted** and what depends on it ("3 projects and 240 files").
- The button carries the real verb ("Delete account"), never "OK".
- The destructive action is neither next to nor similar to the frequent action.

**Warning signs:** `onClick={handleDelete}` with no confirmation or undo · silent deletion ·
"Are you sure?" as the only barrier to something unrecoverable.

## Notifications and interruptions

**Dominant mechanism.** Involuntary attentional orienting: an interruption isn't "ignored", it's
paid for. After every interruption, getting back into the task has a cost.

**Critical invariants:** INV-03, INV-01, INV-10.

**Acceptance criteria**
- Nothing interrupts a task in progress unless the interruption is more urgent than the task.
- Batching and silence by default; the user chooses what gets escalated.
- Every notification says what happened and what's expected of the user; if it requires no action,
  it goes to the log, not onto the screen.
- Granular, accessible control, not an all-or-nothing switch buried in settings.

**Warning signs:** a `setInterval` that opens modals · permanent badges for non-urgent content ·
push notifications used as a marketing channel · asking for notification permission in the first
second.

## States: loading, empty and error

**Dominant mechanism.** A pure gulf of evaluation. An undesigned state is the user wondering whether
the system works, and that uncertainty is read as unreliability.

**Critical invariants:** INV-05, INV-07, INV-04.

**Acceptance criteria**
- A perceptible response within ≤100 ms to every tap or click, even if the result takes longer.
- Waiting with meaning: what's being done and, if it's long, real progress ("3 of 7") instead of an
  endless spinner. *Skeletons* only if they preserve the final geometry (otherwise they cause layout
  jumps and break INV-06).
- An empty state that teaches: what goes here, why it's empty and what the first action is.
- Errors with cause, consequence and a way out, in plain language, preserving what the user had
  already done.
- Offline and partial states accounted for: what was saved and what wasn't.
- Disabled always with a visible reason ("2 required fields missing").

**Warning signs:** "Something went wrong" · raw error codes · a spinner with no time ceiling ·
empty screens identical to loading screens · data that pops in and shifts whatever the user was
about to tap.

## AI and LLM interfaces

**Dominant mechanism.** The gulf of envisioning (translating intention into an instruction is hard),
deferred trust and overtrust through fluency, plus the risk of cognitive debt.

**Critical invariants:** INV-05, INV-07 (don't promise capabilities the system doesn't have),
INV-13 in internal reasoning, INV-14 if any biometric signal is captured.

**Levers:** PRO-10 (calibrated transparency), PRO-11 (automate mechanics, not judgment), PRO-03.

**Acceptance criteria**
- The system returns its interpretation of the request before or alongside the result.
- Examples, templates and prompt suggestions available at the point of use.
- Piecewise correction: edit one fragment without redoing everything; history and going back.
- Uncertainty and sources visible where the decision is made, not in a legal notice.
- Limits stated in context ("I have no data after X", "I can't access your account").
- The point where the human exercises judgment is explicitly designed and comfortable.

**Warning signs:** a single text field with no guidance at all · output always presented with the
same tone of certainty · no way to see what it was based on · the user has to copy into another tool
to verify.

## Dense tables and dashboards

**Dominant mechanism.** Ventral pathway fatigue: density that forces decoding every cell, on top of
comparison held in working memory.

**Critical invariants:** INV-01, INV-06, INV-04.

**Acceptance criteria**
- One main question per view; everything else one click away.
- Numbers right-aligned, the same format and precision throughout the column, units in the header.
- Comparisons done by the system (delta, change, benchmark), not by the user subtracting in their
  head.
- Sticky headers, persistent sorting and filters, adjustable density.
- Color encodes at most one dimension and never on its own (always paired with text or shape).

**Warning signs:** 15 equally weighted KPIs with no hierarchy · decorative charts with no question
behind them · legends that force the eye back and forth · horizontal scrolling that loses the headers.

## Learning and gamification

**Dominant mechanism.** The only context where friction is sought on purpose: germane load builds
durable schemas even if it hurts immediate performance.

**Levers:** PRO-08 (retrieval, spacing, interleaving), PRO-07, PRO-05.

**Acceptance criteria**
- Active retrieval before rereading: ask before showing.
- Reviews spread out over time instead of massed blocks.
- Mixed problem types instead of homogeneous sets.
- The extra effort falls on the content, never on the interface: navigation and controls stay
  transparent. A confusing menu isn't a desirable difficulty; it's extraneous load.
- Rewards don't replace the intrinsic motivation of mastering the subject; no hook loops that
  exploit variable intermittent reinforcement.

**Warning signs:** streaks that punish real life · progress lost for not logging in one day ·
"gamification" applied to administrative tasks the user just wants to finish.
