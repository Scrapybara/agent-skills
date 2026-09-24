# Music and sound

## What top launches sound like

Based on about 30 launch clips from Cursor, Linear, Codex, Claude, Perplexity, Cline and Replit:

- Many are silent or carried by voice-over.
- The music-led ones sit at 90–125 BPM, mostly 110–120. They use soft synth pulses or a pad over a
  heavy sub, with a large share of the energy below 80 Hz, ticking percussion rather than a full
  kit, and little above 3 kHz.
- There is one lift, not an EDM drop: the music steps up 8–15 dB where the payoff lands.
- Sound design is sparse and synced to picture: UI clicks, whooshes on camera moves, and one impact
  on the reveal.
- End cards resolve on a single hit with a 3–4 s tail. None use a sting.

## Choosing the track

Choose it yourself. Collect 20–30 commercially licensable candidates from libraries such as
Bensound, Mixkit Music and Tonehum, and check each licence's attribution and paid-ads terms. Score
the candidates with `scripts/music.py score <files…>`, which reports:

- build-versus-lift contrast (dB),
- melodic energy (chroma plus 300–4000 Hz energy, so a bare pulse scores low),
- chord movement in the 8 s after the lift,
- spectral richness,
- the three strongest lifts (time in seconds), so you can put one on the payoff; pin the exact hit with `onsets`.

Look at the finalists' spectrograms, then pick. Reject anonymous beds, generic corporate tracks,
pop, hyperpop, and vocal anime or J-pop songs. Record the exact licence text you need to publish.
For example, Bensound free tracks need a per-video attribution line with a licence code and exclude
paid ads.

## Timing

- `scripts/music.py grid <file> <bpm> <from> <to>` prints the beat grid with kick strength.
- `scripts/music.py onsets <file> <from> <to>` shows where the lift lands.
- Put the payoff on the lift: `data-media-start = lift − D`, with later events at `D + n·p`. The
  first visual beat lands exactly on a detected onset.

Run the scripts with `uv run --with librosa --with numpy --with soundfile --with pyloudnorm python …`.

## Sound design layer

`scripts/mix.py` places effects from the video's own `events.json` (written by `build.py`) and mixes
them under the track. Build a kit from CC0 or freely licensed sources, such as Kenney UI Audio (CC0)
and Mixkit sound effects (free licence; download them yourself, don't re-host). The kit that worked:

- keystroke slices, one per typed character, with a little random gain
- a send click, plus a pop for cards and bubbles
- whooshes on camera moves (alternate two), and a soft whoosh on text reveals
- shutter clicks on captures, plus ticks and snaps on beat-locked UI changes
- a riser that ends exactly on the payoff, then an impact and a synthesized sub hit (a sine sweeping
  from about 70 Hz down to 42 Hz, decaying over about 0.45 s)
- a tick on every payoff cut or state flip
- a final hit and sub on the end card, with the music cut at that hit so the tail rings out

## Mix targets

- Music at about −15 to −14 LUFS short-term through the body, and a little lower in a quiet intro.
- The SFX stem about 5–6 LU under the music. The impact and final hit may peak about 2.5 dB over it.
- Duck the music 2–3 dB for about 0.6 s under the impact only.
- Master at −14 LUFS integrated, true peak ≤ −1 dBTP.
- Keep the music audible every second: the per-second RMS of the music stem should sit within about
  4 dB of the full mix.

Render the picture, then mux the mix in:

```bash
ffmpeg -i picture.mp4 -i mix.m4a -map 0:v -map 1:a -c copy -shortest -movflags +faststart out.mp4
```
