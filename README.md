# careerwithcode-shorts

Automation for the CareerWithCode channel: 5 coding Shorts a day, posted to
YouTube, Instagram and Facebook via Metricool.

- `make_short.py` – renders a 15 s, 1080x1920 code-explainer video from a JSON spec
- `publish_video.sh` – uploads a video to the `media` branch and prints its public URL
- `curriculum.json` – ordered Go and Python series topics + idea lists
- `tracker.json` – which series part is next and what has been posted
- `RUNBOOK.md` – the steps each scheduled run follows

To change the series order, edit `curriculum.json`. To jump a series to a
different part, change `next_part` in `tracker.json`.
