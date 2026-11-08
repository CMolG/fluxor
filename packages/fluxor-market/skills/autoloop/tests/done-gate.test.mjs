// The done gate (card://JAVA-2004): `done` is refused while the tracker says the held unit still has work for this
// session, a forced exit names a reason from a closed list, and a check that cannot answer never traps a session.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { FORCED, gate } from '../scripts/lib/finish.mjs';

const h = (answer, config = { doneCheck: { command: 'check' } }) => {
  const asked = [];
  return { asked, ctx: { config }, ask: (command, env) => { asked.push({ command, env }); return answer; } };
};

test('an open unit refuses the done, naming the card and the reason', () => {
  const worker = h({ open: true, key: 'JAVA-1598', reason: 'JAVA-1601 is the checkpoint the sweep builds now' });
  const verdict = gate(worker, ['JAVA-1598']);
  assert.match(verdict.refused, /JAVA-1598 still has work for this session: JAVA-1601 is the checkpoint/);
  assert.match(verdict.refused, /--forced run-killed\|environment\|context/);
  assert.deepEqual(worker.asked, [{ command: 'check', env: { AUTOLOOP_CARD: 'JAVA-1598' } }]);
});

test('a closed unit, no held card, no configured check or a forced exit lets it through unasked', () => {
  assert.deepEqual(gate(h({ open: false }), ['PROJ-1']), {});
  const none = h({ open: true });
  assert.deepEqual(gate(none, []), {});
  assert.deepEqual(gate(h({ open: true }, {}), ['PROJ-1']), {});
  const forced = h({ open: true });
  assert.deepEqual(gate(forced, ['PROJ-1'], 'run-killed'), {});
  assert.equal(none.asked.length + forced.asked.length, 0);
});

test('a check that cannot answer warns and lets the done through', () => {
  assert.match(gate(h(null), ['PROJ-1']).warning, /could not answer/);
  assert.match(gate(h({ open: null, reason: 'network error' }), ['PROJ-1']).warning, /could not answer/);
});

test('the forced reasons are a closed list', () => {
  assert.deepEqual(FORCED, ['run-killed', 'environment', 'context']);
});
