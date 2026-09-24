# Research

Study launch clips of the same kind of feature before designing anything.

## Finding clips

- **launcharchive.ai company pages** list launch posts at
  `https://launcharchive.ai/companies/<company>` (cursor, linear, openai, anthropic, replit, github,
  vercel, and others). Slugs end in `--x_<postId>`.
- **X videos without a login:** `curl -s https://api.fxtwitter.com/status/<postId>` returns
  `tweet.media.all[].formats[]`. Take the mp4 at or below about 2.5 Mbps.
- **YouTube:** `uv tool install yt-dlp`, then
  `yt-dlp -f "bv*[height<=720][ext=mp4]+ba/b[height<=720]" --merge-output-format mp4 <url>`.
- **Teardown sites** such as impractical.ai and videngineer.com break down well-known launch films
  shot by shot.

## Watching

```bash
d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 clip.mp4)
ffmpeg -loglevel error -y -i clip.mp4 -vf "fps=$(python3 -c "print(min(3,48/$d))"),scale=300:-2,tile=8x6" -frames:v 1 sheet.jpg
ffmpeg -loglevel error -y -ss 3.5 -t 3 -i clip.mp4 -vf "fps=10,scale=320:-2,tile=8x4" detail.jpg
```

For each clip, note the background, whether the UI is built or captured, the camera move, the
type, the cuts per beat, the end card, and the audio: music versus sound design, tempo, and where
the hits land.

## What the strongest launches share

- **Cursor "Orchestrate":** a prompt is typed, then an animated tree grows (planner → sub-agents →
  workers and verifiers that turn green). Clean lines on white, with the logo at the end.
- **Cursor "Origin":** one sentence carries the story, with real UI chips inline ("Create a repo
  and start a [+ New] project"), and the camera pushes into the chip on the beat.
- **Linear "Diffs" and "Releases":** dark and restrained, with a single lift in the music, hard
  cuts, a short end line, and then the logo.
- **Codex Sites:** bracket typography ("Go from [idea] to (deployment)") and a fast collage finish.
- **Claude Cowork and Code desktop:** a cream background, one large component at a time, and lots of
  white space.
- **Cursor Auto-review and SDK:** launches that are only a diagram or only code, which suit features
  with no UI.

What fails: literal copies of a flashy style (gradient blobs, mosaic wipes), 3D screenshot planes,
and a cursor-driven tour of mocked apps.
