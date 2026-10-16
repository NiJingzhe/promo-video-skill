#!/usr/bin/env bash
# Create a Remotion project from the skill's template.
#   new_project.sh <dir> [--link-modules <existing project's node_modules>]
set -euo pipefail
dir="${1:?usage: new_project.sh <dir> [--link-modules <path>]}"; shift || true
here="$(cd "$(dirname "$0")/.." && pwd)"
[ -e "$dir" ] && { echo "$dir exists"; exit 1; }
mkdir -p "$dir" && cp -R "$here/template/." "$dir/"
cd "$dir"
if [ "${1:-}" = "--link-modules" ]; then ln -s "$(cd "$(dirname "$2")" && pwd)/$(basename "$2")" node_modules
else npm install --no-audit --no-fund; fi
# WebGL needs the playwright headless shell (see remotion.config.ts)
ls ~/Library/Caches/ms-playwright 2>/dev/null | grep -q headless_shell || npx --yes playwright-core install chromium-headless-shell
echo "ready: $dir   (npm run studio | npm run still | npm run render)"
