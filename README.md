# careerwithcode-shorts

Automation for the CareerWithCode channel: 5 coding Shorts a day (20–30 s each), posted to
YouTube, Instagram and Facebook via Metricool.

- `make_short.py` – renders a 15 s, 1080x1920 code-explainer video from a JSON spec
- `publish_video.sh` – commits a video to `shorts/` and prints its public URL
- `shorts/` – every video posted, kept permanently
- `specs/` – the script (JSON) behind every video
- `curriculum.json` – ordered Go and Python series topics + idea lists
- `tracker.json` – which series part is next and what has been posted
- `RUNBOOK.md` – the steps each scheduled run follows

To change the series order, edit `curriculum.json`. To jump a series to a
different part, change `next_part` in `tracker.json`.

## CuriosityBox (separate channel)

`curiositybox/` holds the automation for the separate Hindi channel CuriosityBox: 4 Shorts a
day (08:00, 14:00, 17:00, 20:00 IST) on YouTube and Facebook. It has its own renderer,
specs, videos, tracker and runbook (`curiositybox/RUNBOOK.md`) and never touches the
CareerWithCode files above.
