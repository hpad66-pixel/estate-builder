#!/usr/bin/env bash
# Refresh an estate that already exists with the current engine.
#
# The stamp is a one-time copy. Without this, an estate is frozen at whatever
# version of the engine it was stamped from, and every improvement made later
# never reaches the people who already installed. This is the other half.
#
#   bash scripts/update_estate.sh              # update the estate this script sits in
#   bash scripts/update_estate.sh --dry-run    # show what would change, touch nothing
#   bash scripts/update_estate.sh --from ~/dev/estate-builder
#
# What it refreshes: the engine's own files. Scripts, style presets, the lane
# templates, the operating rules, the interviews.
#
# What it never touches: SOUL.md, brand/brand.json, your logo, your chapters,
# your figures, your dated article folders, the well, and scripts/repos.txt.
# Your work and your identity are yours. Anything replaced is backed up first.
set -e

ESTATE="$(cd "$(dirname "$0")/.." && pwd)"
ENGINE="${SOULOS_HOME:-$HOME/.soulos-engine}"
DRY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --from) ENGINE="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

say() { printf '\n%s\n' "$*"; }

[ -d "$ENGINE/template" ] || {
  echo "No engine found at $ENGINE"
  echo "Re-run your install command to refresh it, or pass --from <path-to-estate-builder>."
  exit 1
}

if [ ! -f "$ESTATE/.soulos-estate" ]; then
  echo ""
  echo "This folder was not stamped by the engine: no .soulos-estate marker."
  echo "Refusing to run. This updater replaces CLAUDE.md, AGENTS.md, the lane"
  echo "templates and the scripts, which would overwrite the operating rules of a"
  echo "hand-built repository."
  echo ""
  echo "If you know this is an estate, run --dry-run first, then create the marker"
  echo "yourself: touch .soulos-estate"
  exit 1
fi

say "Updating: $ESTATE"
say "From engine: $ENGINE"

if [ -d "$ESTATE/.git" ] && [ -n "$(cd "$ESTATE" && git status --porcelain)" ] && [ "$DRY" = "0" ]; then
  printf '\nYou have uncommitted work in this estate. Seal it first so anything\n'
  printf 'replaced here is recoverable from git as well as from the backup.\n'
  printf 'Continue anyway? [y/N] '
  if [ -e /dev/tty ]; then read -r ans </dev/tty; else ans="n"; fi
  case "$ans" in y|Y|yes|YES) ;; *) echo "Stopped. Nothing changed."; exit 0 ;; esac
fi

python3 - "$ESTATE" "$ENGINE" "$DRY" <<'PYUP'
import sys, os, shutil, pathlib, re, time, filecmp

estate, engine, dry = sys.argv[1], sys.argv[2], sys.argv[3] == "1"
E, G = pathlib.Path(estate), pathlib.Path(engine)

# Engine-owned. Refreshed on update. Everything else in the estate is the
# owner's and is never touched.
OWNED = [
    "CLAUDE.md", "AGENTS.md", "CONTENT-MAP.md",
    "INTERVIEW.md", "INTERVIEW-LONG.md", "BRAND-INTERVIEW.md",
    "scripts/figure.py", "scripts/build_book.py", "scripts/qc_check.py", "scripts/seal_all.sh",
    "scripts/update_estate.sh",
    "brand/README.md",
    "book/ART.md", "book/chapters/README.md", "book/figures/README.md",
    "articles/README.md",
    "articles/_template/article.md", "articles/_template/substack.md",
    "articles/_template/linkedin.md", "articles/_template/figures/README.md",
    "courses/README.md", "docs/README.md",
    "outputs/book-compiled/README.md",
]
OWNED_GLOBS = ["brand/styles/*.json"]

# Never, under any circumstances.
PROTECTED = {"SOUL.md", "brand/brand.json", "scripts/repos.txt"}

# Recover the owner's details so refreshed files get filled in the same way the
# stamp filled them.
author = ""
bj = E / "brand" / "brand.json"
if bj.exists():
    m = re.search(r'"owner"\s*:\s*"([^"]*)"', bj.read_text(encoding="utf-8"))
    if m:
        author = m.group(1)
if not author and (E / "SOUL.md").exists():
    m = re.search(r"the voice law of (.+)", (E / "SOUL.md").read_text(encoding="utf-8"))
    if m:
        author = m.group(1).strip()
slug = E.name
book = ""
well = E / "outputs" / "book-evidence" / "book-one" / "raw-dictations.md"
if well.exists():
    m = re.search(r"Book One · (.+)", well.read_text(encoding="utf-8"))
    if m:
        book = m.group(1).strip()

if not author:
    print("Could not work out the owner's name from this estate. Stopping rather than")
    print("writing {{AUTHOR}} into your files.")
    sys.exit(1)


def fill(t):
    return t.replace("{{AUTHOR}}", author).replace("{{SLUG}}", slug).replace("{{BOOK}}", book or "Book One")


targets = list(OWNED)
for pat in OWNED_GLOBS:
    d = (G / "template" / pat).parent
    if d.is_dir():
        for f in sorted(d.glob(pathlib.Path(pat).name)):
            targets.append(str(pathlib.Path(pat).parent / f.name))

stamp = time.strftime("%Y%m%d-%H%M%S")
backup = E / (".soulos-backup-" + stamp)
new, changed, same, missing = [], [], [], []

for rel in targets:
    if rel in PROTECTED:
        continue
    src = G / "template" / rel
    if not src.exists():                       # the three interviews live at engine root
        src = G / rel
    if not src.exists():
        missing.append(rel)
        continue
    dst = E / rel
    content = fill(src.read_text(encoding="utf-8"))
    if not dst.exists():
        new.append(rel)
    elif dst.read_text(encoding="utf-8") == content:
        same.append(rel)
        continue
    else:
        changed.append(rel)
    if dry:
        continue
    if dst.exists():
        b = backup / rel
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dst, b)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(content, encoding="utf-8")
    if rel.endswith(".sh") or rel.endswith(".py"):
        os.chmod(dst, 0o755)

def show(label, items):
    if items:
        print("\n" + label + ":")
        for i in items:
            print("  " + i)

show("New", new)
show("Updated", changed)
show("Already current (%d)" % len(same), [] if len(same) > 8 else same)
show("Not in this engine build", missing)

print("\nUntouched, as always: SOUL.md, brand/brand.json, brand/logo/, your chapters,")
print("your figures, your article folders, the well, and scripts/repos.txt.")

if dry:
    print("\nDry run. Nothing was written.")
elif new or changed:
    print("\nBacked up what was replaced: " + os.path.relpath(backup, estate))
    print("Delete that folder once you are happy, then seal.")
else:
    print("\nAlready up to date.")
PYUP
