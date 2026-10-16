# /// script
# dependencies = ["librosa", "numpy", "soundfile"]
# ///
"""Read a music track the way an editor would: true tempo, beat grid, sections, the drop.

    uv run music_analyze.py track.wav --out beats.json [--trim-start 0]

Prints a summary and writes {bpm, beat, offset, beats[], bars[], sections[], marks{}}.
The tempo is refined by fitting a line through the tracked beats: a tracker's rounded BPM drifts a
frame or two per bar, and a 0.5 % tempo error is a third of a beat out of phase after 40 s
(that is what made an early splice "hitch"). Always cut on THIS grid, never on a guessed BPM.
"""
import argparse
import json

import librosa
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("audio")
ap.add_argument("--out", default="beats.json")
ap.add_argument("--trim-start", type=float, default=0.0, help="seconds of the file to ignore (leading silence)")
a = ap.parse_args()

y, sr = librosa.load(a.audio, sr=22050, mono=True)
y = y[int(a.trim_start * sr):]
dur = len(y) / sr
hop = 512
oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
tempo, frames = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=hop, tightness=200)
bt = librosa.frames_to_time(frames, sr=sr, hop_length=hop)

# refine: scan tempi finely; the right one puts a beat grid on the onset peaks across the WHOLE track
# (a tracker's own BPM is rounded and drifts; 0.5 % is a third of a beat out of phase after 40 s)
t0 = float(np.atleast_1d(tempo)[0])
fps = sr / hop
best = (-1, t0, 0.0)
for cand in np.arange(t0 * 0.94, t0 * 1.06, 0.01):
    b = 60 / cand
    for off in np.arange(0, b, 0.01):
        idx = np.round((off + b * np.arange(int((dur - off) / b))) * fps).astype(int)
        idx = idx[idx < len(oenv)]
        score = oenv[idx].mean()
        if score > best[0]: best = (score, cand, off)
_, bpm, offset = best
beat = 60 / bpm
grid = offset + beat * np.arange(0, int((dur - offset) / beat) + 1)

# which beat of the bar is the downbeat: the one whose low-band onsets are strongest, every 4th beat
S = np.abs(librosa.stft(y, hop_length=hop)) ** 2
low = np.sqrt(S[:12].sum(0))
fr = librosa.time_to_frames(grid, sr=sr, hop_length=hop).clip(0, len(low) - 1)
phase = int(np.argmax([low[fr[p::4]].mean() for p in range(4)]))
bars = grid[phase::4]

# sections: loudness per bar, a section starts where it changes a lot
rms = librosa.feature.rms(y=y, hop_length=hop)[0]
t_rms = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
db = librosa.amplitude_to_db(rms + 1e-9)
per_bar = np.array([db[(t_rms >= b0) & (t_rms < b1)].mean() for b0, b1 in zip(bars[:-1], bars[1:]) if ((t_rms >= b0) & (t_rms < b1)).any()])
per_bar = np.maximum(per_bar, per_bar.max() - 25)  # silence is not a section
jumps = np.diff(per_bar)
sections = []
for i in np.argsort(-np.abs(jumps))[:8]:
    if abs(jumps[i]) >= 3.0:
        sections.append({"t": round(float(bars[i + 1]), 3), "change_db": round(float(jumps[i]), 1), "kind": "drop/up" if jumps[i] > 0 else "breakdown/down"})
sections.sort(key=lambda s: s["t"])
drop = max((s for s in sections if s["change_db"] > 0), key=lambda s: s["change_db"], default=None)

# near-silence gaps (a stab then a gap is the classic pre-drop; a held silence makes a good black beat)
quiet = db < db.max() - 40
gaps, start = [], None
for t, q in zip(t_rms, quiet):
    if q and start is None: start = t
    if not q and start is not None:
        if t - start > 0.25: gaps.append([round(float(start), 3), round(float(t), 3)])
        start = None

out = {
    "file": a.audio, "trim_start": a.trim_start, "duration": round(dur, 3),
    "bpm": round(float(bpm), 3), "beat": round(float(beat), 5), "offset": round(float(offset), 4),
    "bar": round(float(beat * 4), 4), "downbeat_phase": phase,
    "beats": [round(float(t), 4) for t in grid], "bars": [round(float(t), 4) for t in bars],
    "sections": sections, "silent_gaps": gaps, "drop": drop,
}
json.dump(out, open(a.out, "w"))
print(f"{a.audio}: {dur:.1f}s  {bpm:.2f} BPM (beat {beat:.4f}s, bar {beat*4:.3f}s)  first beat {offset:.3f}s")
print("sections (bar-aligned loudness changes):")
for s in sections: print(f"  {s['t']:7.2f}s  {s['change_db']:+5.1f} dB  {s['kind']}")
print("silent gaps:", gaps or "none")
print(f"-> {a.out}  (beats[] and bars[] are in this file's own time, after --trim-start)")
