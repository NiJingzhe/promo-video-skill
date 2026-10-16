import { AbsoluteFill, Audio, Sequence, staticFile } from 'remotion'
import { FPS, MARK, lerp, seg, voice } from './marks'
import { Demo } from './scenes/Demo'

// The mix. The music sits at `body` and dips ~4 dB under every voice line (0.15 s in, 0.25 s out), so the voice
// is always on top without a hard duck. The voice clips are levelled to about -15 LUFS by vo_cut.py.
function bgmVolume(t: number): number {
  const body = lerp(0.85, 0.5, seg(t, MARK.drop - 0.3, MARK.drop + 0.3))   // quiet intro, louder body: tune by ear
  const under = Math.max(0, ...voice.map((v) => Math.min(seg(t, v.at - 0.05, v.at + 0.1), 1 - seg(t, v.at + v.duration - 0.1, v.at + v.duration + 0.15))))
  return body * lerp(1, 0.62, under)
}

export const Promo = () => (
  <AbsoluteFill style={{ background: '#000' }}>
    {/* <Audio src={staticFile('bgm.wav')} volume={(f) => bgmVolume(f / FPS)} /> */}
    {voice.map((v) => (
      <Sequence key={v.file} from={Math.round(v.at * FPS)} durationInFrames={Math.ceil(v.duration * FPS) + 2}>
        <Audio src={staticFile(v.file)} volume={1} />
      </Sequence>
    ))}
    <Demo />
  </AbsoluteFill>
)
void bgmVolume
