// Fly a "camera" over a 2D UI (a replica of your product's screen) with push, pull, pan, tilt and orbit.
// The screen is a fixed-size div; the camera is a transform on its parent, driven by keyframes. The rules that
// make it look filmed rather than zoomed:
//   * ease between keyframes (easeInOut), and put keyframes ON beats;
//   * clamp x/y so the screen always covers the frame (no black edges), except where you want to leave it;
//   * rx/ry tilt reveals the screen's edge (a black sliver) when the clamp is tight: keep tilts <= 6 deg, or
//     make `screen` larger than the visible UI and fill it with the same background;
//   * a little rx/ry (a few degrees) with CSS perspective gives parallax: layers at different translateZ slide;
//   * CSS animations/transitions inside the UI must be driven from the video clock (useSyncCssAnimations),
//     otherwise they run in wall time and every render comes out different.
import { useLayoutEffect } from 'react'
import { easeInOut, lerp, seg } from '../marks'

export interface Key { t: number; x: number; y: number; z: number; rx?: number; ry?: number }

export function cameraAt(keys: Key[], t: number, screen: { w: number; h: number }, frame: { w: number; h: number }) {
  let i = keys.findIndex((k) => k.t > t)
  if (i < 0) i = keys.length
  const a = keys[Math.max(0, i - 1)], b = keys[Math.min(keys.length - 1, i)]
  const k = a === b ? 0 : easeInOut(seg(t, a.t, b.t))
  const z = lerp(a.z, b.z, k)
  const halfW = frame.w / 2 / z, halfH = frame.h / 2 / z   // how much of the screen the frame shows
  const x = Math.min(screen.w - halfW, Math.max(halfW, lerp(a.x, b.x, k)))
  const y = Math.min(screen.h - halfH, Math.max(halfH, lerp(a.y, b.y, k)))
  return { x, y, z, rx: lerp(a.rx ?? 0, b.rx ?? 0, k), ry: lerp(a.ry ?? 0, b.ry ?? 0, k) }
}

export function useSyncCssAnimations(t: number) {
  useLayoutEffect(() => { document.getAnimations().forEach((a) => { a.pause(); a.currentTime = t * 1000 }) })
}

/** <VirtualCamera keys=... t=...>{screen}</VirtualCamera>: `screen` is laid out at w x h, the frame is W x H. */
export function VirtualCamera({ keys, t, screen, frame, children }: { keys: Key[]; t: number; screen: { w: number; h: number }; frame: { w: number; h: number }; children: React.ReactNode }) {
  const c = cameraAt(keys, t, screen, frame)
  useSyncCssAnimations(t)
  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', background: '#000', perspective: 2600 }}>
      <div style={{ position: 'absolute', left: 0, top: 0, width: screen.w, height: screen.h, transformOrigin: `${c.x}px ${c.y}px`,
        transform: `translate(${frame.w / 2 - c.x}px, ${frame.h / 2 - c.y}px) scale(${c.z}) rotateX(${c.rx}deg) rotateY(${c.ry}deg)` }}>
        {children}
      </div>
    </div>
  )
}
