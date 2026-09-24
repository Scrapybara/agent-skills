# Banger video

Makes short product launch and feature videos in the style of the best software launches: a product display cut on the beat, not a screen-recorded demo. The agent researches similar launches, rebuilds the product's real UI as HTML + GSAP, picks and times the music, adds sound design, renders with HyperFrames, and checks every frame before delivering an MP4.

## Structure

- `SKILL.md` - The rules and the end-to-end workflow
- `references/`
  - `research.md` - Finding and studying reference launch clips
  - `capture.md` - Capturing whole components and measured geometry from a running app
  - `music-and-sound.md` - Choosing a track, finding its lift, sound design, and mix targets
  - `hyperframes.md` - Building, linting, snapshotting, and rendering compositions
  - `patterns.md` - Beat sheets for formats that worked
- `scripts/`
  - `music.py` - Beat grid, onsets, and candidate-track scoring
  - `mix.py` - Events-driven music + sound-effects mix, mastered to -14 LUFS / -1 dBTP

## Requirements

- Node.js (for `npx hyperframes`) and ffmpeg
- Python via `uv run --with librosa --with numpy --with soundfile --with pyloudnorm python scripts/…`

## When to use

- "Make a launch video for our new search page"
- "Make a 20 second feature video for the new dashboard"
- "Make something like this launch clip for our product"
