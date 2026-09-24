# Capturing real UI

Use real geometry and whole components. Never crop rectangles out of a screenshot.

## Whole components

If the product is a web app you can run locally or on a staging URL, drive it with Playwright at
`deviceScaleFactor: 3` and screenshot the element itself:

```js
const el = page.getByText("Needs you").locator("xpath=ancestor::section[1]");
await el.screenshot({ path: "needs-you.png" });
```

To find the whole component around a text label, walk up from the label to the largest ancestor
that doesn't yet contain unrelated neighbouring sections. Park the mouse off-screen before
capturing so no hover state gets baked in. Capture both themes if the video might use either.

## Typing

To show an input being typed into, type one character at a time and screenshot the input element
after each keystroke. Play the frames back at a slightly uneven rate (±10 ms), with a longer pause
on spaces.

## Geometry

After the first build, load the generated `index.html` in a headless browser. Measure every element
the timeline aims at, such as tag widths, label widths and row positions, and write the numbers to
`widths.json`. The build reads that file, so every tween targets real pixel positions. Don't use
function-valued tweens that measure layout at render time: they aren't deterministic across render
workers.

## Montage captures

For a set of N variants (themes, wallpapers, templates), script the settings change and capture the
same screen for each one. Score the captures, for example by mean saturation × brightness in the
region the viewer will look at, and keep the strongest. When a setting pairs with an asset, match
them automatically, such as picking the theme whose accent hue is closest to the asset's dominant
hue.

## When there's no runnable UI

Rebuild the components as HTML from the product's design tokens (colours, radii, type scale, icon
set), keeping them flat and clean. Don't mock whole third-party apps.
