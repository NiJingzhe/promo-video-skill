// A starting scene: one metal part, a studio of moving softboxes, a camera that pushes in. Replace it.
// The pattern to keep: StageView builds objects once (`setup`) and `direct` sets everything from `t` every frame.
import * as THREE from 'three'
import { AbsoluteFill } from 'remotion'
import { StageView } from '../three/StageView'
import { METALS, type Softbox } from '../three/stage'
import { easeInOut, pulse, seg } from '../marks'

const studio = (t: number): Softbox[] => {
  const a = t * 0.9                                   // the key light orbits continuously: it must never jump back
  return [
    { dir: [Math.sin(a), 0.55, Math.cos(a)], size: [0.2, 3.6], intensity: 5.5 },
    { dir: [-0.9, 0.35, -1], size: [0.08, 3.2], intensity: 4 },
    { dir: [0, 1, 0.15], size: [2.6, 1.6], intensity: 0.2 },
  ]
}

export const Demo = () => (
  <AbsoluteFill>
    <StageView
      models={[]}
      setup={(stage) => {
        const m = new THREE.Mesh(new THREE.TorusKnotGeometry(40, 12, 256, 48), METALS.alu())
        stage.scene.add(m)
        return { m }
      }}
      direct={(stage, t, _models, built) => {
        const m = built.m as THREE.Mesh
        m.rotation.y = t * 0.5
        m.scale.setScalar(1 + 0.03 * pulse(t))        // a small kick on every beat
        const d = 380 - 120 * easeInOut(seg(t, 0, 6))  // push in
        stage.camera.position.set(0, 60, d); stage.camera.lookAt(0, 0, 0)
        stage.camera.updateProjectionMatrix()
        stage.lightWith(studio(t))
      }}
    />
  </AbsoluteFill>
)
