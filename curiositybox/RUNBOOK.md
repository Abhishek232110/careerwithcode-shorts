# CuriosityBox Shorts — run instructions

CuriosityBox is a **separate channel** from CareerWithCode. Everything for it lives in
`curiositybox/` and it posts **only** to the CuriosityBox Metricool brand. Never touch the
CareerWithCode files (`make_short.py`, `tracker.json`, `shorts/`, `specs/` at the repo root)
and never post CuriosityBox content to the Career With Code brand (blogId `7393281`).

Each scheduled run makes ONE Hinglish Short of **20–30 seconds** for ONE slot and posts it
publicly to **YouTube (Short)** and **Facebook (Reel)** through Metricool.

| Slot (IST) | `SLOT`   | Category chip   | Content | Tone |
|-----------|----------|-----------------|---------|------|
| 08:00     | `ai`     | AI & Tech       | A useful AI tool, tech trick or "how AI works" | Practical quick win, energetic |
| 14:00     | `whatif` | What If?        | "Agar ... ho jaye toh?" science question | Wonder, dramatic curiosity |
| 17:00     | `paisa`  | Paisa & Career  | Money basics, career and skills tips | Smart bade bhai/didi, friendly |
| 20:00     | `kahani` | Kahaniyaan      | History, mythology, mystery or country facts (rotate) | Storyteller, suspense |

## Language and style

- All on-screen text and captions in **Hinglish (Hindi in Latin script)**, the way people
  actually talk: short, casual, warm. No emoji in the spec (the video font can't draw them);
  emoji are fine in the caption.
- Rotate the hook format so a slot never repeats its previous one (check that slot's last
  `hook_format` in `tracker.json` `log`): `question`, `shocking-fact`, `myth-vs-fact`,
  `number-list` ("3 baatein jo..."), `story-open` ("Saal 1912..."), `challenge`.
- Vary CTA and caption wording every time; end the caption with a question to drive comments.

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
     "category": "whatif",                          // ai | whatif | paisa | kahani
     "hook": "Agar Chand Gayab Ho Jaye Toh?",       // <= 7 words, curiosity-driven
     "points": [                                    // 3 cards (4 max)
       {"title": "<= 5 words", "text": "<= 16 words"}
     ],
     "takeaway": "<= 12 words, the punchline",
     "cta": "Follow karo, roz ek naya sawaal",      // <= 6 words, vary it
     "duration": 25                                 // 20-30, more text = longer
   }
   ```

4. **Render:** `python3 curiositybox/make_short.py curiositybox/specs/<name>.json curiositybox/shorts/<name>.mp4`
   Check it is 20–30 s and 1080x1920 (`ffprobe`). Extract frames at ~8 s and 1 s before the end
   and look at them with Read: no text overlapping or running off screen. If it does, shorten
   the text and re-render.

5. **Upload:** `curiositybox/publish.sh curiositybox/shorts/<name>.mp4` → commits the video and
   prints its public URL.

6. **Find the brand.** Call Metricool `getBrandSettings` and pick the brand whose `label`
   contains "curiosity" (case-insensitive). Use its `id` as `blogId`.
   - If there is **no such brand**, or it has no YouTube/Facebook connected: do NOT post
     anywhere. Set the log `status` to `"rendered, not posted: CuriosityBox brand not connected in Metricool"`
     and continue at step 8.
   - Only post to the networks that brand has connected (`youtubeData`, `facebookData`).

7. **Post** with Metricool `createScheduledPost`:
   - `blogId`: the CuriosityBox brand id from step 6
   - `date`: today at the slot time exactly (e.g. `17:00:00+05:30`). Runs start ~15 min early.
     If the slot time has already passed, use now + 3 minutes.
   - `info`:
     - `providers`: `[{"network":"youtube"},{"network":"facebook"}]`
     - `media`: `[<video URL>]`
     - `publicationDate`: `{"dateTime": "<same time, no offset>", "timezone": "Asia/Calcutta"}`
     - `text`: 1–2 line Hinglish caption + 5–8 hashtags (#shorts #hindifacts #curiositybox + topic tags)
     - `autoPublish`: true, `draft`: false
     - `youtubeData`: `{"title": "<= 90 chars, Hinglish, ends with #shorts", "type": "short",
        "privacy": "public", "madeForKids": false, "category": "EDUCATION",
        "tags": [...], "isAiGeneratedContent": false}`
     - `facebookData`: `{"type": "REEL"}`
   - If Metricool rejects the post, fix the reported field and retry once. If it still fails,
     do not retry further; record the error.

8. **Update the tracker** (`curiositybox/tracker.json`): append the topic to `tracker[SLOT].posted`
   and append to `log`: `{"date", "slot", "title", "tone", "hook_format", "video", "status"}`.
   Keep `log` to the latest 100 entries. Then:
   `git add curiositybox && git commit -m "curiositybox <date> <slot>: <topic>"`,
   `git pull --rebase origin main`, `git push origin main`.

9. **Finish** with a one-line summary: slot, title, and whether the post succeeded.
