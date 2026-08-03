#!/usr/bin/env bash
# The Estate Builder v0. Stamps a complete writing estate: voice law, well, lanes, gates, seal.
set -e

say() { printf '\n%s\n' "$*"; }

HERE="$(cd "$(dirname "$0")/.." && pwd)"

say "THE ESTATE BUILDER v0"
say "Four questions, then the stamp."

printf '\n'
read -r -p "Your full name (goes on the work): " AUTHOR
read -r -p "Estate folder name, lowercase-with-dashes (example: jane-soul): " SLUG
read -r -p "Working title of your first book: " BOOK
read -r -p "GitHub username (leave blank if none yet): " GHUSER

[ -n "$AUTHOR" ] || { echo "A name is required."; exit 1; }
[ -n "$SLUG" ] || { echo "A folder name is required."; exit 1; }
[ -n "$BOOK" ] || BOOK="Book One"

DEST="$HOME/dev/$SLUG"
if [ -e "$DEST" ]; then
  echo "Refusing to overwrite: $DEST already exists."
  exit 1
fi
mkdir -p "$HOME/dev"

cp -R "$HERE/template" "$DEST"
# The interview travels with the estate. Asking someone to go find it inside a
# hidden cache folder is where a non-technical owner gets stuck and stops.
cp "$HERE/INTERVIEW.md" "$DEST/INTERVIEW.md"
cp "$HERE/INTERVIEW-LONG.md" "$DEST/INTERVIEW-LONG.md"

python3 - "$DEST" "$AUTHOR" "$SLUG" "$BOOK" <<'PYFILL'
import sys, pathlib
dest, author, slug, book = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
for p in pathlib.Path(dest).rglob('*'):
    if p.is_file() and p.suffix in {'.md', '.sh', '.py', '.txt'}:
        t = p.read_text(encoding='utf-8')
        t = t.replace('{{AUTHOR}}', author).replace('{{SLUG}}', slug).replace('{{BOOK}}', book)
        p.write_text(t, encoding='utf-8')
PYFILL

printf '%s\n' "$DEST" > "$DEST/scripts/repos.txt"
chmod +x "$DEST/scripts/seal_all.sh" "$DEST/scripts/qc_check.py" 2>/dev/null || true

cd "$DEST"
git init -q
if ! git config user.email >/dev/null 2>&1; then
  git config user.name "$AUTHOR"
  git config user.email "estate@local"
fi
git add -A
git commit -q -m "estate stamped: $SLUG"

say "Stamped: $DEST"
say "Next, in order:"
say "  1. Open $DEST in your AI tool (Claude, Cowork, Codex) and paste in one of"
say "     the two interviews sitting in that folder. Both write your SOUL.md: how"
say "     you sound, so no machine ever smooths you into sounding like everyone"
say "     else. Say the answers out loud rather than typing them."
say "       INTERVIEW.md       12 questions, about 20 minutes. Start here."
say "       INTERVIEW-LONG.md  100 questions, an hour or two. Deeper grain."
say "  2. Start speaking. Everything lands verbatim, dated, in"
say "     outputs/book-evidence/book-one/raw-dictations.md before any shaping."
if [ -n "$GHUSER" ]; then
  say "  3. On publish day: gh repo create $SLUG --private --source $DEST --push"
else
  say "  3. On publish day: make a GitHub account, install gh, then"
  say "     gh repo create $SLUG --private --source $DEST --push"
fi
say "  4. From then on, one command ships everything:"
say "     bash $DEST/scripts/seal_all.sh \"what changed\""
say "The estate works fully offline until publish day. Nothing leaves without your hand on the seal."
