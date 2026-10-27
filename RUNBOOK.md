# CareerWithCode Shorts — run instructions

Each scheduled run makes ONE Short of **20–30 seconds** for ONE slot and posts it publicly to YouTube (Short) and
Facebook (Reel) through **Zapier only** (step 6). Metricool is no longer used. Instagram is
skipped because Zapier can't post to it.

| Slot (IST) | `SLOT` value   | Content |
|-----------|----------------|---------|
| 08:00     | `go`           | Go series, next part from `curriculum.json` |
| 11:00     | `educational`  | Helpful coding tip / concept, new topic |
| 14:00     | `educational`  | Helpful coding tip / concept, new topic |
| 17:00     | `learn`        | How to learn programming (roadmaps, study tips) |
| 20:00     | `python`       | Python series, next part from `curriculum.json` |

## Tone — every Short must feel different

Each slot has its own voice. Hook, takeaway, CTA and caption must all match it.

| Slot  | Tone | Feel |
|-------|------|------|
| 08:00 Go series | **Friendly teacher** | Clear, encouraging, "let's learn this together". CTA teases the next part. |
| 11:00 educational | **Practical quick win** | Energetic and useful: "Save this", a trick you can use today. |
| 14:00 educational | **Myth-buster / surprising** | "You've been doing this wrong", "Most devs don't know this". |
| 17:00 learn | **Motivating mentor** | Inspiring, growth-focused, speaks to beginners chasing a dev career. |
| 20:00 Python series | **Playful & relatable** | Light humour, relatable dev moments, still teaches the topic properly. |

**Rotate the hook format** so the same slot never uses the same format twice in a row
(check that slot's last entry in `tracker.log`, field `hook_format`):
`question` ("Do you know why…?"), `bold-claim`, `common-mistake`, `quiz`
("What does this print?" — show the answer in `output`), `myth-vs-fact`, `comparison`
(X vs Y), `mini-story` ("I spent 2 hours on this bug…"), `challenge` ("Try this today").

**Style:** all on-screen text (hook, labels, takeaway, button) uses the handwritten
Kalam font from `fonts/` automatically; code stays monospace. Write every hook, takeaway
and caption the way a real person talks: casual, warm, first person ("I", "you"),
short sentences, no robotic or corporate phrasing.

Also vary the CTA and caption wording (never copy the previous post's text), and end the
caption with an engaging question or "comment X" prompt to grow reach.

## Steps

1. **Get the repo.** `git clone https://github.com/Abhishek232110/careerwithcode-shorts`
   (if the session has no access, attach it first with the add_repo tool, push access).
   Work inside the clone.

2. **Pick the topic.** Read `tracker.json` and `curriculum.json`.
   - `go` / `python`: topic = `curriculum[SLOT][next_part - 1]`. If the list has run out,
     write the next sensible topic for that series yourself and append it to the list.
   - `educational` / `learn`: choose a topic NOT already in `tracker[SLOT].posted`
     (use the `*_ideas` lists for inspiration; vary languages and formats; never repeat).

3. **Write the spec** to `specs/<YYYY-MM-DD>_<HHMM>_<slot>-<slug>.json` (IST date/time):
   ```json
   {
     "series_label": "Go Series · Part 7",          // series slots only; omit otherwise
     "hook": "Go has no while loop. Here's why",       // ≤ 8 words, curiosity-driven
     "language": "Go",                                // badge: Python, Go, JavaScript, SQL, Git, Roadmap…
     "before": ["..."],                               // optional "old/wrong way", ≤ 4 lines
     "code": ["..."],                                 // main code, ≤ 6 lines, ≤ 34 chars per line
     "output": "i = 3",                               // optional, short
     "takeaway": "One line, ≤ 12 words.",
     "cta": "Follow for Part 8 tomorrow",              // series: "Follow for Part N+1 tomorrow"
     "duration": 25,                                  // REQUIRED: 20-30 seconds, more text = longer
     "before_title": "...", "code_title": "..."       // optional panel titles
   }
   ```
   - The code MUST be correct. For Python, run it with `python3` and copy the real output.
   - `learn` slot: put a short roadmap/steps in `code` (e.g. `"Week 1: syntax + loops"`),
     set `language` to `"Roadmap"` and `code_title` to something like `"30-day plan"`;
     leave out `before`/`output` if they don't fit.
   - Educational slot: a gotcha, trick, or "X explained" with a tiny code example.

4. **Render:** `python3 make_short.py specs/<name>.json shorts/<name>.mp4`
   Check it is 20–30 s and 1080x1920 (`ffprobe`). Extract one frame 1 s before the end and look at it
   with Read: text must not overlap or run off the screen. If it does, shorten the
   text and re-render.

5. **Upload:** `./publish_video.sh shorts/<name>.mp4` → commits the video to `shorts/`
   on main (every video is kept in the repo permanently) and prints its public URL.

6. **Post through Zapier only.** Never use Metricool, `poster/route.py` or `poster/queue_post.py`.
   Load the Zapier tools with ToolSearch (`select:mcp__Zapier__list_zapier_connections,mcp__Zapier__inspect_zapier_actions,mcp__Zapier__execute_zapier_write_action,mcp__Zapier__execute_zapier_read_action`).
   Targets — use exactly these, never any other channel or page:
   - YouTube channel **CareerWithCode**, id `UCZ6m5Lh_vmFjOLL_RAHNTxw`
   - Facebook page **CareerWithCode**, page id `926523670552408`
   Never post to the CuriosityBox channel `UCtJ6818H8WuXS071samDcPA` or page `1380858578445805`.

   **Check the connections first.** YouTube connection `0262b3cb-1516-8a90-ab80-2759bc7523b1` is
   CareerWithCode; confirm with youtube_make_api_get_request (`url: https://www.googleapis.com/youtube/v3/channels`, `querystring: {"part": "snippet", "mine": "true"}`, `fail_on_errors: false`) that it returns
   `UCZ6m5Lh_vmFjOLL_RAHNTxw` and pass it as `connection_id`. Facebook uses connection
   `0255d81b-a11a-8f8c-9c7a-002223e547ee`. YouTube rejects descriptions containing `<` or `>`. For Facebook, check that page
   `926523670552408` is in the `page` dropdown of `facebook_pages_create_page_video`. If a
   CareerWithCode account isn't connected, don't post to it: keep the video and record
   "not posted: not connected in Zapier" for that platform.

   Runs start ~15 min early. Wait (sleep) until the slot time before posting, because Zapier
   publishes immediately. If the slot time has already passed, post right away.

   a. **YouTube:** `execute_zapier_write_action` with `selected_api: "YouTubeV4CLIAPI"`,
      `action: "upload_video"`, `tool_name: "youtube_upload_video"`, the CareerWithCode
      `connection_id`, params: `title` (<= 90 chars, ends with #shorts), `description`
      (caption + 5–8 hashtags: #shorts #coding #programming #<language> …), `video` (the public URL
      from step 5), `privacy_status: "public"`, `made_for_kids: "false"`, `category_id: "27"`
      (Education), `tags` (list), `notify_subscribers: "true"`.
      Check the result's `channelId` is `UCZ6m5Lh_vmFjOLL_RAHNTxw`; record the video `id`.
   b. **Facebook:** `execute_zapier_write_action` with `selected_api: "FacebookV2CLIAPI"`,
      `action: "page_video"`, `tool_name: "facebook_pages_create_page_video"`, params:
      `page: "926523670552408"`, `source` (same video URL), `title`, `description` (same caption,
      #reels instead of #shorts). Record the returned `id`.
   - If an action fails, fix the reported field and retry once. If it still fails, record the
     error. If Zapier reports the monthly task limit is reached, do not retry; record
     "not posted: Zapier task limit reached".
   - Never post the same video twice: if step a succeeded and b fails, retry only b.

7. **Update the tracker** (`tracker.json`):
   - series slots: `next_part += 1`, append `"Part N: <topic>"` to `posted`
   - other slots: append the topic to `posted`
   - append to `log`: `{"date", "slot", "title", "tone", "hook_format", "video": "<file name>", "status": "queued"}`
   Keep `log` to the latest 100 entries.
   Then: `git add specs tracker.json curriculum.json && git commit -m "<date> <slot>: <topic>"`,
   `git pull --rebase origin main`, `git push origin main`.

8. **Finish** with a one-line summary: slot, title, YouTube video id and Facebook post id (or why a platform wasn't posted).
