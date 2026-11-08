#!/usr/bin/env node
/**
 * Fluxor Local's catalog seed: writes ONE Liquibase changeset that loads the base marketplace
 * (packages/fluxor-market: roles, mods, steps, flows, hooks, presets and skills) into the harness
 * catalog (fluxor_harness_item) and its file blobs (fluxor_harness_blob).
 *
 *   node scripts/seed-catalog.mjs
 *
 * It builds the market's own content-addressed bundle (tools/marketplace.py build, the format
 * packages/fluxor-market/README.md describes) and maps each atom to a catalog row: a mod is a
 * directive; a role is a directive in the exclusive "role" group; a step and a skill are skills; a
 * hook is a hook with its scripts and fallback inline; a preset is a preset. Each row records the
 * atom's market version and content hash. The output is generated: never edit it by hand, run this
 * again after changing the market and bump the changeset id.
 */
import { spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
export const MARKET_DIR = join(ROOT, 'packages/fluxor-market');
export const CHANGELOG_DIR = join(
  ROOT, 'server/apps/fluxor-local/src/main/resources/db/changelog/fluxor-local');

/**
 * Atoms the market does not validate yet, kept out of the catalog. The seed
 * accepts a failing build only when every error is one of theirs, and fails once a held atom
 * validates, so this list cannot outlive its reason.
 */
export const HELD = new Map([]);

const KEY = /^[a-z0-9][a-z0-9-]{0,63}$/;
const HASH = /^[0-9a-f]{64}$/;
const KINDS = { role: 'directive', mod: 'directive', step: 'skill', flow: 'directive', skill: 'skill', hook: 'hook',
  preset: 'preset', engine: 'skill' };
const FOLDERS = { role: 'roles', mod: 'mods', step: 'steps', flow: 'flows', hook: 'hooks' };
/** The atoms whose inventory card a project with the `atoms` skill gets. */
const ATOMS = new Set(['role', 'mod', 'step', 'flow']);
/**
 * The seed's mapping revision: a row seeded by an earlier mapping is seeded again,
 * as a new version, even when its market content did not change. Earlier changesets are revision 1.
 */
export const SEED = 2;

/** The atom a `marketplace.py validate` error names, from the manifest path it starts with. */
function atomOfError(line) {
  const match = line.match(/^error: (?:(?:meta-)?skills\/([^/]+)\/|market\/[a-z]+\/([^/.]+)\.)/);
  return match ? (match[1] ?? match[2]) : null;
}

/**
 * The catalog items Fluxor's market holds, in the bundle's order (kind, then id): its bundle is
 * built into a temporary directory, and the `held` atoms are left out.
 */
export function marketItems(held = HELD) {
  const out = mkdtempSync(join(tmpdir(), 'harness-catalog-'));
  const run = (...extra) => spawnSync('python3', ['tools/marketplace.py', 'build', '--out', out, ...extra],
    { cwd: MARKET_DIR, encoding: 'utf8' });
  try {
    let result = run();
    const errors = `${result.stdout}${result.stderr}`.split('\n').filter((line) => line.startsWith('error: '));
    if (result.status !== 0) {
      const blocking = errors.filter((line) => !held.has(atomOfError(line)));
      if (blocking.length || !errors.length) {
        throw new Error(`Fluxor's market does not build:\n${blocking.join('\n') || result.stdout + result.stderr}`);
      }
      result = run('--force');
      if (result.status !== 0) throw new Error(`marketplace.py build --force failed:\n${result.stderr}`);
    }
    for (const [id, card] of held) {
      if (!errors.some((line) => atomOfError(line) === id)) {
        throw new Error(`${id} validates now: release it from HELD in scripts/harness-catalog-seed.mjs (${card})`);
      }
    }
    const index = JSON.parse(readFileSync(join(out, 'index.json'), 'utf8'));
    const blob = (sha256) => readFileSync(join(out, 'blobs', sha256));
    const cards = inventoryCards(join(out, 'inventory.json'));
    return withoutBrokenPresets(index.atoms.filter((atom) => KINDS[atom.kind] && !held.has(atom.id))
      .map((atom) => itemOf(atom, blob, cards)));
  } finally {
    rmSync(out, { recursive: true, force: true });
  }
}

/** A preset is seeded only with every item it lists: one held back, or missing, holds it back too. */
export function withoutBrokenPresets(items) {
  const keys = new Set(items.filter((item) => item.kind !== 'preset').map((item) => item.key));
  return items.filter((item) => item.kind !== 'preset' || item.spec.items.every((listed) => keys.has(listed.key)));
}

/**
 * Every card of the bundle's inventory, by name, rendered by Python the way `marketplace.py` renders
 * `inventory.json` (`json.dumps(indent=2, ensure_ascii=False)`), so the snapshot that nests them is
 * byte for byte the file `marketplace.py install` writes.
 */
export function inventoryCards(path) {
  const script = 'import json,sys\ninv=json.load(open(sys.argv[1],encoding="utf-8"))\n'
    + 'print(json.dumps({c["name"]:json.dumps(c,indent=2,ensure_ascii=False) for k in inv for c in inv[k]}))';
  const run = spawnSync('python3', ['-c', script, path], { encoding: 'utf8', maxBuffer: 64 << 20 });
  if (run.status !== 0) throw new Error(`could not render the inventory cards:\n${run.stderr}`);
  return JSON.parse(run.stdout);
}

export function itemOf(atom, blob, cards = {}) {
  const { manifest } = atom;
  if (atom.kind === 'preset') return presetOf(atom);
  if (atom.kind === 'engine') return engineOf(atom, blob);
  const skill = atom.kind === 'skill';
  const prefix = `skills/${atom.id}/`;
  const main = skill ? `${prefix}SKILL.md` : `market/${FOLDERS[atom.kind]}/${atom.id}.md`;
  const file = atom.files.find((f) => f.path === main);
  if (!KEY.test(atom.id)) throw new Error(`${atom.ref}: a catalog key must match ${KEY}`);
  if (!file) throw new Error(`${atom.ref}: the bundle has no ${main}`);
  if (!HASH.test(atom.hash)) throw new Error(`${atom.ref}: unexpected content hash ${atom.hash}`);
  const body = blob(file.sha256).toString('utf8');
  const heading = body.match(skill ? /^# (.+)$/m : /^# [a-z0-9-]+: (.+)$/m);
  return {
    key: atom.id,
    kind: KINDS[atom.kind],
    title: heading ? heading[1].trim() : atom.id,
    description: manifest.description ?? '',
    body,
    spec: { ...(skill ? skillSpec(manifest, atom.files, prefix)
      : atom.kind === 'hook' ? hookSpec(atom, body, blob) : directiveSpec(atom.kind, manifest)),
    ...(ATOMS.has(atom.kind) ? { atom: atom.kind, card: cardOf(atom, cards), ...companions(atom, main) } : {}),
    seed: SEED },
    provenance: `${atom.ref}, from Fluxor's market (packages/fluxor-market)`,
    marketVersion: atom.version,
    contentHash: atom.hash,
    // The bytes of every file `spec.files` (or an atom's `spec.marketFiles`) lists, by sha256: what the blob
    // store serves.
    blobs: new Map(skill || ATOMS.has(atom.kind)
      ? atom.files.filter((f) => skill || f.path !== main).map((f) => [f.sha256, blob(f.sha256)]) : []),
  };
}

/**
 * An atom's files besides its `.md` (a mod's `<id>.config.schema.json` and `.config.example.json`), which
 * the atoms layout writes next to it, as blob references relative to its folder.
 */
function companions(atom, main) {
  const folder = `market/${FOLDERS[atom.kind]}/`;
  const extra = atom.files.filter((f) => f.path !== main);
  return extra.length ? { marketFiles: extra.map((f) => ({ path: f.path.slice(folder.length), sha256: f.sha256,
    size: f.size, executable: f.executable })) } : {};
}

function cardOf(atom, cards) {
  if (typeof cards[atom.id] !== 'string') throw new Error(`${atom.ref}: the bundle's inventory has no card for it`);
  return cards[atom.id];
}

/** The engine (`motor.py`, `lexicon.json`) as a skill whose files a project with `atoms` gets under `market/`. */
function engineOf(atom, blob) {
  if (!KEY.test(atom.id)) throw new Error(`${atom.ref}: a catalog key must match ${KEY}`);
  if (!HASH.test(atom.hash)) throw new Error(`${atom.ref}: unexpected content hash ${atom.hash}`);
  return {
    key: atom.id,
    kind: 'skill',
    title: 'Atoms engine',
    description: atom.manifest.description ?? '',
    body: atom.manifest.description ?? '',
    spec: { atom: 'engine', seed: SEED,
      files: atom.files.map((f) => ({ path: f.path.replace(/^market\//, ''), sha256: f.sha256, size: f.size,
        executable: f.executable })) },
    provenance: `${atom.ref}, from Fluxor's market (packages/fluxor-market)`,
    marketVersion: atom.version,
    contentHash: atom.hash,
    blobs: new Map(atom.files.map((f) => [f.sha256, blob(f.sha256)])),
  };
}

/** A preset has no files: its title and items are its manifest's, its body the description. */
function presetOf(atom) {
  const { manifest } = atom;
  if (!KEY.test(atom.id)) throw new Error(`${atom.ref}: a catalog key must match ${KEY}`);
  if (!HASH.test(atom.hash)) throw new Error(`${atom.ref}: unexpected content hash ${atom.hash}`);
  return {
    key: atom.id,
    kind: 'preset',
    title: manifest.title,
    description: manifest.description,
    body: manifest.description,
    spec: { items: manifest.items, seed: SEED, ...(manifest.precedenceTemplates && { precedenceTemplates: manifest.precedenceTemplates }) },
    provenance: `${atom.ref}, from Fluxor's market (packages/fluxor-market)`,
    marketVersion: atom.version,
    contentHash: atom.hash,
    blobs: new Map(),
  };
}

function directiveSpec(kind, manifest) {
  // A step is invoked when needed, a flow read when it is run; any other directive is always read.
  const spec = kind === 'step' ? {} : { activation: kind === 'flow' ? 'on-demand' : 'always' };
  if (kind === 'role') spec.exclusiveGroup = 'role';
  // the tools a session that works the role may use; Officium serves it per role.
  if (kind === 'role' && manifest.toolTier) spec.toolTier = manifest.toolTier;
  if (manifest.exclusiveGroup) spec.exclusiveGroup = manifest.exclusiveGroup;
  if (manifest.incompatibleWith?.length) spec.incompatibleWith = manifest.incompatibleWith;
  if (manifest.domains?.length) spec.domains = manifest.domains;
  if (manifest.tags?.length) spec.tags = manifest.tags;
  // the mods a role needs (), and how a mod ranks against another.
  if (manifest.requires?.atoms?.length) spec.requires = manifest.requires.atoms;
  if (manifest.precedence) spec.precedence = manifest.precedence;
  if (manifest.enforcement) spec.enforcement = manifest.enforcement;
  return spec;
}

/**
 * A hook's spec is what `HarnessSnapshotService.hookFiles` reads: the event, the scripts as text, and
 * the fallback (fluxor/003 refuses a hook row without one). `sends` is for the people who consent.
 */
function hookSpec(atom, fallback, blob) {
  const { manifest } = atom;
  const spec = { event: manifest.event, fallback };
  for (const kind of ['sh', 'ps1']) {
    const file = atom.files.find((f) => f.path === `market/hooks/${atom.id}.${kind}`);
    if (file) spec[kind] = blob(file.sha256).toString('utf8');
  }
  for (const field of ['tools', 'notifications', 'timeoutMs']) {
    if (manifest[field] !== undefined) spec[field] = manifest[field];
  }
  spec.sends = manifest.sends;
  return spec;
}

/** A skill is a folder: `body` is its SKILL.md, `files` what installing the whole folder writes. */
function skillSpec(manifest, files, prefix) {
  const spec = { packaging: manifest.packaging };
  // A meta-skill's form (its questions, profile and templates), which Fluxor renders.
  if (manifest.form) spec.form = manifest.form;
  if (manifest.requires?.atoms?.length) spec.requires = manifest.requires.atoms;
  if (manifest.domains?.length) spec.domains = manifest.domains;
  if (manifest.tags?.length) spec.tags = manifest.tags;
  // the file under .harness/config/ a project's params for the skill are written to.
  if (manifest.config?.file) spec.config = { file: manifest.config.file };
  spec.files = files.map((f) => ({ path: f.path.slice(prefix.length), sha256: f.sha256, size: f.size,
    executable: f.executable }));
  return spec;
}

const literal = (value) => `'${String(value).replaceAll("'", "''")}'`;

/** One statement per item: a new version only when the newest one carries a different hash. */
export function itemSql(item) {
  const newest = `(select max(version) from fluxor_harness_item where key = ${literal(item.key)})`;
  return [
    'insert into fluxor_harness_item',
    '  (key, version, kind, title, description, body, spec, provenance, market_version, content_hash)',
    `select ${literal(item.key)}, coalesce(${newest}, 0) + 1, ${literal(item.kind)}, ${literal(item.title)},`,
    `  ${literal(item.description)},`,
    `  ${literal(item.body)},`,
    `  ${literal(JSON.stringify(item.spec))}::jsonb, ${literal(item.provenance)},`,
    `  ${literal(item.marketVersion)}, ${literal(item.contentHash)}`,
    'where not exists (',
    `  select 1 from fluxor_harness_item i where i.key = ${literal(item.key)} and i.version = ${newest}`,
    `    and i.content_hash = ${literal(item.contentHash)} and i.spec ->> 'seed' = '${SEED}');`,
  ].join('\n');
}

/** One blob, idempotent: the same bytes always have the same key. */
export function blobSql(sha256, content) {
  return `insert into fluxor_harness_blob (sha256, content, size) values ('${sha256}', `
    + `decode('${content.toString('base64')}', 'base64'), ${content.length}) on conflict (sha256) do nothing;`;
}

export function renderChangeset(id, items, held = HELD, blobs = new Map()) {
  const indent = (text) => text.split('\n').map((line) => (line ? `              ${line}` : '')).join('\n');
  const statement = (sql) => [
    '        - sql:',
    '            splitStatements: false',
    '            stripComments: false',
    '            sql: |',
    indent(sql),
  ].join('\n');
  const changes = [...items.map((item) => statement(itemSql(item))),
    ...[...blobs].map(([sha, content]) => statement(blobSql(sha, content)))];
  const heldNote = held.size
    ? ` Held back until they validate: ${[...held].map(([key, card]) => `${key} (${card})`).join(', ')}.`
    : '';
  return [
    'databaseChangeLog:',
    '  - changeSet:',
    `      id: ${id}`,
    '      author: fluxor-local',
    '      context: default',
    '      comment: >',
    "        GENERATED by scripts/seed-catalog.mjs from Fluxor's market bundle",
    '        (packages/fluxor-market); never edit it by hand. Seeding a newer market is a new',
    '        changeset from the same script, which only carries the items whose content hash changed.',
    `        ${items.length} items${blobs.size ? `, ${blobs.size} skill-file blobs` : ''}.${heldNote}`,
    '      changes:',
    ...changes,
    '',
  ].join('\n');
}


function main(argv) {
  const id = argv[0] ?? '100-local-catalog';
  if (!/^\d{3}-[a-z0-9-]+$/.test(id)) {
    console.error('usage: node scripts/seed-catalog.mjs [NNN-changeset-name]');
    return 2;
  }
  const items = marketItems();
  const blobs = new Map(items.flatMap((item) => [...item.blobs]));
  const sorted = new Map([...blobs].sort(([a], [b]) => a.localeCompare(b)));
  const file = join(CHANGELOG_DIR, id + '.yaml');
  writeFileSync(file, renderChangeset(id, items, HELD, sorted));
  console.log('Wrote ' + items.length + ' items and ' + sorted.size + ' blobs to ' + file);
  return 0;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) process.exit(main(process.argv.slice(2)));
