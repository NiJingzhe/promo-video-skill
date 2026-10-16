import { Composition } from 'remotion'
import { Promo } from './Promo'
import { DURATION, FPS, H, W } from './marks'

export const Root = () => <Composition id="Promo" component={Promo} durationInFrames={Math.round(DURATION * FPS)} fps={FPS} width={W} height={H} />
