// The skill is installed into other projects, so what it ships names no project: a tracker key in
// a shipped file is one project's card, meaningless anywhere else. Examples use the PROJ- prefix.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');

function shipped(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const path = join(dir, e.name);
    if (e.isDirectory()) return e.name === 'tests' ? [] : shipped(path);
    return [path];
  });
}

test('no shipped file carries a tracker key other than the PROJ- placeholder', () => {
  const found = shipped(root).flatMap((file) =>
    [...readFileSync(file, 'utf8').matchAll(/\b(?!PROJ-)[A-Z]{2,}-\d+\b/g)]
      .map((m) => `${relative(root, file)}: ${m[0]}`));
  assert.deepEqual(found, []);
});
