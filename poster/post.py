#!/usr/bin/env python3
"""Post queued Shorts straight to YouTube, Facebook and Instagram with their official APIs.

No Zapier, no Metricool: this runs inside GitHub Actions (.github/workflows/post-shorts.yml)
using tokens stored as GitHub repo secrets (see poster/SETUP.md).

A scheduled Claude run renders a Short, commits the video, and drops a job file in
queue/<channel>/<name>.json. This script picks up pending jobs, waits until each job's
publish_at time, uploads the video to every platform in the job, writes the results into the
job file and moves it to queue/done/<channel>/.

Usage:
  python3 poster/post.py                 # process the queue
  python3 poster/post.py --dry-run       # show what would happen, call no APIs
  python3 poster/post.py --check         # check which secrets are configured per channel
"""
import argparse
import datetime as dt
import glob
import json
import os
import shutil
import subprocess
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "queue")
DONE = os.path.join(QUEUE, "done")
CHANNELS = json.load(open(os.path.join(ROOT, "poster", "channels.json")))
GRAPH_VERSION = os.environ.get("GRAPH_VERSION", "v24.0")
GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
TIMEOUT = 300


class NotConfigured(Exception):
    pass


def now():
    return dt.datetime.now(dt.timezone.utc)


def log(msg):
    print(f"[{now().astimezone(IST):%H:%M:%S} IST] {msg}", flush=True)


def secret(prefix, name, required=True):
    val = os.environ.get(f"{prefix}_{name}", "").strip()
    if required and not val:
        raise NotConfigured(f"secret {prefix}_{name} is not set")
    return val


def check_response(r, what):
    if r.status_code >= 400:
        raise RuntimeError(f"{what} failed: HTTP {r.status_code}: {r.text[:500]}")
    return r


# ---------------------------------------------------------------- YouTube
def youtube_access_token(prefix):
    cid = secret(prefix, "YT_CLIENT_ID")
    csec = secret(prefix, "YT_CLIENT_SECRET")
    rtok = secret(prefix, "YT_REFRESH_TOKEN")
    r = requests.post("https://oauth2.googleapis.com/token", timeout=60, data={
        "client_id": cid, "client_secret": csec,
        "refresh_token": rtok, "grant_type": "refresh_token"})
    check_response(r, "YouTube token refresh")
    return r.json()["access_token"]


def post_youtube(job, cfg, video_path):
    prefix = cfg["secret_prefix"]
    token = youtube_access_token(prefix)
    yt = job.get("youtube", {})
    title = yt.get("title") or job.get("title", "")
    if not title:
        raise RuntimeError("job has no youtube.title")
    lang = yt.get("default_language", cfg.get("default_language", "en"))
    body = {
        "snippet": {
            "title": title[:100],
            "description": yt.get("description", job.get("caption", ""))[:5000],
            "tags": yt.get("tags", []),
            "categoryId": str(yt.get("category_id", cfg.get("youtube_category_id", "27"))),
            "defaultLanguage": lang,
            "defaultAudioLanguage": lang,
        },
        "status": {
            "privacyStatus": yt.get("privacy", "public"),
            "selfDeclaredMadeForKids": False,
            "embeddable": True,
        },
    }
    if "contains_synthetic_media" in yt:
        body["status"]["containsSyntheticMedia"] = bool(yt["contains_synthetic_media"])
    size = os.path.getsize(video_path)
    notify = "true" if yt.get("notify_subscribers", True) else "false"
    r = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos"
        f"?uploadType=resumable&part=snippet,status&notifySubscribers={notify}",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Type": "video/mp4",
                 "X-Upload-Content-Length": str(size)},
        data=json.dumps(body), timeout=60)
    check_response(r, "YouTube upload start")
    upload_url = r.headers["Location"]
    with open(video_path, "rb") as f:
        r = requests.put(upload_url, data=f, timeout=TIMEOUT,
                         headers={"Authorization": f"Bearer {token}",
                                  "Content-Type": "video/mp4",
                                  "Content-Length": str(size)})
    check_response(r, "YouTube upload")
    v = r.json()
    channel = v.get("snippet", {}).get("channelId")
    expected = cfg.get("youtube_channel_id")
    result = {"status": "posted", "id": v["id"],
              "url": f"https://youtube.com/shorts/{v['id']}",
              "privacy": v.get("status", {}).get("privacyStatus"),
              "channel_id": channel}
    if expected and channel and channel != expected:
        result["warning"] = (f"uploaded to channel {channel}, expected {expected}: "
                             "the YouTube token belongs to the wrong channel")
    if result["privacy"] != body["status"]["privacyStatus"]:
        result["warning"] = (f"YouTube set privacy to '{result['privacy']}'. New, unaudited "
                             "Google Cloud projects are locked to private until the YouTube "
                             "API audit is approved (see poster/SETUP.md).")
    return result


# ---------------------------------------------------------------- Facebook (Reels)
def post_facebook(job, cfg, video_path):
    prefix = cfg["secret_prefix"]
    page_id = os.environ.get(f"{prefix}_FB_PAGE_ID", "").strip() or cfg.get("facebook_page_id")
    if not page_id:
        raise NotConfigured(f"secret {prefix}_FB_PAGE_ID is not set")
    token = secret(prefix, "FB_PAGE_TOKEN")
    r = requests.post(f"{GRAPH}/{page_id}/video_reels", timeout=60,
                      data={"upload_phase": "start", "access_token": token})
    check_response(r, "Facebook reel start")
    video_id = r.json()["video_id"]
    size = os.path.getsize(video_path)
    with open(video_path, "rb") as f:
        r = requests.post(f"https://rupload.facebook.com/video-upload/{GRAPH_VERSION}/{video_id}",
                          data=f, timeout=TIMEOUT,
                          headers={"Authorization": f"OAuth {token}",
                                   "offset": "0", "file_size": str(size)})
    check_response(r, "Facebook reel upload")
    fb = job.get("facebook", {})
    desc = fb.get("description") or job.get("caption", "")
    data = {"upload_phase": "finish", "video_id": video_id, "video_state": "PUBLISHED",
            "description": desc, "access_token": token}
    if fb.get("title"):
        data["title"] = fb["title"]
    r = requests.post(f"{GRAPH}/{page_id}/video_reels", timeout=60, data=data)
    check_response(r, "Facebook reel publish")
    return {"status": "posted", "id": video_id,
            "url": f"https://www.facebook.com/reel/{video_id}"}


# ---------------------------------------------------------------- Instagram (Reels)
def post_instagram(job, cfg, video_path):
    prefix = cfg["secret_prefix"]
    ig_user = secret(prefix, "IG_USER_ID")
    token = os.environ.get(f"{prefix}_IG_TOKEN", "").strip() or secret(prefix, "FB_PAGE_TOKEN")
    ig = job.get("instagram", {})
    caption = ig.get("caption") or job.get("caption", "")
    r = requests.post(f"{GRAPH}/{ig_user}/media", timeout=60, data={
        "media_type": "REELS", "upload_type": "resumable", "caption": caption,
        "share_to_feed": "true", "access_token": token})
    check_response(r, "Instagram container")
    container = r.json()["id"]
    size = os.path.getsize(video_path)
    with open(video_path, "rb") as f:
        r = requests.post(f"https://rupload.facebook.com/ig-api-upload/{GRAPH_VERSION}/{container}",
                          data=f, timeout=TIMEOUT,
                          headers={"Authorization": f"OAuth {token}",
                                   "offset": "0", "file_size": str(size)})
    check_response(r, "Instagram upload")
    for _ in range(60):  # wait up to ~5 min for Instagram to process the video
        r = requests.get(f"{GRAPH}/{container}", timeout=60,
                         params={"fields": "status_code,status", "access_token": token})
        check_response(r, "Instagram status")
        st = r.json().get("status_code")
        if st == "FINISHED":
            break
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram processing {st}: {r.json().get('status')}")
        time.sleep(5)
    else:
        raise RuntimeError("Instagram processing timed out")
    r = requests.post(f"{GRAPH}/{ig_user}/media_publish", timeout=60,
                      data={"creation_id": container, "access_token": token})
    check_response(r, "Instagram publish")
    media_id = r.json()["id"]
    link = None
    try:
        link = requests.get(f"{GRAPH}/{media_id}", timeout=60, params={
            "fields": "permalink", "access_token": token}).json().get("permalink")
    except Exception:
        pass
    return {"status": "posted", "id": media_id, "url": link}


POSTERS = {"youtube": post_youtube, "facebook": post_facebook, "instagram": post_instagram}


# ---------------------------------------------------------------- queue handling
def git_persist(paths, message):
    """Commit and push job results right away so a crash never causes a double post."""
    if os.environ.get("PERSIST_GIT") != "1":
        return
    def run(*a):
        return subprocess.run(["git", "-C", ROOT, *a], capture_output=True, text=True)
    run("add", "-A", "--", *paths)
    if run("diff", "--cached", "--quiet").returncode == 0:
        return
    run("-c", "user.name=Shorts Poster", "-c", "user.email=poster@careerwithcode.local",
        "commit", "-q", "-m", message)
    for _ in range(5):
        run("pull", "-q", "--rebase", "origin", "main")
        if run("push", "-q", "origin", "HEAD:main").returncode == 0:
            return
        time.sleep(5)
    log("WARNING: could not push job results")


def parse_time(s):
    t = dt.datetime.fromisoformat(s)
    if t.tzinfo is None:
        t = t.replace(tzinfo=IST)
    return t


def save(path, job):
    with open(path, "w") as f:
        json.dump(job, f, indent=2, ensure_ascii=False)
        f.write("\n")


def finish(path, job, channel):
    dest_dir = os.path.join(DONE, channel)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(path))
    save(path, job)
    shutil.move(path, dest)
    rel_src = os.path.relpath(path, ROOT)
    rel_dst = os.path.relpath(dest, ROOT)
    git_persist([rel_src, rel_dst], f"poster: {channel} {os.path.basename(path)} -> {job['status']}")


def process(path, args):
    job = json.load(open(path))
    channel = job.get("channel") or os.path.basename(os.path.dirname(path))
    if channel not in CHANNELS:
        log(f"{path}: unknown channel '{channel}', skipping")
        return
    cfg = CHANNELS[channel]
    name = os.path.relpath(path, ROOT)
    if job.get("status", "pending") != "pending":
        return
    publish_at = parse_time(job["publish_at"])
    wait = (publish_at - now()).total_seconds()
    if wait > args.max_wait_min * 60:
        log(f"{name}: publish_at {publish_at.astimezone(IST):%Y-%m-%d %H:%M} IST is later, leaving it")
        return
    if -wait > args.max_late_hours * 3600:
        job["status"] = "expired"
        job["note"] = f"not posted: more than {args.max_late_hours} h past publish_at"
        log(f"{name}: expired")
        if not args.dry_run:
            finish(path, job, channel)
        return
    video = os.path.join(ROOT, job["video"])
    if not os.path.isfile(video):
        job["status"] = "failed"
        job["note"] = f"video file not found: {job['video']}"
        log(f"{name}: {job['note']}")
        if not args.dry_run:
            finish(path, job, channel)
        return
    platforms = job.get("platforms") or cfg["default_platforms"]
    if args.dry_run:
        log(f"{name}: would post {job['video']} to {platforms} at "
            f"{publish_at.astimezone(IST):%H:%M} IST (in {max(0, wait)/60:.0f} min)")
        return
    if wait > 0:
        log(f"{name}: waiting {wait/60:.1f} min until {publish_at.astimezone(IST):%H:%M} IST")
        time.sleep(wait)
    results = job.setdefault("results", {})
    for p in platforms:
        if results.get(p, {}).get("status") == "posted":
            continue  # never post the same video twice
        if p not in POSTERS:
            results[p] = {"status": "failed", "error": f"unknown platform {p}"}
            continue
        for attempt in (1, 2):
            try:
                log(f"{name}: posting to {p} (attempt {attempt})")
                results[p] = POSTERS[p](job, cfg, video)
                results[p]["at"] = now().astimezone(IST).isoformat(timespec="seconds")
                log(f"{name}: {p} -> {results[p]}")
                break
            except NotConfigured as e:
                results[p] = {"status": "skipped", "error": str(e)}
                log(f"{name}: {p} skipped: {e}")
                break
            except Exception as e:
                results[p] = {"status": "failed", "error": str(e)[:800]}
                log(f"{name}: {p} error: {e}")
                if attempt == 1:
                    time.sleep(20)
        save(path, job)
        git_persist([os.path.relpath(path, ROOT)], f"poster: {channel} {p} result")
    states = {r.get("status") for r in results.values()} - {"skipped"}
    job["status"] = ("skipped" if not states else
                     "posted" if states == {"posted"} else
                     "partial" if "posted" in states else "failed")
    finish(path, job, channel)


NEED = {"youtube": ["YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"],
        "facebook": ["FB_PAGE_TOKEN"],
        "instagram": ["IG_USER_ID", "FB_PAGE_TOKEN"]}


def readiness():
    """{channel: {platform: True/False}} based on which secrets are present."""
    out = {}
    for name, cfg in CHANNELS.items():
        if name.startswith("_"):
            continue
        p = cfg["secret_prefix"]
        out[name] = {}
        for plat in cfg["default_platforms"]:
            need = list(NEED[plat])
            if plat == "facebook" and not cfg.get("facebook_page_id"):
                need.append("FB_PAGE_ID")
            out[name][plat] = all(os.environ.get(f"{p}_{s}") for s in need)
    return out


def write_status():
    """Write poster/status.json so scheduled runs know which platforms post directly."""
    path = os.path.join(ROOT, "poster", "status.json")
    data = {"_note": "Written by the Post Shorts GitHub Action. true = posts directly via "
                     "official API; false = token not added yet (runs use the fallback).",
            "ready": readiness()}
    old = None
    if os.path.exists(path):
        try:
            old = json.load(open(path)).get("ready")
        except Exception:
            pass
    if old == data["ready"]:
        return
    data["updated"] = now().astimezone(IST).isoformat(timespec="seconds")
    save(path, data)
    git_persist(["poster/status.json"], "poster: update platform readiness")
    log(f"status.json updated: {data['ready']}")


def check():
    ok = True
    for name, cfg in CHANNELS.items():
        if name.startswith("_"):
            continue
        p = cfg["secret_prefix"]
        print(f"{name}:")
        need = {"youtube": ["YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"],
                "facebook": ["FB_PAGE_TOKEN"] + ([] if cfg.get("facebook_page_id") else ["FB_PAGE_ID"]),
                "instagram": ["IG_USER_ID", "FB_PAGE_TOKEN"]}
        for plat in cfg["default_platforms"]:
            missing = [f"{p}_{s}" for s in need[plat] if not os.environ.get(f"{p}_{s}")]
            print(f"  {plat:9s} {'ready' if not missing else 'missing ' + ', '.join(missing)}")
            ok = ok and not missing
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--max-wait-min", type=float, default=45,
                    help="wait for jobs due within this many minutes")
    ap.add_argument("--max-late-hours", type=float, default=6,
                    help="jobs later than this are marked expired instead of posted")
    args = ap.parse_args()
    if args.check:
        check()
        return
    if not args.dry_run:
        write_status()
    jobs = [p for p in glob.glob(os.path.join(QUEUE, "*", "*.json"))
            if not p.startswith(DONE + os.sep)]
    jobs.sort(key=lambda p: json.load(open(p)).get("publish_at", ""))
    if not jobs:
        log("queue is empty")
    for p in jobs:
        try:
            process(p, args)
        except Exception as e:
            log(f"{p}: unexpected error: {e}")


if __name__ == "__main__":
    sys.exit(main())
