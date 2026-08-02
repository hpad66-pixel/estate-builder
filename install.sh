#!/usr/bin/env bash
# SoulOS one-line installer.
# Serve this file at https://owos.ai/install.sh
# Then anyone stamps their own estate with:
#
#     bash -c "$(curl -fsSL https://owos.ai/install.sh)"
#
# It fetches the Estate Builder engine and runs the stamp. No git knowledge needed.

set -euo pipefail

REPO="https://github.com/hpad66-pixel/estate-builder"
CACHE="${ESTATE_BUILDER_HOME:-$HOME/.estate-builder}"

say()  { printf '\n%s\n' "$*"; }
die()  { printf '\n%s\n' "$*" >&2; exit 1; }

say "SoulOS. Stamp your own estate."

# 1. Prerequisites. Both ship with most machines; if not, one line installs them.
command -v git >/dev/null 2>&1 || die "Git is needed. On a Mac run: xcode-select --install   Then run this again."
command -v python3 >/dev/null 2>&1 || die "Python 3 is needed. On a Mac run: brew install python   Then run this again."

# 2. Get the engine, or refresh it if you already have it.
if [ -d "$CACHE/.git" ]; then
  say "Refreshing the engine ..."
  git -C "$CACHE" pull --quiet --ff-only || say "Could not refresh. Using the copy you already have."
else
  say "Fetching the engine ..."
  git clone --quiet "$REPO" "$CACHE"
fi

STAMP="$CACHE/scripts/new_estate.sh"
[ -f "$STAMP" ] || die "The engine is missing its stamp script. Try again, or clone $REPO by hand."

# 3. Run the stamp. Reconnect the keyboard so the four questions work even when
#    this installer arrived through a pipe.
say "Four questions, then your estate."
if [ -e /dev/tty ]; then
  exec bash "$STAMP" </dev/tty
else
  exec bash "$STAMP"
fi
