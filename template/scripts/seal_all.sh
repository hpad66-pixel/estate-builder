#!/usr/bin/env bash
# The seal. Commits and pushes every repo listed in scripts/repos.txt.
# One way, one door, your hand on it.
set -e
LIST="$(cd "$(dirname "$0")" && pwd)/repos.txt"
MSG="${1:-Estate update $(date +%Y-%m-%d)}"
[ -f "$LIST" ] || { echo "No repos.txt beside this script."; exit 1; }
while IFS= read -r R; do
  [ -n "$R" ] || continue
  [ -d "$R/.git" ] || continue
  cd "$R"
  find .git \( -name "*.lock" -o -name "tmp_obj_*" \) -delete 2>/dev/null || true
  if [ -n "$(git status --porcelain)" ]; then
    git add -A
    git commit -m "$MSG"
    git push 2>/dev/null || echo "  (no remote yet; sealed locally)"
    echo "sealed: $(basename "$R")"
  else
    git push >/dev/null 2>&1 || true
    echo "clean:  $(basename "$R")"
  fi
done < "$LIST"
