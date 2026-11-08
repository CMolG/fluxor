# idea-map-synthesizer: Notes to Capability Pillars

This mod turns the loose notes of a mind map into a few pillars the rest of the flow can work with. It reads only the notes bound to its step, and it keeps what each note meant.

## Rules

1. **Read every bound note.** Each note of a type the step binds is read before any grouping. A note that does not fit a pillar is kept as an orphan, not dropped.
2. **Group by the outcome, not by the wording.** Two notes that want the same result for the reader belong to one pillar, even when their words differ.
3. **Keep the user's intent.** A pillar carries the strategic intent of its notes in the user's terms. Rewording that changes the meaning is not grouping.
4. **Mark the binding mode.** A `primary-input` note drives the pillars. A `read-context` note informs them and is never turned into a pillar on its own.
5. **Name each pillar for its outcome.** A pillar's name says what the reader gets, in plain words.
6. **Report the orphans.** Notes that fit no pillar are listed with the reason, so the author can place them.

## Output

The pillars, each with its name, the notes it groups, the intent it keeps, and the orphans with their reason.
