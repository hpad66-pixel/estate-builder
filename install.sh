#!/usr/bin/env bash
# SoulOS authenticated installer and owner-controlled updater.
#
# Install:
#   SOULOS_KEY=... bash -c "$(curl -fsSL https://owos.ai/install.sh)"
# Guided install:
#   SOULOS_KEY=... bash -c "$(curl -fsSL https://owos.ai/install.sh)" -- install --config "$HOME/Downloads/soulos-onboarding.json"
# Check:
#   bash -c "$(curl -fsSL https://owos.ai/install.sh)" -- check --estate "$HOME/dev/your-soul"
# Update:
#   SOULOS_KEY=... bash -c "$(curl -fsSL https://owos.ai/install.sh)" -- update --estate "$HOME/dev/your-soul"

set -euo pipefail

ENGINE_URL="${SOULOS_ENGINE_URL:-https://owos.ai/soulos/engine}"
META_URL="${SOULOS_META_URL:-https://owos.ai/soulos/version}"
CACHE="${SOULOS_HOME:-$HOME/.soulos-engine}"
KEY="${SOULOS_KEY:-}"
MODE="install"
ESTATE=""
CONFIG=""

say() { printf '\n%s\n' "$*"; }
die() { printf '\n%s\n' "$*" >&2; exit 1; }

case "${1:-}" in
  install|update|check) MODE="$1"; shift ;;
esac
while [ $# -gt 0 ]; do
  case "$1" in
    --estate) [ $# -ge 2 ] || die "--estate needs a folder."; ESTATE="$2"; shift 2 ;;
    --config) [ $# -ge 2 ] || die "--config needs a guided setup file."; CONFIG="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,11p' "$0" 2>/dev/null || true
      exit 0
      ;;
    *) die "Unknown option: $1" ;;
  esac
done

say "SoulOS"
command -v curl >/dev/null 2>&1 || die "curl is needed. It ships with macOS and most Linux."
command -v python3 >/dev/null 2>&1 || die "Python 3 is needed. On a Mac run: brew install python"
if [ "$MODE" != "check" ]; then
  command -v tar >/dev/null 2>&1 || die "tar is needed."
  command -v git >/dev/null 2>&1 || die "Git is needed. On a Mac run: xcode-select --install"
fi

META_FILE="$(mktemp)"
trap 'rm -f "$META_FILE" "${TARBALL:-}"' EXIT
curl -fsSL "$META_URL" -o "$META_FILE" || die "Could not check the current SoulOS release."
META_VALUES="$(python3 - "$META_FILE" <<'PYMETA'
import json, pathlib, re, sys
data = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
version = str(data.get("version", "")).strip()
checksum = str(data.get("sha256", "")).strip().lower()
if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
    raise SystemExit("The release has no valid version.")
if checksum and not re.fullmatch(r"[0-9a-f]{64}", checksum):
    raise SystemExit("The release checksum is invalid.")
print(version)
print(checksum)
PYMETA
)"
LATEST="$(printf '%s\n' "$META_VALUES" | sed -n '1p')"
EXPECTED_SHA="$(printf '%s\n' "$META_VALUES" | sed -n '2p')"

if [ "$MODE" = "check" ]; then
  [ -n "$ESTATE" ] || { [ -f "$PWD/.soulos-estate" ] && ESTATE="$PWD"; }
  [ -n "$ESTATE" ] && [ -f "$ESTATE/.soulos-estate" ] || die "Choose your estate with --estate, or run this inside it."
  CURRENT="$(sed -n 's/^engine[[:space:]]\+//p' "$ESTATE/.soulos-estate" | tail -n 1)"
  [ -n "$CURRENT" ] || CURRENT="unknown"
  say "Installed: $CURRENT"
  say "Available: $LATEST"
  if [ "$CURRENT" = "$LATEST" ]; then
    say "Your estate is current."
  else
    say "An update is available. Nothing changed. Return to SoulOS Studio or run the update command when you are ready."
  fi
  exit 0
fi

if [ -z "$KEY" ] && [ -e /dev/tty ]; then
  printf '\nPaste your SoulOS access key: '
  read -r KEY </dev/tty
fi
[ -n "$KEY" ] || die "No access key. Open SoulOS Studio in your OWOS account to get your private command."

say "Checking access and fetching SoulOS $LATEST ..."
TARBALL="$(mktemp)"
CODE="$(curl -sSL -o "$TARBALL" -w '%{http_code}' "$ENGINE_URL?key=$KEY&purpose=$MODE" || echo 000)"
[ "$CODE" = "200" ] || die "The engine could not be delivered (status $CODE). Open SoulOS Studio to check access."

if [ -n "$EXPECTED_SHA" ]; then
  if command -v shasum >/dev/null 2>&1; then
    ACTUAL_SHA="$(shasum -a 256 "$TARBALL" | awk '{print $1}')"
  elif command -v sha256sum >/dev/null 2>&1; then
    ACTUAL_SHA="$(sha256sum "$TARBALL" | awk '{print $1}')"
  else
    die "A SHA-256 checksum tool is required to verify this update."
  fi
  [ "$ACTUAL_SHA" = "$EXPECTED_SHA" ] || die "The downloaded engine did not match its signed release record. Nothing was installed."
fi

NEW_CACHE="$(mktemp -d)"
tar -xzf "$TARBALL" -C "$NEW_CACHE" --strip-components=1 2>/dev/null || die "The engine archive could not be opened."
[ -f "$NEW_CACHE/VERSION" ] || die "The engine archive has no version record."
[ "$(tr -d '[:space:]' < "$NEW_CACHE/VERSION")" = "$LATEST" ] || die "The engine archive version does not match the release record."
[ -f "$NEW_CACHE/scripts/new_estate.sh" ] || die "The engine archive is incomplete."

if [ -d "$CACHE" ]; then
  PREVIOUS="$CACHE.previous-$(date +%Y%m%d-%H%M%S)"
  mv "$CACHE" "$PREVIOUS"
fi
mkdir -p "$(dirname "$CACHE")"
mv "$NEW_CACHE" "$CACHE"

if [ "$MODE" = "update" ]; then
  [ -n "$ESTATE" ] || { [ -f "$PWD/.soulos-estate" ] && ESTATE="$PWD"; }
  [ -n "$ESTATE" ] && [ -f "$ESTATE/.soulos-estate" ] || die "Choose your estate with --estate, or run the update inside it."
  say "Reviewing the update before anything changes ..."
  bash "$ESTATE/scripts/update_estate.sh" --from "$CACHE" --check
  printf '\nApply this update now? [y/N] '
  if [ -e /dev/tty ]; then read -r ANSWER </dev/tty; else ANSWER="n"; fi
  case "$ANSWER" in
    y|Y|yes|YES) bash "$ESTATE/scripts/update_estate.sh" --from "$CACHE" ;;
    *) say "Stopped after the review. Your estate was not changed." ;;
  esac
  exit 0
fi

STAMP="$CACHE/scripts/new_estate.sh"
say "Your engine is verified. Now we will create your estate."
if [ -n "$CONFIG" ]; then
  [ -f "$CONFIG" ] || die "Guided setup file not found: $CONFIG"
  exec bash "$STAMP" --config "$CONFIG"
elif [ -e /dev/tty ]; then
  exec bash "$STAMP" </dev/tty
else
  exec bash "$STAMP"
fi
