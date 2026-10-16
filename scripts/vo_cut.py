# /// script
# dependencies = ["numpy"]
# ///
"""Cut one ElevenLabs take (many lines separated by <break>s) into one clip per line, levelled.

    uv run vo_cut.py full.mp3 --regions vo/cuts.json --out vo/       # spans marked with cut_ui.py (best)
    uv run vo_cut.py full.mp3 --lines 12 --ends 3,6.7,9,... --out vo/ # or by approximate end times

Without --ends it works only if the speech falls into exactly --lines stretches (otherwise it lists
what it found and asks). With --ends (the time each line
ends in the take, which ElevenLabs' player shows) the take is windowed there and each window is
trimmed to its speech - use it whenever the automatic split is not exactly right.

Each clip is padded 0.12 s before / 0.2 s after, compressed lightly, loudness-normalised to
-15 LUFS (spoken word that sits on top of music) and limited. Writes vo_NN.wav and clips.json:
  {n, file, clip_start, lead, speech, duration}   lead = padding before the first word, so a clip placed at
  (wanted_speech_start - lead) starts speaking exactly when you want it.
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("audio"); ap.add_argument("--lines", type=int, default=0)
ap.add_argument("--regions", help="cuts.json written by cut_ui.py: the exact span of every line (preferred)")
ap.add_argument("--out", default="vo"); ap.add_argument("--ends")
ap.add_argument("--prefix", default="vo"); ap.add_argument("--lufs", type=float, default=-15)
ap.add_argument("--thresh-db", type=float, default=-38)
a = ap.parse_args()

SR = 48000
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.audio, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.float32)
frame = SR // 100
env_db = 20 * np.log10(np.sqrt(np.convolve(x[: len(x) // frame * frame] ** 2, np.ones(frame) / frame, "valid")[::frame]) + 1e-9)
loud = env_db > env_db.max() + a.thresh_db  # speech frames, threshold relative to the loudest

def segments(mask, min_gap):
    segs, start = [], None
    for i, m in enumerate(mask):
        if m and start is None: start = i
        if not m and start is not None: segs.append([start, i]); start = None
    if start is not None: segs.append([start, len(mask)])
    out = []
    for s in segs:                                 # close tiny gaps inside a word
        if out and s[0] - out[-1][1] < min_gap: out[-1][1] = s[1]
        else: out.append(s)
    return out

segs = segments(loud, 8)
def window_picks(cuts):
    """windows between cuts, each trimmed to the speech inside it"""
    cuts = [0.0] + list(cuts) + [len(env_db) / 100]
    picked = []
    for lo, hi in zip(cuts, cuts[1:]):
        inside = [s for s in segs if s[1] / 100 > lo and s[0] / 100 < hi]
        assert inside, f"no speech between {lo:.2f}s and {hi:.2f}s: a cut is misplaced"
        picked.append([max(inside[0][0] / 100, lo), min(inside[-1][1] / 100, hi)])
    return picked


if a.regions:
    data = json.load(open(a.regions))
    if data.get("mode") == "cuts":                  # cut_ui.py: the human clicked between the lines
        picked = window_picks(data["cuts"])
    else:
        picked = [[i["start"], i["end"]] for i in data["items"]]
    assert not a.lines or len(picked) == a.lines, f"{len(picked)} lines in {a.regions}, expected {a.lines}"
elif a.ends:
    assert a.lines, "--lines is required with --ends"
    ends = [float(v) for v in a.ends.split(",")]
    assert len(ends) == a.lines, f"--ends has {len(ends)} values, --lines is {a.lines}"
    # each end time is approximate (the player rounds, and you read it off by ear): cut at the longest pause
    # within 1.2 s of it, then trim every window to its speech
    gaps = [((a0[1] + b0[0]) / 200, (b0[0] - a0[1]) / 100) for a0, b0 in zip(segs, segs[1:])]  # (centre s, length s)
    cuts = [0.0]
    for e in ends[:-1]:
        near = [g for g in gaps if abs(g[0] - e) <= 1.2]
        assert near, f"no pause within 1.2 s of {e}s: check the end time"
        cuts.append(max(near, key=lambda g: g[1])[0])
    cuts.append(len(env_db) / 100)
    picked = []
    for lo, hi in zip(cuts, cuts[1:]):
        inside = [s for s in segs if s[1] / 100 > lo and s[0] / 100 < hi]
        assert inside, f"no speech between {lo}s and {hi}s"
        picked.append([max(inside[0][0] / 100, lo), min(inside[-1][1] / 100, hi)])
else:
    if len(segs) != a.lines:
        # A <break time="0.3s"> inside a line renders as ~0.9 s of silence, about as long as the pause between
        # lines, so pause length cannot tell them apart. Show what was found and ask for the line ends.
        print(f"found {len(segs)} stretches of speech, expected {a.lines} lines:")
        for i, (s0, s1) in enumerate(segs): print(f"  {i+1:2d}  {s0/100:6.2f} - {s1/100:6.2f}s")
        raise SystemExit("rerun with --ends <end time of each line in the take, comma separated> (the ElevenLabs player shows them)")
    picked = [[s[0] / 100, s[1] / 100] for s in segs]

out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
clips = []
for n, (s, e) in enumerate(picked, 1):
    lead, tail = 0.12, 0.2
    start = max(0.0, s - lead); lead = s - start
    dur = e + tail - start
    f = f"{a.prefix}_{n:02d}.wav"
    chain = f"acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120,loudnorm=I={a.lufs}:TP=-1.5:LRA=7,alimiter=limit=0.89"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", a.audio, "-af", chain + ",afade=t=in:d=0.01,afade=t=out:st=%.3f:d=0.15" % (dur - 0.15), "-ar", "48000", str(out / f)], check=True)
    clips.append({"n": n, "file": f, "clip_start": round(start, 3), "lead": round(lead, 3), "speech": round(e - s, 3), "duration": round(dur, 3)})
    print(f"{n:2d}  take {s:6.2f}-{e:6.2f}s  speech {e-s:5.2f}s  -> {f}")
json.dump(clips, open(out / "clips.json", "w"), indent=1)
