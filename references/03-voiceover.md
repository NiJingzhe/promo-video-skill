# Stages 3-4 - Voice-over: write, generate (human), cut

## Write the lines (if the human wants a voice)

- English by default unless told otherwise. Short, concrete, spoken: 3-9 words a line. No jargon the
  viewer has to parse. Verbs. One idea per line. Rhythm matters more than grammar: "Any part. Any structure."
- Count the lines against the storyboard: each line has a **target start time** tied to a mark (a line on the
  drop, a calm line in the breakdown). Do not write more words than the shot gives time for: speech runs at
  ~2.5-3 words per second.
- The product name must be pronounced right. If the voice says it wrong, put a phonetic spelling in the text
  field only (e.g. "Fizz-Space" for an invented brand name that is read wrongly); the film shows the real spelling.
- To compress a film later, choose a subset of lines (the best 8 of 12) rather than speeding them up.

## Give the human an ElevenLabs script

Write `elevenlabs.md`: the **take** (one paste, all lines, with `<break time="..." />` between), the settings
to use, and a table of the lines with their target start in the film. Format that worked:

```
Imagine being able to make anything. <break time="1.0s" /> Any part. <break time="0.3s" /> Any structure. <break time="1.0s" /> ...
```

- Between **lines** use 1.0 s (1.5 s before a big moment); inside a line use 0.3 s. Note that a 0.3 s break
  renders as ~0.9 s of silence, nearly as long as a between-line pause - which is why you cut by the times
  the human reads off, not by gap length.
- Generating it as **one take** keeps the same voice, pace and energy through all lines. Do not generate
  line by line.
- Direction in prose goes in the table, not the text field ("07 is calm and close; 08 lifts on 'live'").
  ElevenLabs reads whatever is in the text field aloud.

*If a browser-automation skill is available, offer to run ElevenLabs for them: say it needs their ElevenLabs account (they sign in; you never touch the password or payment), that generation spends their character quota or credits (~1 character per letter of the take; every regeneration is charged again; give the number), and that they choose the voice (you can audition 2-3 candidates on a single sample line, which also costs a little). After a yes: paste the take, set the chosen voice and settings, generate once, download the mp3. If they decline, they do it with the steps below.*

Tell the human how to do it:
1. elevenlabs.io -> Text to Speech -> pick a voice. For a promo: a confident, warm, medium-low voice. Preview a
   line with 2-3 candidates; they choose. Settings used before: model Multilingual v2/v3, stability ~40-50,
   similarity ~75, style ~20-30 (more = more dramatic).
2. Paste the take, generate, download the mp3.
3. Send me the downloaded file's path. (No need to read times off: you will mark the lines in a browser editor I open.)

If the human has already chosen how to do the voice (own recording, another tool), take that file and the
same list of end times.

## Cut and place (you)

Open the cutting page on the take, with the script so the human can see what they should be hearing
(run it in the background; you are notified when they press Done):

```bash
uv run scripts/cut_ui.py vo/take.mp3 --mode cuts --script elevenlabs.md --out vo/cuts.json
```

`--script` takes `elevenlabs.md` (it reads the `| 01 | line text | ... |` table) or a text file with one line per row.
Tell the human, in these words: "A tab opened. The right side is the script, line by line; the waveform is the whole
take. Press **Space** and listen. Every time one line ends, **click in the pause after it** (or press **C** while it
plays): a red cut line appears. The orange piece and the highlighted script line show which line you are hearing.
No need to be exact - anywhere in the pause is fine. **Suggest cuts** gives a first guess (it is often wrong where a
line has a short break inside it, so check by ear). Press **Done** when the top right says all lines cut." If no tab
opens, give them the printed `http://127.0.0.1:...` URL. Exit code 0 = done (`vo/cuts.json` has `cuts[]` and the
pieces), 2 = cancelled: ask what they want.

```bash
uv run scripts/vo_cut.py vo/take.mp3 --regions vo/cuts.json --out vo/
```

(Each piece is trimmed to the speech inside it, so cuts in the middle of a pause are right. Without the page, `--lines 12 --ends 3,6.7,9,...` cuts at the longest pause near each approximate end time.)

Each clip is padded 0.12 s before / 0.2 s after, compressed lightly and loudness-normalised to -15 LUFS with a limiter.
`clips.json` records `lead` (the padding before the first word) and `duration`.

Copy `vo/vo_NN.wav` to the Remotion `public/` and `vo/clips.json` to `src/data/clips.json`. In `marks.ts`, set
`SPEAK[]` = when each line should *start speaking* in the film; the clip is placed at `SPEAK[i] - lead`.

Place by the marks: a line **on** the drop, lines in the breakdown start on a bar line, last line on the
build. Never let two lines overlap. Leave the picture 0.2-0.5 s of air before a line starts.

Tell the human the placement table (line / text / start / end) before building. If they chose to drop
lines to fit a shorter film, keep the numbering and just omit them from `SPEAK` (the short cut used a
`KEEP = {1: 0.7, 3: 3.9, ...}` map from line number to start).

## Mix (in `Promo.tsx`)

Music keeps a low level in a quiet intro (0.85), 0.5 after the drop, and dips x0.62 under each line (0.15 s
in, 0.25 s out) - set by ear. If the human says the voice is too quiet: lower the music body, not raise
the voice past -15 LUFS. Check the final mix: loudness around -15.5 LUFS, peak under -1 dBFS
(`ffmpeg -i out.mp4 -af loudnorm=print_format=summary -f null -`).
