#!/usr/bin/env sh
# Stable entry point for review-harness: hooks and CI call this path. The checks live in
# review.py (Python 3 standard library only). See SKILL.md.
#
# Exit 0: nothing broken (warnings allowed). Exit 1: at least one check FAILS.
# Without python3 it fails open, like every harness hook: it says the review did not run and
# exits 0, so a missing interpreter never blocks a session.

case "$0" in
  */*) here=${0%/*} ;;
  *) here=. ;;
esac

for py in python3 python; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c 'import sys; sys.exit(sys.version_info < (3, 8))' 2>/dev/null; then
    exec "$py" "$here/review.py" "$@"
  fi
done

echo "  WARN   python3 (3.8+) not found: the harness was NOT reviewed. Install python3 and run again."
exit 0
