# Stages 5-6 - Build in Remotion, render, polish

## Start

```bash
scripts/new_project.sh <project>/video                      # npm install + headless shell
scripts/new_project.sh <project>/video --link-modules <other project>/node_modules   # reuse installed modules
cd <project>/video && npm run studio                         # live preview;  npm run still  = one frame
```

Then, in this order: `src/data/beats.json` (from the analyser, in video time) and `src/data/clips.json`;
`public/` gets the music and the vo clips; `src/marks.ts` gets `DURATION`, `MARK`, `SPEAK`; then scenes.
`Promo.tsx` shows scenes by time window (`t < MARK.x`) and mixes audio. Un-comment the music `<Audio>`.

Architecture that worked: **one scene file per movement** (Opening / Product / Finale); `marks.ts` is the only
place with times; `three/` for WebGL, `ui/` for the product replica, `lib/VirtualCamera.tsx` for 2D flights.

## Pictures (three.js)

- **Model data is real**: `template/tools/mesh.py` tessellates STEP/OCC shapes (`python mesh.py out/ name=file.step=0.05`;
  the last number is the tessellation tolerance, 0.04-0.05 for parts a few hundred mm across) into
  `public/mesh/<name>.json+.bin`; `three/mesh.ts: loadModel(name)` reads it. If OCC cannot read a STEP
  ("string too long"), run `refold.py in.step out.step`. For "the model follows a slider" / "cell by cell"
  scenes, `variants.py` / `stages.py` re-run the real notebook with other parameters / mesh each stage.
  Only parameter values that satisfy the model's own guards work: probe them first, pick ranges that build.
- **Look = studio light, not scene lights.** `Stage.lightWith(softboxes)` builds the PMREM environment from
  emissive strips; metal reflects them. A key strip that **orbits continuously** gives the moving highlight
  of product films; never reset the angle (it visibly jumps). Rims from behind, a dim top fill, a faint bottom.
  Soft-looking metal needs roughness variation: `METALS.*` add a world-space grain to roughness.
- DOF (`stage.bokeh`), bloom, vignette and grain are on in `Stage`; raise aperture only for macro shots.
- **Assemblies**: place parts by their joints (a group per joint, `userData.home` for the rest pose),
  drive angles from `t`; land each part on a beat (`CUT_C + (k+0.5)*BEAT`). Motors/cables can be omitted.
- **Retro-futurist dither** = `stage.grade.uniforms.dither` (Bayer 8x8, `ink` colour). Use it once, for the
  logo end card, so it reads as a brand accent, not a gimmick.
- **Logo ending**: put the real logo bitmap on screen and *fit 3D to the bitmap*, not the other way round
  (trace its faces, back-project onto the cube planes) so the 3D object and the logo coincide at the lock.
  Hold 2-3 s, tagline typed under it.

## Product UI replica

The human asked for the UI to be **rebuilt from the product's own frontend code** (so the camera is free to fly):

- Alias the product's source into Remotion's webpack (`'@'` -> `../web/src`), add its `node_modules` to
  `resolve.modules`, and pin **one** React (`alias.react`). Import real components; give them mock data.
- Fixed-size "screen" div (e.g. 1600x900, scaled 1.2) inside `VirtualCamera` with keyframes. Keyframes land on
  beats; clamp so the screen always fills the frame; add a few degrees of rotateX/Y for parallax.
- **Drive animations from the video clock** (`useSyncCssAnimations`) and any typing/streaming from `t`
  (characters = (t - start) * rate). Never wall-clock `setTimeout`/`useEffect` timers.
- English UI for an English film (set the product's locale).
- **Content must be real and plausible**: take a recorded real conversation / transaction if one exists (an
  example task's log) for what the agent says and the tools it calls. Use the product's real example code
  (form and API); invent nothing the product could not output.
- Camera should follow the action: to the text being typed, the todo list, the cell that just ran. An empty
  area in frame while something happens elsewhere is the most common amateur look.
- A "drag a slider" scene: replicate the real control (including its modified/orange state, revert and
  write-to-source), send drags every 60 ms as the product does, swap the model's mesh per step on **8th notes**.
- Before the reveal: fade UI out + a silent black beat + **flash-in** on the drop; never cross-dissolve into it.

## Motion rules

- Easing: `easeInOut` for camera moves, `easeOutExpo` for things landing, `pulse(t)` for a beat kick.
- Every cut, landing, camera move start = a time from `beats` (`snap(t)`), big ones on bars.
- A move needs 1.2-3 s. Faster than 0.6 s reads as a glitch unless it is a whip-pan *on* a beat.
- Two simultaneous moves (camera + object) must differ in speed/direction (parallax).
- Never show a UI state that did not just change: no dead air.

## QA before every full render

1. `npx tsc --noEmit`
2. Stills at: each cut, each beat-event, the drop (one frame before / on / after), the logo lock, the last
   frame. Make a contact sheet (ffmpeg `tile`) and look at it.
3. A 6-second draft of the hardest section (`remotion render ... --frames=a-b`), then the full.
4. Audio: `ffmpeg -i out.mp4 -af loudnorm=print_format=summary -f null -` -> about -15.5 LUFS, peak < -1 dBFS.
5. Hand over with the path and the length, then run the review page (stage 6, `05-review.md`) instead of asking for free-text feedback.

## Render

```bash
npx remotion render src/index.ts Promo out/promo.mp4          # h264, crf 14, png frames, concurrency 4
AUDIO_ONLY=1 npx remotion render src/index.ts Promo out/mix.wav --codec=wav   # remix without the picture
```

1920x1080x60: expect 1-3 s per frame for the three.js shots on an M-series Mac: a 40 s film takes ~15-40 min.
Run long renders in the background and sample frames while it runs.

## Gotchas (each cost time once)

| Symptom | Cause / fix |
|---|---|
| Config crash `import.meta.dirname` | use `process.cwd()` in `remotion.config.ts` |
| Custom font absent in frames | register with `new FontFace(..., staticFile(file))` + `document.fonts.load` inside `delayRender`; CSS `url()` is resolved as a module |
| WebGL black / "context lost" | use playwright's chrome-headless-shell + `setChromiumOpenGlRenderer('angle')` |
| Mesh flickers between frames | build objects once in `setup`; set everything from `t` in `direct`, no `useState` timers |
| Highlight jumps when a shot repeats | key-light angle must be a continuous function of absolute `t` |
| Voice clips silent | ffmpeg `-ss/-to` must be INPUT options (before `-i`) |
| A splice "hitches" | the tempo was guessed; re-fit with `music_analyze.py`, cut on its bars, crossfade 2 beats |
| UI mark below / beside the logo at the end | an interpolation ramp whose start is after its end; ramp proportionally to the span |
| Event is a frame late | `Math.round(sec*FPS)` consistently; Sequence `from` is in frames |
| Cut-down version | copy the project dir, change `marks.ts` (marks, `SPEAK`, `DURATION`) and drop scenes |
