// A Refine card with no workflow is worked first in a workflow session (card://JAVA-1593): both the
// backlog protocol and the loop's prompt say so, name the mod that writes it and the run cell it
// runs on, and put that session before the planning one.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const backlog = readFileSync(join(root, '..', 'backlog', 'SKILL.md'), 'utf8');
const prompt = readFileSync(join(root, 'prompt.md'), 'utf8');

for (const [name, text] of [['backlog SKILL.md', backlog], ['autoloop prompt.md', prompt]]) {
  test(`${name} names the workflow-author mod and the workflow run cell`, () => {
    assert.match(text, /workflow-author/);
    assert.match(text, /`workflow` cell/);
  });

  test(`${name} writes the workflow session before the planning session`, () => {
    const workflow = text.indexOf('workflow session');
    assert.notEqual(workflow, -1, 'no workflow session');
    assert.ok(text.indexOf('planning session', workflow) > workflow, 'planning comes after the workflow session');
  });
}

test('the backlog protocol degrades on a tracker without workflows', () => {
  assert.match(backlog, /workflowSchema/);
});
