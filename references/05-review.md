# Stage 6 - Review the render with the human

Free-text feedback ("it hitches somewhere around the middle") is slow and vague. The review page lets the human
point at the picture itself, and gives you the frame they were looking at.

```bash
uv run scripts/review_ui.py out/promo.mp4 --out review/review.json --overlay review/overlay.json
```

Run it in the background; a tab opens (print the URL if it does not). Tell the human: "Watch it in the top monitor,
or drag along the strip underneath. When something should change, press **M** (or *Note here*): the frame you are on
is attached. To cover a stretch, drag on the red *Notes* track first. Write what to change. Press *Finish review* and pick
*Approved* or *Needs changes*."

Layout: monitor + notes on top; timeline underneath with the **filmstrip**, the **finished mix's waveform** (the audio
is already in the film, so there are no separate tracks), and from `--overlay` the **beat grid** (bar lines bolder), the
**music marks** and the **voice-over lines**. Seeing a cut next to its beat is the whole point: build the overlay from
`marks.ts`:

```json
{"beats":[0.43,0.95,...], "marks":[{"t":7.34,"label":"drop"}], "vo":[{"start":0.7,"end":3.3,"text":"Imagine being able to make anything."}]}
```

Keys: Space play, ←/→ one frame, Shift+←/→ one second, M note, Del delete note, Cmd/Ctrl+Z undo, Cmd/Ctrl+scroll zoom.

## Reading the result

Exit code 0: `review/review.json` = `{verdict, summary, notes:[{id, t, end, timecode, text, frame}]}`; `frame` is a png path.
Exit code 2: cancelled, ask what they want.

1. **Look at every note's frame** with the Read tool (it shows images) before touching code: it is exactly what they saw.
2. Map each note to the scene/time in `marks.ts` and the storyboard; group notes that share a cause.
3. Tell them back in one table: note -> what you will change. Ask only about notes that are ambiguous.
4. Fix, re-render only what changed (`--frames=a-b` for a draft), run the review page again on the new file and
   pass `--out review/review_2.json`. Repeat until the verdict is *Approved*.

The page plays whatever the browser can play: H.264/AAC mp4 (what the template renders) is fine in Chrome, Safari and Edge.
