# Direct posting setup (no Zapier, no Metricool)

Posting now works like this:

1. A scheduled Claude run renders the Short, commits the video, and runs
   `poster/queue_post.py`, which adds a job file to `queue/<channel>/`.
2. That push starts the **Post Shorts** GitHub Action (`.github/workflows/post-shorts.yml`).
   It waits until the slot time and uploads the video with the official **YouTube Data API**
   and **Meta Graph API** (Facebook Reels + Instagram Reels).
3. Results (video ids, links or errors) are written to `queue/done/<channel>/<name>.json`.

The tokens live only in **GitHub repo secrets**. You do the one-time setup below; nothing else
is needed after that. Any platform whose secrets are missing is simply skipped, so you can set up
YouTube first and Facebook/Instagram later.

Secrets go here: GitHub → `careerwithcode-shorts` → **Settings → Secrets and variables →
Actions → New repository secret**.

---

## Part A — YouTube (do this once per channel)

Do it **signed in with the Gmail that owns the channel**:
CareerWithCode with its Gmail, CuriosityBox with `abhi7392067649@gmail.com`.
Each channel gets its own Google Cloud project, so each gets its own daily upload quota.

1. Open <https://console.cloud.google.com/> → project picker → **New project**
   (e.g. `careerwithcode-poster` / `curiositybox-poster`).
2. **APIs & Services → Library** → search **YouTube Data API v3** → **Enable**.
3. **Google Auth Platform** (OAuth consent screen) → **Get started**: app name, your email,
   audience **External**, finish.
4. **Audience** → click **Publish app** so the status is **In production**.
   ⚠️ If it stays in "Testing", the login expires every 7 days and posting silently stops.
   (You don't need Google verification for your own use; you'll just see an "unverified app"
   warning once when you sign in — click **Advanced → Go to … (unsafe)**.)
5. **Clients → Create client** → type **Desktop app** → create. Copy the **Client ID** and
   **Client secret**.
6. On your computer, in this repo folder, run:
   ```bash
   python3 poster/get_youtube_token.py "CLIENT_ID" "CLIENT_SECRET"
   ```
   A browser opens: sign in, pick the right channel, allow access. The script prints the
   channel name/id (check it is the right one) and a **refresh token**.
7. Add three GitHub secrets:

   | Channel        | Secrets |
   |----------------|---------|
   | CareerWithCode | `CWC_YT_CLIENT_ID`, `CWC_YT_CLIENT_SECRET`, `CWC_YT_REFRESH_TOKEN` |
   | CuriosityBox   | `CB_YT_CLIENT_ID`, `CB_YT_CLIENT_SECRET`, `CB_YT_REFRESH_TOKEN` |

8. **Apply for the YouTube API audit** (important): videos uploaded through the API by a new,
   unaudited project are **locked to private**. Fill in Google's
   *YouTube API Services – Audit and Quota Extension Form*
   (<https://support.google.com/youtube/contact/yt_api_form>) for each project. Say it's an
   internal tool that uploads your own channel's Shorts. Until it's approved, uploads land as
   private and you can make them public by hand in YouTube Studio; the job result shows
   `"privacy": "private"` with a warning.

Quota: each project gets 10,000 units/day and one upload costs about 1,600, so about 6 uploads
per channel per day.

---

## Part B — Facebook Page + Instagram (one Meta app covers both channels)

Requirements: you are an admin of each Facebook Page, and the CareerWithCode Instagram is a
**Professional (Business/Creator) account linked to its Facebook Page**.

1. Open <https://developers.facebook.com/apps> → **Create app** → pick the use cases for
   managing a Page and publishing Instagram content (type **Business** if asked). Leaving the app
   in Development mode is fine: you are its admin and you post only to your own Pages.
2. **App settings → Basic**: copy the **App ID** and **App secret**.
3. Open the **Graph API Explorer** (<https://developers.facebook.com/tools/explorer>), choose
   your app, **User token**, add these permissions, then **Generate Access Token** and allow
   your Pages/Instagram:
   `pages_show_list, pages_read_engagement, pages_manage_posts, business_management,
   instagram_basic, instagram_content_publish`
4. On your computer run:
   ```bash
   python3 poster/get_meta_token.py "APP_ID" "APP_SECRET" "TOKEN_FROM_EXPLORER"
   ```
   It lists each Page with its **page id**, **page token** (doesn't expire) and linked
   **Instagram id**.
5. Add GitHub secrets:

   | Channel        | Secrets |
   |----------------|---------|
   | CareerWithCode | `CWC_FB_PAGE_ID`, `CWC_FB_PAGE_TOKEN`, `CWC_IG_USER_ID` |
   | CuriosityBox   | `CB_FB_PAGE_TOKEN` (page id `1380858578445805` is already set in `poster/channels.json`) |

---

## Part C — Check it

GitHub → **Actions → Post Shorts → Run workflow**, tick **Only check which secrets are set** →
Run. The log shows `ready` or `missing …` for every channel/platform.

After the next scheduled Short, open `queue/done/<channel>/` to see the result with the
YouTube/Facebook/Instagram links.

## Changing things later

- Which platforms a channel posts to: `default_platforms` in `poster/channels.json`.
- Re-run a failed post: move its file from `queue/done/<channel>/` back to `queue/<channel>/`,
  set `"status": "pending"`, set `publish_at` to a time a few minutes ahead, commit and push.
  Platforms already marked `posted` in `results` are not posted again.
- A Graph API version error: set a newer version in the workflow env as `GRAPH_VERSION`
  (default `v24.0`).
