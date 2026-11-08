// Where the project is and how to reach it: the git root, the shared state directory, the
// configuration, and a runner for git and the other git-side tools.
//
// A project whose root is a WSL path seen from Windows (`\\wsl.localhost\<distro>\...`) is
// detected from the path itself: git, gh and the setup command then run inside that distro through
// `wsl.exe`, because Windows git fails on those paths, while `claude` keeps running natively with
// the UNC path as its cwd. Everywhere else every command runs directly.
import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { hostname } from 'node:os';

const WSL_PATH = /^(?:\\\\|\/\/)wsl(?:\.localhost|\$)[\\/]([^\\/]+)(.*)$/i;

/** `\\wsl.localhost\Ubuntu\home\x` or `//wsl.localhost/Ubuntu/home/x` -> {distro, linux: '/home/x'}. */
export function wslPath(path) {
  const m = WSL_PATH.exec(path ?? '');
  if (!m) return null;
  return { distro: m[1], linux: m[2].replace(/\\/g, '/') || '/' };
}

export const uncOf = (distro, linux) => `\\\\wsl.localhost\\${distro}${linux.replace(/\//g, '\\')}`;

export const DEFAULTS = Object.freeze({
  slots: 2,
  maxSlots: 6,
  worktreeRoot: '~/wt',
  worktreePrefix: 'loop-',
  remote: 'origin',
  baseBranch: 'main',
  targetTemplate: 'feat/cb-{projectTag}-sprint-{sprint}',
  machineName: 'hostname',
  idleMinutes: 30,
  doneGraceSeconds: 120,
  pollSeconds: 15,
  startTimeoutSeconds: 120,
  maxFailedStarts: 3,
  claimTtlMinutes: 15,
  portOffsetStep: 100,
  doneMarker: '.claude/autoloop.done',
  relaunchMarker: '.claude/autoloop.relaunch',
  idleMarker: '.claude/autoloop.idle',
  idleRetryMinutes: 30,
  claude: { command: 'claude', args: ['--dangerously-skip-permissions'] },
  tiers: { enabled: false },
  env: {},
});

/** The tracker statuses a worker may take a card from, in the backlog's pick order. */
export const PHASES = Object.freeze(['review', 'ready', 'todo', 'refine']);

/**
 * `--phases review,ready` -> {phases: ['review', 'ready']}; nothing or `all` -> {phases: null},
 * every phase; an unknown name -> {error}.
 */
export function parsePhases(text) {
  if (text === undefined || text === null || text.trim() === '' || text.trim() === 'all') return { phases: null };
  const asked = text.split(',').map((p) => p.trim().toLowerCase()).filter(Boolean);
  const unknown = asked.filter((p) => !PHASES.includes(p));
  if (unknown.length) return { error: `Unknown phase(s) ${unknown.join(', ')}: use ${PHASES.join(', ')}, or all.` };
  return { phases: PHASES.filter((p) => asked.includes(p)) };
}

/** WSLENV names every variable a Windows process hands on to the commands it runs in WSL. */
export function withWslenv(env, names) {
  const have = (env.WSLENV ?? '').split(':').filter(Boolean);
  const add = names.filter((n) => !have.some((h) => h.split('/')[0] === n));
  return { ...env, WSLENV: [...have, ...add].join(':') };
}

/** Runs `cmd args` on the git side: inside the distro when there is one, directly otherwise. */
export function runner(distro) {
  return (cmd, args, { cwd, input, env, names = [] } = {}) => {
    const r = distro
      ? spawnSync('wsl.exe', ['-d', distro, ...(cwd ? ['--cd', cwd] : []), '--', cmd, ...args], {
          encoding: 'utf8',
          input,
          env: withWslenv(env ?? process.env, names),
          windowsHide: true,
        })
      : spawnSync(cmd, args, { cwd, encoding: 'utf8', input, env: env ?? process.env });
    return { status: r.status ?? 1, stdout: r.stdout ?? '', stderr: (r.stderr ?? '') + (r.error ? String(r.error) : '') };
  };
}

/**
 * The project, from `--root`, `$CLAUDE_PROJECT_DIR` or the cwd (the git top level of whichever).
 * `root` and every path in the result are git-side paths; `fs(path)` turns one into a path this
 * process can open.
 */
export function openContext({ root, env = process.env, cwd = process.cwd() } = {}) {
  const start = root || env.CLAUDE_PROJECT_DIR || cwd;
  const wsl = wslPath(start);
  const distro = wsl?.distro ?? null;
  const run = runner(distro);
  const startCwd = wsl ? wsl.linux : start;
  const git = (args, opts = {}) => run('git', args, { cwd: startCwd, ...opts });
  const top = git(['rev-parse', '--show-toplevel']);
  if (top.status !== 0) throw new Error(`not a git repository: ${start}\n${top.stderr.trim()}`);
  const gitRoot = top.stdout.trim();
  const common = git(['rev-parse', '--path-format=absolute', '--git-common-dir']).stdout.trim();
  const fs = (p) => (distro && p.startsWith('/') ? uncOf(distro, p) : p);
  const home = distro ? run('sh', ['-c', 'cd ~ && pwd']).stdout.trim() : env.HOME ?? env.USERPROFILE ?? '';
  const harness = env.HARNESS_DIR || `${gitRoot}/.harness`;
  const ctx = {
    distro,
    root: gitRoot,
    common,
    stateDir: `${common}/autoloop`,
    home,
    harness,
    fs,
    run,
    git: (args, opts = {}) => run('git', args, { cwd: gitRoot, ...opts }),
    readJson: (p) => readJson(fs(p)),
    expand: (p) => (p.startsWith('~/') ? `${home}${p.slice(1)}` : p),
  };
  ctx.config = { ...DEFAULTS, ...(ctx.readJson(`${harness}/config/autoloop.json`) ?? {}) };
  ctx.config.claude = { ...DEFAULTS.claude, ...(ctx.config.claude ?? {}) };
  return ctx;
}

export function readJson(path) {
  if (!existsSync(path)) return null;
  return JSON.parse(readFileSync(path, 'utf8'));
}

/** The machine name the backlog sees: `hostname`, `env:VAR`, or a literal. */
export function machineName(setting, env = process.env) {
  if (!setting || setting === 'hostname') return env.COMPUTERNAME || hostname();
  if (setting.startsWith('env:')) return env[setting.slice(4)] || hostname();
  return setting;
}

/** The short tag the control branch template uses: config, else the backlog's key prefix. */
export function projectTag(ctx) {
  if (ctx.config.projectTag) return ctx.config.projectTag;
  const backlog = ctx.readJson(`${ctx.harness}/config/backlog.json`);
  if (backlog?.keyPrefix) return backlog.keyPrefix.toLowerCase();
  return ctx.root.split('/').pop().toLowerCase();
}
