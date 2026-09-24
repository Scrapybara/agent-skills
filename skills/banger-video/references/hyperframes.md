# HyperFrames notes

HyperFrames (`npx --yes hyperframes@<version>`, from HeyGen) renders HTML with GSAP timelines to
MP4. Pin the version in `package.json` so re-renders match.

## Structure

- The root is `<div id="root" data-composition-id="main" data-start="0" data-duration="T" data-width="1920" data-height="1080">`.
- Register one paused timeline: `window.__timelines["main"] = gsap.timeline({ paused: true })`.
- Every timed element needs `data-start` and `data-duration`, plus `class="clip"`.
  `data-track-index` only sets the display lane.
- Name templates `src.tpl`, so the project root has only one `.html` file with a composition id.

## Media

- Audio: `<audio id="music" src=… data-start="0" data-duration="T" data-media-start="<offset>">`.
  Without an `id` it renders silent. For final delivery, mix the audio separately and mux it in.
- Video: `<video id=… muted data-start … data-media-start …>` must sit at the top level. When nested
  inside a wrapper that has its own `data-start`, it pulls the wrong frames.

## Motion

- Animate transforms (`x`, `y`, `scale`, `rotate`), not `left` or `top`, which snap to whole
  pixels.
- Tween colours as hex or rgb. GSAP interpolates `oklch()` and `color-mix()` wrong, which shows as
  neon flashes.
- Don't overlap relative `+=` tweens with another tween on the same property. Add
  `immediateRender: false` to repeated `fromTo` calls, or set a baseline at 0.
- Keep it deterministic: use a seeded PRNG, never `Date.now()` or `Math.random()`. Read measured
  layout from `widths.json`.
- House text reveal: wrap each word in `<span class="w">` and stagger opacity, y and blur(10px→0)
  with `expo.out`. To swap a status in place, blur the old word out and the new one in, never
  cross-fade.

## Checking and rendering

- Loop: `lint`, then `snapshot --at 1.2,3.4,… --no-end --describe false`, then tile the snapshots
  with ffmpeg and look at them.
- Render: `render -q high -f 60 -w 2 -o out.mp4`. With 2 workers it takes about 3–4 s of wall time
  per second of video. Run it as a background job.
