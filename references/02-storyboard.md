# Stage 2 - Storyboard

You design with the human, then write it down as a shot table timed to the music. Do not start building until
they approve the table.

## Ask (3-5 questions at a time, with your recommended answer for each)

1. **What is it and who is it for?** One sentence a stranger would understand. Who watches (customers,
   investors, engineers) and where (landing page autoplay muted? a launch event with sound?). Muted autoplay =
   captions needed; event = voice-over.
2. **The one idea.** What should the viewer remember? ("describe it, an agent builds it, drag a slider and it
   follows"). A 40 s film carries one idea and at most two proofs.
3. **Must show / must not show.** Real product screens, a specific feature, a logo ending, example output.
   Anything confidential (keys, user data, internal names)? These are never filmed.
4. **Look.** Offer 2-3 concrete options with a reference each: *dark studio + metal macro* (product film),
   *light UI-forward* (SaaS), *retro-futurist dither* (brand accent; use once, for the logo), motion references
   the human likes (e.g. a competitor's launch film: ask for a link and sample frames from it).
5. **Voice-over?** Yes / no / one line only. And language. Captions?
6. **Length and format.** 30-60 s, 1920x1080 at 60 fps by default; vertical 9:16 only if asked.

If the human is unsure, propose a default and say what it costs to change later.

## The film's grammar (use unless told otherwise)

A product film in four movements, matched to the music's structure:

| Movement | Music | Picture | Voice |
|---|---|---|---|
| Hook | quiet intro, riser | an object or question, slow, beautiful, no UI | the premise, 1-3 short lines |
| Reveal | **drop** | the product, hard cut or flash in. Silence + black one beat before it | the product name |
| Proof | body; breakdown + re-push | the feature in action, real UI, camera follows the action; a second feature on the re-push | what it does, one line each |
| Close | build, last phrase | scale-up or collapse into the logo; hold | the tagline, last |

Rules that make it feel like a launch film, not a screen recording:
- **Cut on beats, move on bars.** Every cut, every UI event, every camera move lands on a beat time from
  `marks.ts`. Big camera moves start on a bar line. Nothing happens off-grid unless it is meant (a drag
  eased across 8th notes is fine).
- **Camera never sits still**: push-in during reveals, pull-back to show scale, trucks/pans that follow the
  eye (to the text being typed, to the cell that just changed), small orbit for parallax. 1.2-3 s per move.
- **One thing at a time on screen.** Zoom so the part that matters fills the frame; the rest blurs or exits.
- **Show the real output**: the model after each step, the numbers changing. Never lorem ipsum.
- **Silence is a shot.** A beat of black before the drop, a calm line under a thinned-out breakdown.
- **End on a still logo** with enough hold (2-3 s) and a tagline; fade with the music.

## Write `PLAN.md`

```
# <Product> promo - <N> s - 1920x1080 60fps - VO: yes/no

## Music  (file, true BPM, marks in video time)
| mark | t | what you hear |

## Storyboard
| t (s) | picture (what is on screen, the camera move) | on which beat/mark | VO line |

## Real material to gather
(list: meshes, code files, UI components, logo file, fonts)
```

Read it back to the human in 5 lines, ask "approve / change?" Only then go to stage 3 (voice) and 5 (build).
