# CareerWithCode Shorts — run instructions

Each scheduled run makes ONE Short of **more than 30 seconds (31–60 s; Abhishek, Oct 29)**, built from **4-6 content images with an ENGLISH voiceover and captions (Abhishek, Nov 1; English only, series only)**, for ONE slot and posts it publicly to YouTube (Short) and
Facebook (image post of the poster, never a reel) through **Zapier only** (step 6). Metricool is no longer used. Instagram is
skipped because Zapier can't post to it.

| Slot (IST) | `SLOT` value   | Content |
|-----------|----------------|---------|
| 20:00     | `go`           | Go series, next part from `curriculum.json` (English) |
| 21:00     | `data_analytics` | Data Analytics series, next part from `curriculum.json` (English). Python series is retired (Abhishek posts it himself). |

Abhishek (Nov 1 2026): CareerWithCode posts only in the night shift (8-9 PM IST), only in English,
and only as series in order (no random one-off topics). The other slots below are retired.


**STYLE + GROWTH RULES (Abhishek, Nov 4 2026, from his Facebook insights review):**
- Light background on every short and post (make_cwc_explainer.py default `"theme": "light"`), and the
  Indian cartoon character (brown skin, "Career With Code" hoodie, drawn by the renderer). Voice stays English.
- HOOK IN THE FIRST 3 SECONDS: scene 1's first `say` sentence is the hook (a question or surprise,
  max 8 words, e.g. "Row or column? Most beginners mix them up!"); the series name and part number
  come after it. Scene 1's first title line is the same hook.
- SUPER-EASY END QUESTION: the last scene asks a one-word choice ("Value or pointer - pick 1",
  "Row or column? Pick 1!"), put it in the sticky `note` and say it; repeat it at the end of the
  YouTube description and Facebook caption.
- Times: Go series 21:30 IST, Data Analytics 22:00 IST (followers are most active around 9:30 PM).

## Tone — every Short must feel different

Each slot has its own voice. Hook, takeaway, CTA and caption must all match it.

| Slot  | Tone | Feel |
|-------|------|------|
| 20:00 Go series | **Friendly teacher** | Clear, encouraging, "let's learn this together". CTA teases the next part. |
| 11:00 educational | **Practical quick win** | Energetic and useful: "Save this", a trick you can use today. |
| 14:00 educational | **Myth-buster / surprising** | "You've been doing this wrong", "Most devs don't know this". |
| 17:00 learn | **Motivating mentor** | Inspiring, growth-focused, speaks to beginners chasing a dev career. |
| 21:00 Python series | **Playful & relatable** | Light humour, relatable dev moments, still teaches the topic properly. |

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
   - `go` / `data_analytics`: topic = `curriculum[SLOT][next_part - 1]`. If the list has run out,
     write the next sensible topic for that series yourself and append it to the list.
   - `educational` / `learn`: choose a topic NOT already in `tracker[SLOT].posted`
     (use the `*_ideas` lists for inspiration; vary languages and formats; never repeat).

3. **Write the spec** (ENGLISH explainer Short, from Nov 1 2026) to `specs/<YYYY-MM-DD>_<HHMM>_<slot>-<slug>.json` (IST).
   Abhishek (Nov 1): "generate images of the content, then make shorts using these images and explain
   in English", and "post only in English on the CareerWithCode channel and page". EVERYTHING is
   English: titles, image text, voice, captions, YouTube title/description, Facebook caption.
   No Hindi, no Hinglish, no Devanagari anywhere. `make_cwc_explainer.py` draws 4-6 content images
   (code editor, output, memory/flow diagrams, checklist) in the CareerWithCode poster look, speaks an
   English voiceover (offline Kokoro, am_michael) and burns in word-by-word English captions.
   Full example: `specs/sample_explainer_list_alias.json`. Scene keys:
   - `title`: 1-3 short English lines (<= 16 chars), `box`: yellow | red optional.
   - `image` (what the scene SHOWS, the real content):
     `{"type": "code", "file": "main.go", "lines": [...], "highlight": [i], "output": [...]}` (lines type in one by one, output last),
     `{"type": "refs", "names": [...], "boxes": [[...]], "links": [[name, box]], "new": [[box, cell]], "label": "..."}` (names pointing at values in memory),
     `{"type": "check", "items": [...], "kind": "check|cross|steps"}`.
   - `face` happy|thinking|worried, `palette` blue|orange|purple (vary them), optional `banner`, `note`, `reveal` (seconds per step).
   - `say`: 1-3 short spoken English sentences explaining that image. Write code as spoken
     ("x colon equals five", "a dot copy"), never raw code.
   - Story: scene 1 = "Go Part N" / "Python Part N" + hook question; middle = code, real output, why;
     last = recap checklist + tease Part N+1 + "Follow CareerWithCode".
   - Code must be correct: run it (go run / python3) and use the real output.

4. **Render:** first `python3 -m pip install -q kokoro-onnx soundfile` (the voice model downloads
   itself from GitHub on first use), then
   `python3 make_cwc_explainer.py specs/<name>.json shorts/<name>.mp4`
   It prints the length; it must be MORE than 30 s and at most 60 s. If the voiceover is too long,
   shorten the `say` lines. Check the images: `python3 make_cwc_explainer.py specs/<name>.json /tmp/imgs --images`
   and Read them (nothing cut off or overlapping, all text English).
   (`make_cwc_story.py` = old Hindi version, no longer used for posting.)

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
   `926523670552408` is in the `page` dropdown of `facebook_pages_create_page_photo`. If a
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
   b. **Facebook (Nov 4 2026): post the SAME video as a Facebook video/reel** (photo posts got 7-10 views;
      reels reach far wider). Find the page video action with inspect_zapier_actions (FacebookV2CLIAPI,
      facebook_pages_create_page_video), page 926523670552408, video = the public mp4 URL. Only if that
      fails twice, fall back to the image post below. (Old rule, 30 Oct: image post only.)
      Make the image: `python3 make_cwc_explainer.py specs/<name>.json shorts/<name>.jpg --still` (the `still_scene` poster as one 1080x1920 JPEG), look at it with Read,
      then publish it: `./publish_video.sh shorts/<name>.jpg` (prints its public URL).
      Post it with `execute_zapier_write_action`, `selected_api: "FacebookV2CLIAPI"`,
      `action: "page_photo"`, `tool_name: "facebook_pages_create_page_photo"`, connection_id
      `0255d81b-a11a-8f8c-9c7a-002223e547ee`, params: `page: "926523670552408"`, `source` (the image URL),
      `message` (the caption + hashtags, no #shorts/#reels). Record the returned `id`.
      Never call `facebook_pages_create_page_video`.
   - If an action fails, fix the reported field and retry once. If it still fails, record the
     error. If Zapier reports the monthly task limit is reached, do not retry; record
     "not posted: Zapier task limit reached".
   - Never post twice: if step a succeeded and b fails, retry only b.

7. **Update the tracker** (`tracker.json`):
   - series slots: `next_part += 1`, append `"Part N: <topic>"` to `posted`
   - other slots: append the topic to `posted`
   - append to `log`: `{"date", "slot", "title", "tone", "hook_format", "video": "<file name>", "status": "queued"}`
   Keep `log` to the latest 100 entries.
   Then: `git add specs tracker.json curriculum.json && git commit -m "<date> <slot>: <topic>"`,
   `git pull --rebase origin main`, `git push origin main`.

8. **Finish** with a one-line summary: slot, title, YouTube video id and Facebook post id (or why a platform wasn't posted).
