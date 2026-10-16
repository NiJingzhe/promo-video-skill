---
name: promo-video
description: Make a beat-synced product promo / launch film end to end with a human in the loop - pick music (Epidemic Sound "Create a cut"), design the storyboard together, write the shot script and an ElevenLabs voice-over script, cut the returned voice take, then build the video in Remotion (three.js metal renders, replicas of the product UI, virtual-camera push/pull/pan, every cut on the beat). Use when the user wants a promo video, trailer, launch film, product teaser, motion-graphics ad, or asks to sync video to music or generate a storyboard + VO script.
---

# promo-video

A film is made in six stages. **Each stage ends with something the human checks.** Do not run ahead:
the expensive stage (the build) is only cheap if the earlier ones are settled, because every picture event
is placed against the music and the voice.

Say the plan to the human once at the start (README.md has the human-facing version), then run the stages in
order. Talk to them in their language. Keep every project file in one directory (`<project>/`: `audio/`, `vo/`,
`PLAN.md`, `elevenlabs.md`, the Remotion project in `video/`).

| # | Stage | You do | Human does | Reference |
|---|---|---|---|---|
| 1 | Music | analyse the track, find the true tempo and the hard marks | picks the track on Epidemic Sound, uses **Create a cut** for the length, gives you the file | [references/01-music.md](references/01-music.md) |
| 2 | Storyboard | ask the guiding questions, write `PLAN.md` (shot table timed to the music) | answers, approves | [references/02-storyboard.md](references/02-storyboard.md) |
| 3 | Voice script | write the lines + the tagged ElevenLabs take | generates it in ElevenLabs, sends the file | [references/03-voiceover.md](references/03-voiceover.md) |
| 4 | Cut the voice | open `cut_ui.py` on the take, then split, level, place each line | clicks between the lines in the browser page, presses Done; checks the placement table | [references/03-voiceover.md](references/03-voiceover.md) |
| 5 | Build | Remotion project from `template/`, scene by scene, still-check each | reviews stills / a draft render | [references/04-build.md](references/04-build.md) |
| 6 | Review + polish | render, loudness check, open `review_ui.py` on the render, read their notes + frames, fix, re-render | watches in the review page, leaves notes on the picture, picks Approved / Needs changes | [references/05-review.md](references/05-review.md) |

## Browser automation: offer it, never assume it

Stages 1 and 3 happen on websites (Epidemic Sound, ElevenLabs). If a browser-automation skill or tool is
available (e.g. `ego-browser`, a Playwright setup, a browser MCP), **offer to do those parts yourself**, and say
plainly what that involves before asking for a yes:

- **Accounts**: both sites need an account (Epidemic Sound is a paid subscription with a trial; ElevenLabs has a
  free tier with a monthly character limit). If the human has none, *they* sign up: you do not create accounts.
- **Cost**: ElevenLabs bills by characters; a 40-60 s film is ~600-1000 characters, and every re-generation is
  charged again. Epidemic downloads count against the plan. Tell them the expected spend and ask first.
- **Login and payment are the human's**: hand the browser over (`task.handOff()` in ego-browser) for sign-in,
  2FA, captchas and any payment screen; resume after they say done. Never type their password, never enter or
  store card details, never paste their API key into a page or file.
- **What you may do after a yes**: search/filter tracks by the agreed mood and BPM and open candidates for them
  to listen (they choose), click *Create a cut* with the target length and download the result; paste the
  `elevenlabs.md` take, apply the voice and settings they picked, generate once, download the mp3.
- Without such a tool, or if they decline: give them the exact steps (stage 1 and 3 documents) and wait for the file.

The choices stay theirs: the track and the voice are never picked for them.

## Ground rules (learned the hard way)

1. **Everything shown is real.** Real example meshes (tessellate the actual CAD/STEP), real code and API in
   code panels, the UI rebuilt from the product's own frontend components. Fake-looking content is the one
   thing viewers notice. If you cannot get the real thing, say so and ask - do not invent it.
2. **The music is the clock.** Measure the true tempo (`scripts/music_analyze.py` fits it; a guessed BPM
   that is 1.2 % off puts a splice a third of a beat out and the human hears a stumble). All times live in
   `src/marks.ts`; scenes import them, never hard-code seconds.
3. **Confirm outward-facing or expensive steps**: the music file and the voice are the human's to choose; you
   never pick them for them. Never print API keys or login tokens that show up in the product you film.
4. **Check pictures with stills**, not by faith: render the frames at the marks (beat hits, cuts, the logo)
   and look at them before a full render. A full render takes minutes; a still takes seconds.
5. **Keep the old version.** When the human asks for a cut-down or variant, copy the project directory and
   edit the copy (`cp -R video video_short`, symlink `node_modules`).
6. **Report like an editor**: what changed, the file path, what to listen/watch for and at which second.

## Tools in this skill

All Python scripts run with `uv run` (dependencies are declared in each file; nothing to install).

| Script | Purpose |
|---|---|
| `scripts/music_analyze.py track.wav --out beats.json` | true BPM (fitted), beat/bar grid, sections, drop, silent gaps |
| `scripts/music_splice.py track.wav out.wav --beats beats.json --keep a:b --keep c:d` | shorten a track by a bar-aligned, crossfaded jump; verifies the join |
| `scripts/cut_ui.py take.mp3 --mode cuts --script elevenlabs.md --out vo/cuts.json` | **browser cutting page** (waveform, the script shown line by line, speech vs pauses, zoom, undo/redo): the human plays it and clicks where a line ends, presses Done, the tab closes and `cuts.json` lands for you. `--mode marks --beats beats.json` marks the music's drop/stab/breakdown on the beat grid |
| `scripts/vo_cut.py take.mp3 --regions vo/cuts.json --out vo/` | split an ElevenLabs take into levelled clips + `clips.json` (or `--lines N --ends t1,...` if the human prefers typing times) |
| `scripts/review_ui.py out/promo.mp4 --out review/review.json [--overlay overlay.json]` | **browser review page**: monitor on top, timeline strip below (filmstrip + the finished mix's waveform + optional beats / marks / voice lines). The human leaves notes at a moment or over a range; each note carries the exact frame; they finish with Approved / Needs changes and `review.json` lands for you |
| `scripts/new_project.sh <dir> [--link-modules path]` | Remotion project from `template/` (metal stage, beat clock, VO mix, virtual camera) |
| `template/tools/mesh.py` | STEP/OCC shapes -> compact mesh + B-rep edges for three.js |
| `template/tools/refold.py` | blank the huge STEP metadata strings OCC cannot read |
| `template/tools/variants.py`, `stages.py` | mesh parameter variants / every intermediate solid of a CAD notebook (for "drag a slider, the model follows" and "cell by cell" scenes) |

Needs: `ffmpeg`, `node` 20+, `uv`. For three.js in headless Chrome: playwright's chrome-headless-shell
(`new_project.sh` installs it).
