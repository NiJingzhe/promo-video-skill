// Loads the meshes promo/tools/mesh.py wrote (B-rep tessellated by OCC): per part, positions, normals,
// indices and the B-rep edges as line segments.
import * as THREE from 'three'
import { staticFile } from 'remotion'

export interface MeshPart { name: string; geometry: THREE.BufferGeometry; edges: THREE.BufferGeometry }
export interface MeshModel { name: string; parts: MeshPart[]; box: THREE.Box3 }

const cache = new Map<string, Promise<MeshModel>>()

export function loadModel(name: string): Promise<MeshModel> {
  if (!cache.has(name)) cache.set(name, fetchModel(name))
  return cache.get(name)!
}

async function fetchModel(name: string): Promise<MeshModel> {
  const meta = await (await fetch(staticFile(`mesh/${name}.json`))).json() as { parts: { name: string; vertices: number; triangles: number; edges: number }[]; bbox: [number[], number[]] }
  const buf = await (await fetch(staticFile(`mesh/${name}.bin`))).arrayBuffer()
  let off = 0
  const take = <T extends Float32Array | Uint32Array>(Ctor: new (b: ArrayBuffer, o: number, n: number) => T, n: number) => { const a = new Ctor(buf, off, n); off += n * 4; return a }
  const parts = meta.parts.map((p) => {
    const pos = take(Float32Array, p.vertices * 3)
    const nor = take(Float32Array, p.vertices * 3)
    const idx = take(Uint32Array, p.triangles * 3)
    const seg = take(Float32Array, p.edges * 6)
    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    geometry.setAttribute('normal', new THREE.BufferAttribute(nor, 3))
    geometry.setIndex(new THREE.BufferAttribute(idx, 1))
    const edges = new THREE.BufferGeometry()
    edges.setAttribute('position', new THREE.BufferAttribute(seg, 3))
    return { name: p.name, geometry, edges }
  })
  const box = new THREE.Box3(new THREE.Vector3(...meta.bbox[0]), new THREE.Vector3(...meta.bbox[1]))
  return { name, parts, box }
}
