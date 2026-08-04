#!/usr/bin/env bash
# SoulOS estate stamp. Run interactively, with flags, or with a guided setup file.
set -euo pipefail

say() { printf '\n%s\n' "$*"; }
die() { printf '\n%s\n' "$*" >&2; exit 1; }

HERE="$(cd "$(dirname "$0")/.." && pwd)"
AUTHOR=""
SLUG=""
BOOK=""
GHUSER=""
CONFIG=""
SOUL_FILE=""
ONBOARDING=""

usage() {
  cat <<'EOF'
SoulOS estate stamp

  bash scripts/new_estate.sh
  bash scripts/new_estate.sh --config ~/Downloads/soulos-onboarding.json
  bash scripts/new_estate.sh --author "Your Name" --slug your-soul --book "Book One" --interview
  bash scripts/new_estate.sh --author "Your Name" --slug your-soul --book "Book One" --soul /path/to/SOUL.md

Options:
  --config FILE       Guided setup file downloaded from SoulOS Studio
  --author NAME       Name placed on the work
  --slug SLUG         Folder name, lowercase letters, numbers, and dashes
  --book TITLE        Working title of the first book
  --github USER       GitHub username, optional
  --soul FILE         Import an existing SOUL.md and skip the interview
  --interview         Start with the SoulOS voice interview
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --config) [ $# -ge 2 ] || die "--config needs a file."; CONFIG="$2"; shift 2 ;;
    --author) [ $# -ge 2 ] || die "--author needs a name."; AUTHOR="$2"; shift 2 ;;
    --slug) [ $# -ge 2 ] || die "--slug needs a folder name."; SLUG="$2"; shift 2 ;;
    --book) [ $# -ge 2 ] || die "--book needs a title."; BOOK="$2"; shift 2 ;;
    --github) [ $# -ge 2 ] || die "--github needs a username."; GHUSER="$2"; shift 2 ;;
    --soul) [ $# -ge 2 ] || die "--soul needs a Markdown file."; SOUL_FILE="$2"; ONBOARDING="import"; shift 2 ;;
    --interview) ONBOARDING="interview"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1. Run with --help." ;;
  esac
done

if [ -n "$CONFIG" ]; then
  [ -f "$CONFIG" ] || die "Guided setup file not found: $CONFIG"
  CONFIG_VALUES="$(python3 - "$CONFIG" <<'PYCONFIG'
import json, pathlib, re, sys
p = pathlib.Path(sys.argv[1])
try:
    data = json.loads(p.read_text(encoding="utf-8"))
except Exception as exc:
    raise SystemExit("The guided setup file is not valid JSON: " + str(exc))
fields = {
    "author": str(data.get("author", "")).strip(),
    "slug": str(data.get("slug", "")).strip(),
    "book": str(data.get("book", "")).strip(),
    "github": str(data.get("githubUsername", "")).strip(),
    "mode": str(data.get("onboardingMode", "interview")).strip(),
}
if any("\n" in value or "\r" in value for value in fields.values()):
    raise SystemExit("Setup fields may not contain line breaks.")
if fields["mode"] not in {"interview", "import"}:
    raise SystemExit("Choose interview or import for onboardingMode.")
if fields["mode"] == "import":
    soul = str(data.get("soulMarkdown", ""))
    if not soul.strip() or len(soul.encode("utf-8")) > 262144:
        raise SystemExit("Imported SOUL.md must contain text and be no larger than 256 KB.")
for key in ("author", "slug", "book", "github", "mode"):
    print(fields[key])
PYCONFIG
)"
  AUTHOR="$(printf '%s\n' "$CONFIG_VALUES" | sed -n '1p')"
  SLUG="$(printf '%s\n' "$CONFIG_VALUES" | sed -n '2p')"
  BOOK="$(printf '%s\n' "$CONFIG_VALUES" | sed -n '3p')"
  GHUSER="$(printf '%s\n' "$CONFIG_VALUES" | sed -n '4p')"
  ONBOARDING="$(printf '%s\n' "$CONFIG_VALUES" | sed -n '5p')"
fi

say "SOULOS"
say "Four details, then your estate."

if [ -z "$AUTHOR" ]; then read -r -p "Your full name (goes on the work): " AUTHOR; fi
if [ -z "$SLUG" ]; then read -r -p "Estate folder name, lowercase-with-dashes (example: jane-soul): " SLUG; fi
if [ -z "$BOOK" ]; then read -r -p "Working title of your first book: " BOOK; fi
if [ -z "$GHUSER" ] && [ -z "$CONFIG" ]; then read -r -p "GitHub username (leave blank if none yet): " GHUSER; fi

[ -n "$AUTHOR" ] || die "A name is required."
printf '%s' "$SLUG" | grep -Eq '^[a-z0-9]+(-[a-z0-9]+)*$' || die "Use lowercase letters, numbers, and single dashes for the folder name."
[ -n "$BOOK" ] || BOOK="Book One"

if [ -z "$ONBOARDING" ]; then
  printf '\nHow should this estate learn your voice?\n'
  printf '  1. Take the SoulOS voice interview\n'
  printf '  2. Import my existing SOUL.md and skip the interview\n'
  printf 'Choose 1 or 2 [1]: '
  if [ -e /dev/tty ]; then read -r CHOICE </dev/tty; else read -r CHOICE || true; fi
  case "${CHOICE:-1}" in
    2)
      printf 'Path to your SOUL.md: '
      if [ -e /dev/tty ]; then read -r SOUL_FILE </dev/tty; else read -r SOUL_FILE; fi
      ONBOARDING="import"
      ;;
    *) ONBOARDING="interview" ;;
  esac
fi

if [ "$ONBOARDING" = "import" ] && [ -z "$CONFIG" ]; then
  [ -f "$SOUL_FILE" ] || die "SOUL.md not found: $SOUL_FILE"
  [ -s "$SOUL_FILE" ] || die "The selected SOUL.md is empty."
  [ "$(wc -c < "$SOUL_FILE" | tr -d ' ')" -le 262144 ] || die "SOUL.md must be no larger than 256 KB."
fi

DEST="$HOME/dev/$SLUG"
[ ! -e "$DEST" ] || die "Refusing to overwrite: $DEST already exists."
mkdir -p "$HOME/dev"
cp -R "$HERE/template" "$DEST"
cp "$HERE/INTERVIEW.md" "$DEST/INTERVIEW.md"
cp "$HERE/INTERVIEW-LONG.md" "$DEST/INTERVIEW-LONG.md"
cp "$HERE/BRAND-INTERVIEW.md" "$DEST/BRAND-INTERVIEW.md"

python3 - "$DEST" "$AUTHOR" "$SLUG" "$BOOK" "$ONBOARDING" "$CONFIG" "$SOUL_FILE" <<'PYFILL'
import json, pathlib, shutil, sys
dest, author, slug, book, onboarding, config, soul_file = sys.argv[1:]
root = pathlib.Path(dest)
for p in root.rglob("*"):
    if p.is_file() and p.suffix in {".md", ".sh", ".py", ".txt", ".json", ".css", ".html"}:
        text = p.read_text(encoding="utf-8")
        p.write_text(text.replace("{{AUTHOR}}", author).replace("{{SLUG}}", slug).replace("{{BOOK}}", book), encoding="utf-8")
if onboarding == "import":
    if config:
        source = str(json.loads(pathlib.Path(config).read_text(encoding="utf-8")).get("soulMarkdown", ""))
    else:
        source = pathlib.Path(soul_file).read_text(encoding="utf-8")
    if not source.strip():
        raise SystemExit("The imported SOUL.md is empty.")
    (root / "SOUL.md").write_text(source, encoding="utf-8")
PYFILL

printf '%s\n' "$DEST" > "$DEST/scripts/repos.txt"
VERSION="$(tr -d '[:space:]' < "$HERE/VERSION")"
{
  printf 'stamped %s\n' "$(date +%Y-%m-%d)"
  printf 'engine %s\n' "$VERSION"
  printf 'onboarding %s\n' "$ONBOARDING"
} > "$DEST/.soulos-estate"
chmod +x "$DEST/scripts/seal_all.sh" "$DEST/scripts/qc_check.py" "$DEST/scripts/figure.py" "$DEST/scripts/build_book.py" "$DEST/scripts/build_site.py" "$DEST/scripts/update_estate.sh" 2>/dev/null || true

cd "$DEST"
git init -q
if ! git config user.email >/dev/null 2>&1; then
  git config user.name "$AUTHOR"
  git config user.email "estate@local"
fi
git add -A
git commit -q -m "estate stamped: $SLUG"

say "Stamped: $DEST"
if [ "$ONBOARDING" = "import" ]; then
  say "Your SOUL.md was imported exactly as provided. The interview is available later if you ever want to deepen it."
else
  say "Next: open $DEST in your AI tool and paste INTERVIEW.md. Say the answers out loud."
fi
say "Make it look like you: python3 $DEST/scripts/figure.py --preview"
say "Start speaking. Your words land verbatim in outputs/book-evidence/book-one/raw-dictations.md."
if [ -n "$GHUSER" ]; then
  say "On publish day: gh repo create $SLUG --private --source $DEST --push"
else
  say "On publish day, connect your private GitHub repository when you are ready."
fi
say "Nothing leaves without your hand on the seal."
