#!/usr/bin/env bash
# End-to-end safety test for guided setup, SOUL import, and updates.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEST_ROOT"' EXIT
export HOME="$TEST_ROOT/home"
mkdir -p "$HOME/Downloads"

cat > "$HOME/Downloads/soulos-onboarding.json" <<'JSON'
{
  "author": "Test Owner",
  "slug": "test-owner-soul",
  "book": "The Test Book",
  "githubUsername": "",
  "onboardingMode": "import",
  "soulMarkdown": "# SOUL.md\n\nThis is the owner's exact voice law.\n"
}
JSON

bash "$ROOT/scripts/new_estate.sh" --config "$HOME/Downloads/soulos-onboarding.json"
ESTATE="$HOME/dev/test-owner-soul"
grep -Fq "This is the owner's exact voice law." "$ESTATE/SOUL.md"
grep -Fq "onboarding import" "$ESTATE/.soulos-estate"
grep -Fq "engine $(tr -d '[:space:]' < "$ROOT/VERSION")" "$ESTATE/.soulos-estate"

printf '\nOwner addition.\n' >> "$ESTATE/SOUL.md"
printf '\nLocally changed engine-owned file.\n' >> "$ESTATE/CONTENT-MAP.md"
git -C "$ESTATE" add SOUL.md CONTENT-MAP.md
git -C "$ESTATE" commit -q -m "test local changes"

bash "$ESTATE/scripts/update_estate.sh" --from "$ROOT" --check
bash "$ESTATE/scripts/update_estate.sh" --from "$ROOT"
grep -Fq "Owner addition." "$ESTATE/SOUL.md"
if grep -Fq "Locally changed engine-owned file." "$ESTATE/CONTENT-MAP.md"; then
  echo "Engine-owned file was not refreshed." >&2
  exit 1
fi
find "$ESTATE" -maxdepth 1 -type d -name '.soulos-backup-*' | grep -q .
python3 "$ESTATE/scripts/qc_check.py"

printf '\nSoulOS engine test passed.\n'
