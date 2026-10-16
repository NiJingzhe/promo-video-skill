# /// script
# dependencies = ["librosa", "numpy", "soundfile"]
# ///
"""Cut a track shorter by jumping from one bar line to another, hidden by a beat-aligned crossfade.

    uv run music_splice.py track.wav out.wav --beats beats.json \
        --keep 11.19:43.34 --keep 55.75:63.0 [--fade-beats 2] [--fade-in 1.6]

Each --keep is a span of the source. Consecutive spans are joined with a linear crossfade of
--fade-beats beats CENTRED on the join, and the join points are snapped to bar lines of the grid in
--beats, so the drums of both sides coincide while they overlap. The jump must be a whole number of
bars (the script nudges the second point to make it so and prints how far it moved). It then
verifies the result: cross-correlating the beat envelope before and after the join must peak at the
expected lag; if it is off by more than 30 ms the splice would be heard as a stumble.
"""
import argparse
import json

import librosa
import numpy as np
import soundfile as sf

ap = argparse.ArgumentParser()
ap.add_argument("audio"); ap.add_argument("out")
ap.add_argument("--beats", required=True)
ap.add_argument("--keep", action="append", required=True, help="start:end of a source span (seconds); repeat")
ap.add_argument("--fade-beats", type=float, default=2.0)
ap.add_argument("--fade-in", type=float, default=0.0, help="fade in the very start (s)")
ap.add_argument("--fade-out", type=float, default=0.0, help="fade out the very end (s)")
a = ap.parse_args()

g = json.load(open(a.beats))
beat, bars = g["beat"], np.array(g["bars"]) + g.get("trim_start", 0)
y, sr = sf.read(a.audio, always_2d=True)
spans = [tuple(float(x) for x in s.split(":")) for s in a.keep]
snap = lambda t: float(bars[np.argmin(abs(bars - t))])

# snap joins to bar lines; make each jump a whole number of bars
joins = []  # (end of span i, start of span i+1) on bar lines
for (s0, e0), (s1, e1) in zip(spans, spans[1:]):
    A = snap(e0); B = snap(s1)
    jump = (B - A) / (beat * 4)
    if abs(jump - round(jump)) > 0.02:
        B = A + round(jump) * beat * 4
        print(f"  nudged the second join point to {B:.3f}s so the jump is {round(jump)} whole bars")
    joins.append((A, B))
    print(f"join: {A:.3f}s -> {B:.3f}s  = {(B-A)/beat:.1f} beats")

half = a.fade_beats * beat / 2
pieces = []
for i, (s, e) in enumerate(spans):
    start = s if i == 0 else joins[i - 1][1] - half
    end = e if i == len(spans) - 1 else joins[i][0] + half
    pieces.append(y[int(start * sr):int(end * sr)])
out = pieces[0]
n = int(2 * half * sr)
for p in pieces[1:]:
    ramp = np.linspace(0, 1, n)[:, None]
    mixed = out[-n:] * (1 - ramp) + p[:n] * ramp
    out = np.concatenate([out[:-n], mixed, p[n:]])
if a.fade_in:  out[:int(a.fade_in * sr)] *= np.linspace(0, 1, int(a.fade_in * sr))[:, None]
if a.fade_out: out[-int(a.fade_out * sr):] *= np.linspace(1, 0, int(a.fade_out * sr))[:, None]
sf.write(a.out, out, sr, subtype="PCM_16")
print(f"wrote {a.out}: {len(out)/sr:.2f}s")

# verify each join: the beat envelope after it must be the one before it, shifted by whole beats
mono = librosa.to_mono(out.T) if out.ndim > 1 else out
env = librosa.onset.onset_strength(y=mono, sr=sr, hop_length=256)
fps = sr / 256
t = 0.0
for (A, B), p in zip(joins, pieces[:-1]):
    t += len(p) / sr - half            # the join's centre in the output
    w = int(4 * beat * fps)
    c = int(t * fps)
    before, after = env[c - 3 * w // 2: c - w // 2], env[c + w // 2: c + 3 * w // 2]
    if len(before) == len(after) and len(before) > 8:
        cc = np.correlate(after - after.mean(), before - before.mean(), "full")
        lags = (np.arange(len(cc)) - (len(before) - 1)) / fps
        near = abs(lags) < beat / 2  # a phase error is less than half a beat; the beat itself repeats
        lag = lags[near][np.argmax(cc[near])]
        err = abs(lag)
        print(f"check @ {t:.2f}s: the bar after the join lines up with the bar before it to within {err*1000:.0f} ms  {'OK' if err < 0.03 else 'AUDIBLE STUMBLE - choose other bars'}")
