import { Config } from '@remotion/cli/config'
import fs from 'node:fs'
import path from 'node:path'
import os from 'node:os'

// WebGL in headless Chrome: Remotion's default browser has no usable GPU path for three.js on macOS, the
// playwright chrome-headless-shell with ANGLE does. `npx playwright-core install chromium-headless-shell` once.
const shells = path.join(os.homedir(), 'Library/Caches/ms-playwright')
const shell = fs.existsSync(shells) ? fs.readdirSync(shells).filter((d) => d.startsWith('chromium_headless_shell')).sort().pop() : undefined
if (shell) {
  const dir = path.join(shells, shell)
  const bin = fs.readdirSync(dir).map((d) => path.join(dir, d, 'chrome-headless-shell')).find(fs.existsSync)
  if (bin) Config.setBrowserExecutable(bin)
}
Config.setVideoImageFormat('png')       // PNG frames: no JPEG banding in gradients and dithers
Config.setChromiumOpenGlRenderer('angle')
Config.setConcurrency(4)
// AUDIO_ONLY=1 renders just the mix (a .wav) so you can rebalance audio without re-rendering the picture
if (!process.env.AUDIO_ONLY) { Config.setCodec('h264'); Config.setCrf(14); Config.setPixelFormat('yuv420p') }
