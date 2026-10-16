import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { continueRender, delayRender, useCurrentFrame } from 'remotion'
import { FPS, H, W } from '../marks'
import { loadModel, type MeshModel } from './mesh'
import { Stage } from './stage'

export type Models = Record<string, MeshModel>
export type Direct = (stage: Stage, t: number, models: Models, built: Built) => void
/** objects a scene builds once and moves every frame */
export type Built = Record<string, any>

/** A full-frame WebGL picture: loads `models`, calls `setup` once and `direct` every frame, renders. */
export function StageView({ models, setup, direct, style }: {
  models: string[]
  setup: (stage: Stage, models: Models) => Built
  direct: Direct
  style?: React.CSSProperties
}) {
  const frame = useCurrentFrame()
  const canvas = useRef<HTMLCanvasElement>(null)
  const stage = useRef<Stage | null>(null)
  const built = useRef<Built | null>(null)
  const [loaded, setLoaded] = useState<Models | null>(null)
  const [handle] = useState(() => delayRender(`models ${models.join(',')}`, { timeoutInMilliseconds: 120000 }))
  useEffect(() => {
    Promise.all(models.map(loadModel)).then((list) => {
      setLoaded(Object.fromEntries(list.map((m) => [m.name, m])))
      continueRender(handle)
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps
  useLayoutEffect(() => {
    if (!loaded || !canvas.current) return
    if (!stage.current) {
      stage.current = new Stage(canvas.current, W, H)
      built.current = setup(stage.current, loaded)
    }
    direct(stage.current, frame / FPS, loaded, built.current!)
    stage.current.grade.uniforms.time.value = frame / FPS
    stage.current.render()
  })
  return <canvas ref={canvas} width={W} height={H} style={{ position: 'absolute', inset: 0, width: W, height: H, ...style }} />
}

/** a model as a group of meshes, centred on its bounding box, one material per part */
export function modelGroup(model: MeshModel, materials: THREE.Material[], edges?: THREE.Material): THREE.Group {
  const g = new THREE.Group()
  const inner = new THREE.Group()
  const c = model.box.getCenter(new THREE.Vector3())
  inner.position.set(-c.x, -c.y, -c.z)
  model.parts.forEach((p, i) => {
    inner.add(new THREE.Mesh(p.geometry, materials[i % materials.length]))
    if (edges) inner.add(new THREE.LineSegments(p.edges, edges))
  })
  g.add(inner)
  return g
}

/** a model in its own (CAD) frame, not centred: for assemblies placed by their joints */
export function rawGroup(model: MeshModel, materials: THREE.Material[]): THREE.Group {
  const g = new THREE.Group()
  model.parts.forEach((p, i) => g.add(new THREE.Mesh(p.geometry, materials[i % materials.length])))
  return g
}
