#!/usr/bin/env python3
"""Queue a rendered Short for posting. Used by the scheduled runs (see RUNBOOK.md).

Writes queue/<channel>/<video name>.json, commits it and pushes to main. The push starts the
"Post Shorts" GitHub Action, which waits until --time and posts with the official APIs.

  python3 poster/queue_post.py --channel careerwithcode --video shorts/X.mp4 \
      --time "2026-10-19 16:00" --title "Why = NULL fails in SQL #shorts" \
      --caption "Caption line 1\n\n#shorts #coding" --tags sql,coding,shorts

--time is IST. --youtube-description defaults to --caption. --fb-caption replaces the caption
on Facebook/Instagram only (e.g. #reels instead of #shorts).
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
CHANNELS = json.load(open(os.path.join(ROOT, "poster", "channels.json")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True, choices=[c for c in CHANNELS if not c.startswith("_")])
    ap.add_argument("--video", required=True, help="path inside the repo, already committed")
    ap.add_argument("--time", required=True, help='IST, e.g. "2026-10-19 16:00"')
    ap.add_argument("--title", required=True)
    ap.add_argument("--caption", required=True)
    ap.add_argument("--youtube-description")
    ap.add_argument("--fb-caption")
    ap.add_argument("--tags", default="")
    ap.add_argument("--platforms", help="comma list; default from poster/channels.json")
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()

    cfg = CHANNELS[a.channel]
    video = os.path.relpath(os.path.abspath(a.video), ROOT)
    if not os.path.isfile(os.path.join(ROOT, video)):
        sys.exit(f"video not found: {video}")
    t = dt.datetime.fromisoformat(a.time.replace("T", " "))
    if t.tzinfo is None:
        t = t.replace(tzinfo=IST)
    now = dt.datetime.now(IST)
    if t < now:
        t = now + dt.timedelta(minutes=3)  # slot already passed: post right away
    caption = a.caption.replace("\\n", "\n")
    fb_caption = (a.fb_caption or caption).replace("\\n", "\n")
    job = {
        "channel": a.channel,
        "video": video,
        "publish_at": t.isoformat(timespec="seconds"),
        "platforms": a.platforms.split(",") if a.platforms else cfg["default_platforms"],
        "caption": fb_caption,
        "youtube": {
            "title": a.title[:100],
            "description": (a.youtube_description or caption).replace("\\n", "\n"),
            "tags": [x.strip() for x in a.tags.split(",") if x.strip()],
            "category_id": cfg.get("youtube_category_id", "27"),
            "default_language": cfg.get("default_language", "en"),
            "privacy": "public",
        },
        "status": "pending",
    }
    out_dir = os.path.join(ROOT, "queue", a.channel)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, os.path.splitext(os.path.basename(video))[0] + ".json")
    if os.path.exists(out) or os.path.exists(os.path.join(ROOT, "queue", "done", a.channel, os.path.basename(out))):
        sys.exit(f"already queued: {os.path.relpath(out, ROOT)} (never post the same video twice)")
    with open(out, "w") as f:
        json.dump(job, f, indent=2, ensure_ascii=False)
        f.write("\n")
    rel = os.path.relpath(out, ROOT)
    print(f"queued {rel} for {t:%Y-%m-%d %H:%M} IST -> {', '.join(job['platforms'])}")
    if a.no_push:
        return

    def git(*args):
        subprocess.run(["git", "-C", ROOT, *args], check=True)
    git("add", rel)
    git("-c", "user.name=Shorts Bot", "-c", "user.email=bot@careerwithcode.local",
        "commit", "-q", "-m", f"queue {a.channel}: {os.path.basename(video)}", "--", rel)
    git("pull", "-q", "--rebase", "origin", "main")
    git("push", "-q", "origin", "main")
    print("pushed; the 'Post Shorts' GitHub Action will post it at the scheduled time")


if __name__ == "__main__":
    main()
