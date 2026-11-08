// The worker prompt's template: this skill's protocol, the project's notes, then what changes per session. A session's
// first message is cached as a prefix, so the part that differs between consecutive sessions of a slot (the card the
// supervisor picked, the model, effort and tool tier) goes last: the protocol and the notes before it stay shared.

const SESSION = /\n(?=## This session\n)/;

/** `own` is prompt.md; its `## This session` section, when it has one, moves after `extra` (the project's notes). */
export function composeTemplate(own, extra) {
  const [protocol, session] = own.split(SESSION, 2);
  const notes = extra ? `\n\n## This project\n\n${extra}` : '';
  return session === undefined ? `${own}${notes}` : `${protocol.replace(/\n+$/, '')}${notes.replace(/\n+$/, '')}\n\n${session}`;
}
