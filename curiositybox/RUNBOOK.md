# CuriosityBox Shorts — run instructions

CuriosityBox is a **separate channel** from CareerWithCode. Everything for it lives in
`curiositybox/` and it posts **only** to the CuriosityBox YouTube channel and Facebook page, through **Zapier only**
(step 6; Metricool is not used). Never touch the
CareerWithCode files (`make_short.py`, `tracker.json`, `shorts/`, `specs/` at the repo root)
and never post CuriosityBox content to any CareerWithCode account.

Each scheduled run makes ONE Hindi poster-style Short of **more than 30 seconds (31–60 s, aim for ~35 s; Abhishek, Oct 29)** for ONE slot and posts it
publicly to **YouTube (Short)** and **Facebook as an image post, never a reel** (step 6).

| Slot (IST) | `SLOT`   | Category chip   | Content | Tone |
|-----------|----------|-----------------|---------|------|
| 08:00     | `ai`     | AI & Tech       | A useful AI tool, tech trick or "how AI works" | Practical quick win, energetic |
| 14:00     | `whatif` | What If?        | "Agar ... ho jaye toh?" science question | Wonder, dramatic curiosity |
| 17:00     | `paisa`  | Paisa & Career  | Money basics, career and skills tips | Smart bade bhai/didi, friendly |
| 20:00     | `kahani` | Kahaniyaan      | History, mythology, mystery or country facts (rotate) | Storyteller, suspense |

## Look and music (poster design, from Oct 27 2026)

Abhishek asked for every CuriosityBox Short to look like his design sheet: a cinematic Hindi
poster. Render with **`make_poster_short.py`** (not `make_short.py`). Each video is a 31–60 s (over 30 s, Abhishek Oct 29)
animated poster:

- red brush **category tag** top-left (इतिहास, रहस्य, रोचक तथ्य, विज्ञान, AI & टेक, क्या होगा अगर?)
- big **Devanagari headline** with a black outline, 2–3 lines, white with the key word in yellow
- red brush **banner** with the hook's second half
- a white **fact line** that changes every few seconds: 3–5 `facts` shown one by one (the video is over 30 s, so it needs this to keep giving something new)
- yellow **CTA pill** with an arrow
- dark cinematic background (`scene` + `palette`), slow zoom, embers, original music by `mood`.

The viewer must learn the fact from the screen itself: the banner + line state it, they don't
only tease it. The caption tells the fuller story (2–3 short lines).

Music `mood`: `epic` (history, big science), `mysterious` (mysteries, dark history),
`inspiring` (positive stories), `upbeat` (AI tools, fun facts), `motivational` (career/money).

## Language and style

- On-screen text in **Hindi (Devanagari) only**: the poster font has no English letters, so write English words in Devanagari (चैटजीपीटी, एआई); digits and ! ? , are fine. Keep it short and simple: headline <= 6 words total,
  banner <= 7 words, line <= 9 words, CTA <= 4 words. No emoji in the spec.
- Caption in Hindi/Hinglish, ending with a question; emoji are fine there.
- Rotate the hook format so a slot never repeats its previous one (check that slot's last
  `hook_format` in `tracker.json` `log`): `question`, `shocking-fact`, `myth-vs-fact`,
  `number`, `story-open`, `challenge`.
- What If science and surprising-fact stories get the most views on this channel: prefer them.

## Accuracy rules (important)

- Every fact must be true. For anything current (AI tools, prices, features, rules, salaries)
  **use web search first** and only state what you confirmed. If unsure, leave it out.
- `paisa`: general education only. No specific stocks, funds or "guaranteed returns".
  Add "Ye financial advice nahi hai." at the end of the caption.
- `kahani` mythology: present as a story from the text ("Mahabharat ke anusaar..."), not as
  historical fact. Be respectful to all religions and communities.
- Original content only: no movie/TV footage, no copyrighted characters, no song lyrics.

## Steps

1. **Get the repo.** `git clone https://github.com/Abhishek232110/careerwithcode-shorts`
   (if the session has no access, attach it first with the add_repo tool, push access).
   Work inside `curiositybox/` of the clone.

2. **Pick the topic.** Read `curiositybox/tracker.json` and `curiositybox/ideas.json`.
   Choose a topic for SLOT that is NOT in `tracker[SLOT].posted`. Ideas are inspiration;
   new topics are encouraged.

3. **Write the spec** to `curiositybox/specs/<YYYY-MM-DD>_<HHMM>_<slot>-<slug>.json` (IST):
   ```json
   {
     "category": "kahani",                                  // ai | whatif | paisa | kahani (for the tracker)
     "tag": "इतिहास",                                        // red tag, 1-2 words
     "headline": [{"text": "भारत का वो", "color": "white"},
                  {"text": "मंदिर", "color": "yellow"}],      // 2-3 lines, one yellow key word line
     "banner": "जिसे पहाड़ काटकर बनाया गया!",                 // red banner
     "facts": ["एलोरा का कैलाश मंदिर", "एक ही चट्टान से तराशा गया", "8वीं सदी, राष्ट्रकूट राजा कृष्ण प्रथम", "ऊपर से नीचे की ओर काटा गया"],  // 3-5 lines shown one by one, <= 9 words each
     "cta": "फॉलो करें, रोज़ नया रहस्य",                        // yellow pill, vary it
     "scene": "temple",       // temple | ocean | space | cave | forest | city
     "palette": "gold",       // gold | blue | red | green | purple
     "mood": "epic",
     "duration": 35           // 31-60, never 30 or less
   }
   ```

4. **Render:** `python3 curiositybox/make_poster_short.py curiositybox/specs/<name>.json curiositybox/shorts/<name>.mp4`
   Check it is MORE than 30 s (31–60) and 1080x1920 (`ffprobe`). Preview a still with
   `python3 curiositybox/make_poster_short.py <spec> /tmp/still.png --still` and look at it with
   Read: Hindi must render correctly (no boxes), nothing cut off or overlapping. If it is, shorten
   the text and re-render.

5. **Upload:** `curiositybox/publish.sh curiositybox/shorts/<name>.mp4` → commits the video and
   prints its public URL.

6. **Post through Zapier only** (YouTube step a, then Facebook step b). Never use Metricool,
   `poster/route.py` or `poster/queue_post.py`.
   Load the Zapier tools with ToolSearch (`select:mcp__Zapier__inspect_zapier_actions,mcp__Zapier__execute_zapier_write_action,mcp__Zapier__execute_zapier_read_action`).
   Fixed, verified targets — use exactly these, never any other channel or page:
   - YouTube channel **CuriosityBox | Hindi Facts & Stories**, id `UCtJ6818H8WuXS071samDcPA`.
     The Zapier YouTube default connection is **CareerWithCode**, so never upload without an explicit
     `connection_id`: check each YouTube connection with youtube_make_api_get_request (`url: https://www.googleapis.com/youtube/v3/channels`, `querystring: {"part": "snippet", "mine": "true"}`, `method: GET`, `fail_on_errors: false`; a query string inside the url is dropped and gives a 400) and use only
     the one that returns `UCtJ6818H8WuXS071samDcPA`. If none does, skip YouTube and record why. (Verified 2026-10-27: connection `02a3b5ba-1d92-8570-b393-026313523e1c` reaches it.)
   - Facebook page **CuriosityBox Hindi Facts & Stories**, page id `1380858578445805`
     (Zapier connection `0255d81b-a11a-8f8c-9c7a-002223e547ee`)

   Runs start ~20 min early. Wait (sleep) until the slot time before posting, because Zapier
   publishes immediately. If the slot time has already passed, post right away.

   a. **YouTube:** `execute_zapier_write_action` with `selected_api: "YouTubeV4CLIAPI"`,
      `action: "upload_video"`, `tool_name: "youtube_upload_video"`, params:
      `title` (<= 90 chars, Hindi or Hinglish, ends with #shorts), `description` (caption + hashtags),
      `video` (the public URL from step 5), `privacy_status: "public"`, `made_for_kids: "false"`,
      `category_id: "27"` (Education), `tags` (list), `default_language: "hi"`,
      `default_audio_language: "hi"`, `notify_subscribers: "true"`.
      Check the result's `channelId` is `UCtJ6818H8WuXS071samDcPA`; record the video `id`.
   b. **Facebook: IMAGE POST ONLY, never a video or reel** (Abhishek, 30 Oct 2026).
      Make the poster image: `python3 curiositybox/make_poster_short.py curiositybox/specs/<name>.json curiositybox/shorts/<name>.jpg --still` (one 1080x1920 JPEG of the poster), look at it with Read,
      then publish it: `curiositybox/publish.sh curiositybox/shorts/<name>.jpg` (prints its public URL).
      Post it with `execute_zapier_write_action`, `selected_api: "FacebookV2CLIAPI"`,
      `action: "page_photo"`, `tool_name: "facebook_pages_create_page_photo"`, connection_id
      `0255d81b-a11a-8f8c-9c7a-002223e547ee`, params: `page: "1380858578445805"`, `source` (the image URL),
      `message` (the caption + hashtags, no #shorts/#reels). Record the returned `id`.
      Never call `facebook_pages_create_page_video`.
   - If an action fails, fix the reported field and retry once. If it still fails, record the
     error. If Zapier reports the monthly task limit is reached, do not retry; record
     "not posted: Zapier task limit reached".
   - Never post twice: if step a succeeded and b fails, retry only b.

7. **Caption rules:** 2–3 line Hindi or Hinglish caption that tells the fuller story and ends with a question, then 5–8 hashtags
   (#shorts #hindifacts #curiositybox + topic tags). `paisa` captions end with
   "Ye financial advice nahi hai." before the hashtags.

8. **Update the tracker** (`curiositybox/tracker.json`): append the topic to `tracker[SLOT].posted`
   and append to `log`: `{"date", "slot", "title", "tone", "hook_format", "video", "status"}`.
   Keep `log` to the latest 100 entries. Then:
   `git add curiositybox && git commit -m "curiositybox <date> <slot>: <topic>"`,
   `git pull --rebase origin main`, `git push origin main`.

9. **Finish** with a one-line summary: slot, title, YouTube video id and Facebook post id (or what failed).
