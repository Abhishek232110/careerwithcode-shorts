#!/usr/bin/env bash
# Upload a rendered Short to the `media` branch and print its public URL.
# The media branch is rebuilt each time and keeps only the last 3 days of
# videos, so the repo never grows large (videos are already on YouTube/IG/FB).
# Usage: ./publish_video.sh shorts/2026-10-13_0800_go-p01.mp4
set -euo pipefail
VIDEO="$(realpath "$1")"; NAME="$(basename "$VIDEO")"
REPO="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
REMOTE="$(git -C "$REPO" remote get-url origin)"
OWNER_REPO="$(echo "$REMOTE" | sed -E 's#.*github.com[/:]##; s#\.git$##')"
CUTOFF="$(date -u -d '3 days ago' +%Y-%m-%d)"

W="$(mktemp -d)"; cd "$W"
git init -q; git remote add origin "$REMOTE"
if git fetch -q --depth 1 origin media 2>/dev/null; then
  git checkout -q FETCH_HEAD -- . 2>/dev/null || true
fi
git checkout -q --orphan media
mkdir -p v
for f in v/*.mp4; do
  [ -e "$f" ] || continue
  d="$(basename "$f" | cut -c1-10)"
  [[ "$d" < "$CUTOFF" ]] && rm -f "$f"
done
cp "$VIDEO" "v/$NAME"
git add -A
git -c user.name="CareerWithCode Bot" -c user.email="bot@careerwithcode.local" commit -q -m "media: $NAME"
git push -q -f origin media
URL="https://raw.githubusercontent.com/${OWNER_REPO}/media/v/${NAME}"
# wait until the file is publicly downloadable
for i in $(seq 1 20); do
  code="$(curl -s -o /dev/null -w '%{http_code}' -L "$URL" || true)"
  [ "$code" = "200" ] && break
  sleep 3
done
echo "$URL"
