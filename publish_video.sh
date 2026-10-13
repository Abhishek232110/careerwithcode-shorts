#!/usr/bin/env bash
# Commit a rendered Short to the repo (main branch, shorts/ folder) and print
# its public URL. Every video is kept permanently in the repo.
# Usage: ./publish_video.sh shorts/2026-10-13_0800_go-p01.mp4
set -euo pipefail
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
FILE="$1"; NAME="$(basename "$FILE")"
mkdir -p shorts
[ "$FILE" = "shorts/$NAME" ] || cp "$FILE" "shorts/$NAME"
OWNER_REPO="$(git remote get-url origin | sed -E 's#.*github.com[/:]##; s#\.git$##')"
git add "shorts/$NAME"
git -c user.name="CareerWithCode Bot" -c user.email="bot@careerwithcode.local" \
    commit -q -m "video: $NAME" -- "shorts/$NAME"
git pull -q --rebase origin main
git push -q origin main
URL="https://raw.githubusercontent.com/${OWNER_REPO}/main/shorts/${NAME}"
for i in $(seq 1 20); do
  code="$(curl -s -o /dev/null -w '%{http_code}' -L "$URL" || true)"
  [ "$code" = "200" ] && break
  sleep 3
done
echo "$URL"
