---
name: banger-video
description: >
  Makes premium product launch and feature videos (15–25 s, 1080p60, cut on the beat) as HTML +
  GSAP compositions rendered with HyperFrames. Use when asked for a launch video, feature video,
  promo, teaser, product montage, sizzle, or "a video like <some launch clip>" for any product.
license: MIT
metadata:
  author: scrapybara
  version: "1.0.0"
---

# Banger video

Short product videos in the style of the best software launches: a product display, not a demo.
They are built as HTML and GSAP, rendered to MP4 with the HyperFrames CLI, and cut on the music's
beat grid. The bar is whether a client would pay $10k for it, so work as a motion designer and
editor, not a screen recorder.

## Rules

Each rule came from a rejected cut.

1. **Product display, never a demo.** No mouse cursor driving the UI, no clicking through settings,
   no screen-recorded walkthroughs, no narration captions. If the product has an agent that acts,
   show the agent acting, not a person operating the app.
2. **No raw screenshots in the frame.** No arbitrary rectangle crops of screenshots, no
   spotlight / "dim the rest" highlights, no glow rings, and no drifting 3D screenshot planes with
   fake depth of field. Rebuild the UI as clean HTML graphics from the product's own design tokens.
   A real capture is allowed only as a whole component grabbed from the actual element
   (`references/capture.md`). Mock apps that look fake are worse than no apps.
3. **Pixel-exact.** Anything that marks UI (tags, outlines, avatars, badges) is positioned from
   measured geometry of the laid-out page, never eyeballed.
4. **One concept per video.** Every video in a set gets its own idea and look, such as a light flat
   diagram, a dark living document, or a full-frame montage. Never reuse one template across
   features.
5. **Show the product doing the work, with nothing to read.** The payoff is a visible change of
   state: lines swap red→green, tags flip to "✓ Resolved", statuses turn green, a counter completes.
   Never a paragraph, an expanded comment card, or a diff the viewer has to parse. Use one short
   line per beat at most.
6. **Research first.** Before designing, find launch clips of the same kind of feature from the best
   companies and study them frame by frame (`references/research.md`). Name the clip whose
   structure you are borrowing.
7. **Never cut mid-animation.** Before cutting any footage, including your own renders, map it into
   transitions and settled states at 30 fps. A cut enters on a settled frame or the exact start of a
   transition, and exits on a settled frame. A hero change, such as several items resolving, is one
   continuous shot: speed-ramp the dull parts 1.6–2× and keep each state change at real speed,
   landing on a beat or half-beat.
8. **Stay on topic.** If the story is "make X", the payoff shows only X. Don't pad it with shots from
   other videos.
9. **Montages:** the first and last item hold for about 1.5–2 s, and everything between is
   split-second (one beat or half a beat). Keep them full frame, with no zoom or push-ins, no
   per-item labels, and no end-card slogan unless asked.
10. **Music leads, sound design supports, and you choose.** Pick the track yourself with the method
    in `references/music-and-sound.md` rather than sending rounds of previews. Pop, hyperpop, anime
    songs and generic corporate beds all read wrong for a launch, and so does a quiet bed buried
    under sound effects.
11. **Verify every frame yourself** before delivering: contact sheets at 4–10 fps over the whole
    cut, 30 fps strips around every cut and hero moment, and full-res stills of key frames. If you
    can no longer look at images, hand the check to a fresh agent rather than ship unchecked.

## Workflow

1. **Brief** in one message: the feature, a one-sentence story of what the product does, the
   reference clip, the look, and the music.
2. **Research** (`references/research.md`): pull 5–15 relevant launch clips and write down what the
   best ones do.
3. **Real content:** use the product's real strings (names, IDs, file names, statuses), design
   tokens, fonts and icons. If it's a web app you can run, capture exact geometry and whole
   components from it (`references/capture.md`).
4. **Music:** choose and time the track (`scripts/music.py`, `references/music-and-sound.md`). Fix
   the lift offset and the beat period `p` before writing any timeline.
5. **Build** (`references/hyperframes.md`): a `build.py` holds the beat schedule (`B(n) = D + n*p`),
   generates `index.html` from a template, and writes an `events.json` of every moment that should
   make a sound. Measure the real layout into `widths.json` once, then rebuild.
6. **Check:** run `npx --yes hyperframes lint`, then `snapshot --at …`, look at the frames, and
   iterate.
7. **Render the picture:** run `render -q high -f 60 -w 2` as a background job. More workers can
   exhaust a 16 GB machine.
8. **Mix and mux the audio yourself** (`scripts/mix.py`, then ffmpeg `-c copy`). The renderer's
   audio path can change levels.
9. **Deliver:** attach the MP4 and state its duration, the track, and its licence terms
   (attribution text, paid-ads limits).

Beat sheets that worked are in `references/patterns.md`.
