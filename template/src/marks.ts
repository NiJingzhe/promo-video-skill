// The film's clock. EVERYTHING in the picture is placed against this file: the music's marks, the beat grid
// and when each voice-over line starts. Scenes never hard-code a time, they import it from here, so when the
// music or the voice changes you edit one place.
import beatData from './data/beats.json'   // from scripts/music_analyze.py (shifted to video time, see below)
import clips from './data/clips.json'      // from scripts/vo_cut.py

export const FPS = 60
export const W = 1920
export const H = 1080
export const DURATION = 10                 // seconds, = the music's length

/** Hard marks you found in the music (video time): drops, stabs, silences, breakdowns, phrase changes. */
export const MARK = { drop: 4.0, fade: 8.5 } as const

/** Beat length from the analyzer's *fitted* tempo. Never type a BPM you guessed. */
export const BEAT = beatData.beat
/** Beat times in video time (data/beats.json is already in the music file's own time = video time). */
export const beats: number[] = beatData.beats.filter((b) => b < DURATION)
export const snap = (t: number) => beats.find((b) => b >= t - 1e-6) ?? t           // the next beat at/after t
export const beatPhase = (t: number) => { let last = 0; for (const b of beats) { if (b <= t) last = b; else return (t - last) / (b - last) } return 0 }
export const pulse = (t: number, decay = 5) => Math.exp(-decay * beatPhase(t))      // 1 on the beat, decaying

/** When each voice-over line starts SPEAKING (video seconds). clips.json's `lead` is the padding before the first word. */
export const SPEAK: number[] = []
export interface Clip { n: number; file: string; clip_start: number; lead: number; speech: number; duration: number }
export const voice = (clips as Clip[]).map((c, i) => ({ ...c, at: SPEAK[i] - c.lead }))

export const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x))
export const seg = (t: number, a: number, b: number) => clamp((t - a) / (b - a))    // 0..1 progress of t between a and b
export const lerp = (a: number, b: number, k: number) => a + (b - a) * k
export const easeInOut = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2)
export const easeOut = (x: number) => 1 - Math.pow(1 - x, 3)
export const easeOutExpo = (x: number) => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * x))
