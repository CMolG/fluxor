// An epic handed out with a sweep is worked in ONE session (card://JAVA-1872, epic JAVA-1868): the prompt says how,
// the backlog protocol knows the epic is a unit in epic mode, and what changes per session comes last in the template,
// after the project's notes, so consecutive sessions of a slot share the longest prefix.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { composeTemplate } from '../scripts/lib/template.mjs';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const prompt = readFileSync(join(root, 'prompt.md'), 'utf8');
const backlog = readFileSync(join(root, '..', 'backlog', 'SKILL.md'), 'utf8');

test('the prompt sweeps an epic checkpoint by checkpoint in one session and never relaunches mid-epic', () => {
  const flat = prompt.replace(/\s+/g, ' ');
  for (const needle of ['cards.setCheckpoint', '`sweep`', 'never relaunch once the first checkpoint', 'After a compaction',
    'wt/<EPIC>', 'reviewed whole']) {
    assert.ok(flat.includes(needle), `prompt.md lacks: ${needle}`);
  }
});

// card://JAVA-2001: 33 sessions on two epics nobody could move. Each rule below closes one way a session left a unit
// as it found it, so the next session got the same unit: a resume read the epic's column instead of its sweep, a
// sweep's `next` was refused over a sibling in Review, and a card that could not run was released with a comment.
test('the prompt never leaves a unit as it found it', () => {
  const flat = prompt.replace(/\s+/g, ' ');
  for (const needle of ['Read it as its unit**: `cards.unit {key}`', "never in the epic's own `phase` on `cards.get`",
    'Never release a sweep because `next` reads as blocked', 'raise its wall once (`cards.requestHuman`',
    'never one to leave as you found it', 'A unit in Review is never refused']) {
    assert.ok(flat.includes(needle), `prompt.md lacks: ${needle}`);
  }
});

// Consecutive sessions come from different slots, so the per-slot values wait for the end too: every slot of a
// loop reads the same protocol (card://JAVA-1872, sent back on 2026-10-28 for {{SLOT}} on the first line).
test('the per-slot and per-session values come after the project notes, and nowhere before them', () => {
  const composed = composeTemplate(prompt, 'Project notes, the same for every session.');
  const notes = composed.indexOf('## This project');
  const session = composed.indexOf('## This session');
  assert.ok(notes > 0 && session > notes, 'This session follows This project');
  for (const placeholder of ['{{CARD}}', '{{MODEL}}', '{{EFFORT}}', '{{TIER}}', '{{SLOT}}', '{{MACHINE}}',
    '{{WORKTREE}}', '{{PORT_OFFSET}}']) {
    assert.ok(composed.indexOf(placeholder) > session, `${placeholder} only in This session`);
  }
});

test('a template with no session section keeps its old shape', () => {
  assert.equal(composeTemplate('Protocol.\n', 'Notes'), 'Protocol.\n\n\n## This project\n\nNotes');
  assert.equal(composeTemplate('Protocol.\n', ''), 'Protocol.\n');
});

test('the backlog protocol treats an epic as a unit in epic mode', () => {
  for (const needle of ['projects.executionMode', 'sweep', 'cards.setCheckpoint', '`next` is always buildable',
    'reads it as its unit']) {
    assert.ok(backlog.includes(needle), `backlog SKILL.md lacks: ${needle}`);
  }
});
