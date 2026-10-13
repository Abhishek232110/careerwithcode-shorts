#!/usr/bin/env bash
# Commit a rendered CuriosityBox Short to curiositybox/shorts/ on main and print its public URL.
# Kept separate from the CareerWithCode videos in the repo's top-level shorts/ folder.
# Usage: curiositybox/publish.sh curiositybox/shorts/2026-10-13_1700_whatif-chand-gayab.mp4
set -euo pipefail
ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
cd "$ROOT"
FILE="$1"; NAME="$(basename "$FILE")"
DEST="curiositybox/shorts/$NAME"
mkdir -p curiositybox/shorts
[ "$(realpath "$FILE")" = "$(realpath -m "$DEST")" ] || cp "$FILE" "$DEST"
OWNER_REPO="$(git remote get-url origin | sed -E 's#.*github.com[/:]##; s#\.git$##')"
git add "$DEST"
git -c user.name="CuriosityBox Bot" -c user.email="bot@curiositybox.local" \
    commit -q -m "curiositybox video: $NAME" -- "$DEST"
git pull -q --rebase origin main
git push -q origin main
URL="https://raw.githubusercontent.com/${OWNER_REPO}/main/${DEST}"
for i in $(seq 1 20); do
  code="$(curl -s -o /dev/null -w '%{http_code}' -L "$URL" || true)"
  [ "$code" = "200" ] && break
  sleep 3
done
echo "$URL"
