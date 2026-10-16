# Stage 1 - Music

## Ask the human to choose it (do not choose for them)

*If a browser-automation skill is available (ego-browser, Playwright), offer to do the searching and the download. Say it needs an Epidemic Sound account/subscription (the human signs in; you never handle the password or payment), may count against their plan, and that they still pick the track: you shortlist 3-5 by mood/BPM, they listen and choose, then you click **Create a cut** for the target length and download it.*

Music sets the film's mood, length and rhythm, so it comes first. Send the human this, adapted:

> Pick the track on **Epidemic Sound** (royalty-free, so the film can ship). Open a track you like and click
> the **scissors icon -> "Create a cut"**: it re-edits the original into a version of the length you ask
> for, with a proper start and ending (no chopped bar). Ask for roughly the film's length (e.g. 45 s).
> Download it (WAV if offered) and give me the path. Tell me the feel you want: calm / urgent / playful /
> cinematic, and whether you want a *drop* (a quiet intro that explodes) or a steady groove.

What to look for in a track for a product film: a **clear quiet intro** (room for a slow reveal), an obvious
**drop or phrase change** about 1/3 in (the hero moment), **breakdown + re-push** later (room for a second
beat of the story), a **build** into the final phrase (the logo), and a clean tail. Steady four-on-the-floor
at 100-125 BPM cuts best.

If it later has to be shorter than the cut Epidemic gave, do not fade-and-trim: use `music_splice.py`
(below) or go back to Epidemic for another cut.

## Analyse it

```bash
uv run scripts/music_analyze.py audio/track.wav --out audio/beats.json
```

If the analyser's drop / breakdown guesses are doubtful, or the human wants to pick the hit points themselves, open the
marker editor on the track (background; it exits when they press Done):

```bash
uv run scripts/cut_ui.py audio/track.wav --mode marks --beats audio/beats.json --labels stab,drop,breakdown,repush,build,logo --out audio/marks.json
```

The beat grid is drawn over the waveform and markers snap to it; click to drop a marker, drag to move, name it in the
side list. `marks.json` -> `MARK` in `marks.ts` (items with `start == end`).

Read the printout to the human in plain words: "116.0 BPM, one bar is 2.07 s; the loud part starts at
19.6 s; the music thins out at 32.0 s and comes back at 36.1 s". Then **listen-check the marks**: render
a click or just cut 3 s around each mark with ffmpeg and ask the human to confirm "that is the drop" if
the analyser's guess is ambiguous. Write the confirmed marks into `PLAN.md` (stab, silence, drop,
breakdown, re-push, build, last phrase, fade).

Facts learned:
- Fitted tempo matters. A tracker said 117.45; the true tempo was 116.00. Cuts built on the wrong grid
  drift ~0.2 s by 40 s, and a splice on it was 0.16 s out of phase - audible as a stumble.
- Drop to re-push is usually 16 or 32 beats. Check `beats` from the drop onward are exactly `beat` apart.
- Many tracks start with silence. Pass `--trim-start` or shift video time so the first beat is near 0.5 s.
- The *downbeat* (which beat is "1") is a guess from low-frequency energy; snap events to **beats**, put
  big moves on **bars** (every 4th beat from the drop).

## Making it shorter (only when asked)

To keep the film within, say, 40 s: pick two bar lines an exact number of bars apart on the *same* drum
pattern (e.g. the end of a repeated 8-bar block and the start of a later one), and jump between them with
a crossfade of 2 beats centred on the join:

```bash
uv run scripts/music_splice.py audio/track.wav audio/short.wav --beats audio/beats.json \
    --keep 11.19:43.34 --keep 55.75:63.0 --fade-in 1.6
```

The script snaps joins to bar lines, forces a whole number of bars, mixes with a linear crossfade, and
**verifies** by cross-correlating the bar before and after the join (must be within 30 ms). Then re-run
`music_analyze.py` on the new file - all marks move; update `marks.ts` from the new analysis. Ask the human
to listen to the join before building on it.

Pre-roll: put a riser/silence in the ending of the intro; **a held silence of 0.4-0.5 s right before the drop**
makes the drop hit harder (the picture goes black and silent too).
