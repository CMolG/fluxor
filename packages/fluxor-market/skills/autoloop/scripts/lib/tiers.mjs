// The tools a session gets from the tool tier its role declares. A tier is a launch
// property, not a prompt rule: `toolSurface` gives the flags and the environment `claude` is started
// with, and the project's guard hook reads AUTOLOOP_TOOL_TIER to hold the shell. Pure; the supervisor
// does the launch.

/** What a session may do with its tools, narrowest first. */
export const TIERS = ['read', 'comment', 'write'];

/** The file-writing tools a session below `write` does not get. */
export const DENIED_BELOW_WRITE = ['Edit', 'Write', 'NotebookEdit', 'PowerShell'];

/**
 * The launch arguments and environment that hold a session to its tier. A `write` session, a run with no tier
 * and tiers switched off (`config.enabled` false) launch exactly as they did before the tiers. An unknown tier
 * throws: a session never starts on a tier it cannot read.
 */
export function toolSurface(tier, config) {
  if (!config?.enabled || !tier || tier === 'write') return { args: [], env: {} };
  if (!TIERS.includes(tier)) throw new Error(`a tool tier is one of ${TIERS.join(', ')}, not: ${tier}`);
  return { args: ['--disallowedTools', DENIED_BELOW_WRITE.join(' ')], env: { AUTOLOOP_TOOL_TIER: tier } };
}
