// One WebGL stage per canvas: a black studio whose only light is moving softboxes (they light the metal
// through its reflections, the way product films are lit), plus DOF, bloom and a final grade pass that can
// also turn the picture into 1-bit ordered dither (the brand's look, used once at the end).
import * as THREE from 'three'
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js'
import { BokehPass } from 'three/examples/jsm/postprocessing/BokehPass.js'
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js'
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js'
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js'

export interface Softbox { /** direction it lights from (world, normalised inside) */ dir: [number, number, number]; /** width, height in radians-ish */ size: [number, number]; intensity: number; /** roll of the strip about its own axis */ roll?: number }

const GRADE = {
  uniforms: {
    tDiffuse: { value: null }, time: { value: 0 }, vignette: { value: 0.35 }, grain: { value: 0.035 },
    dither: { value: 0 }, ditherScale: { value: 2 }, ink: { value: new THREE.Color(0xf4ecd6) }, gain: { value: 1 }, resolution: { value: new THREE.Vector2(1920, 1080) },
  },
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  fragmentShader: `
    uniform sampler2D tDiffuse; uniform float time, vignette, grain, dither, ditherScale, gain; uniform vec3 ink; uniform vec2 resolution;
    varying vec2 vUv;
    float bayer(vec2 p){ // 8x8 ordered dither
      int x = int(mod(p.x, 8.0)), y = int(mod(p.y, 8.0));
      int m[64] = int[64](0,32,8,40,2,34,10,42,48,16,56,24,50,18,58,26,12,44,4,36,14,46,6,38,60,28,52,20,62,30,54,22,3,35,11,43,1,33,9,41,51,19,59,27,49,17,57,25,15,47,7,39,13,45,5,37,63,31,55,23,61,29,53,21);
      return (float(m[y * 8 + x]) + 0.5) / 64.0;
    }
    float hash(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233)) + time * 13.7) * 43758.5453); }
    void main(){
      vec2 cell = floor(vUv * resolution / ditherScale);
      vec2 uv = dither > 0.0 ? mix(vUv, (cell + 0.5) * ditherScale / resolution, step(0.001, dither)) : vUv;
      vec3 c = texture2D(tDiffuse, uv).rgb * gain;
      vec2 d = vUv - 0.5;
      c *= 1.0 - vignette * dot(d, d) * 2.2;
      c += (hash(vUv * resolution) - 0.5) * grain;
      if (dither > 0.0) {
        float lum = dot(c, vec3(0.299, 0.587, 0.114));
        float on = step(bayer(cell), lum * 1.15);
        c = mix(c, ink * on, dither);
      }
      gl_FragColor = vec4(c, 1.0);
    }`,
}

export class Stage {
  renderer: THREE.WebGLRenderer
  scene = new THREE.Scene()
  camera: THREE.PerspectiveCamera
  composer: EffectComposer
  bokeh: BokehPass & { uniforms: Record<string, { value: any }> }
  bloom: UnrealBloomPass
  grade: ShaderPass
  private env = new THREE.Scene()
  private pmrem: THREE.PMREMGenerator
  private envTarget: THREE.WebGLRenderTarget | null = null
  private boxes: THREE.Mesh[] = []

  constructor(canvas: HTMLCanvasElement, w: number, h: number) {
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true, alpha: false })
    this.renderer.setPixelRatio(1)
    this.renderer.setSize(w, h, false)
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping
    this.renderer.toneMappingExposure = 1.0
    this.camera = new THREE.PerspectiveCamera(28, w / h, 1, 5000)
    this.scene.background = new THREE.Color(0x000000)
    this.pmrem = new THREE.PMREMGenerator(this.renderer)
    this.env.background = new THREE.Color(0x000000)
    const rt = new THREE.WebGLRenderTarget(w, h, { type: THREE.HalfFloatType, samples: 4 })
    this.composer = new EffectComposer(this.renderer, rt)
    this.composer.setPixelRatio(1)
    this.composer.setSize(w, h)
    this.composer.addPass(new RenderPass(this.scene, this.camera))
    this.bokeh = new BokehPass(this.scene, this.camera, { focus: 300, aperture: 0.0, maxblur: 0.008 }) as Stage['bokeh']
    this.composer.addPass(this.bokeh)
    this.bloom = new UnrealBloomPass(new THREE.Vector2(w, h), 0.16, 0.35, 0.92)
    this.composer.addPass(this.bloom)
    this.composer.addPass(new OutputPass())
    this.grade = new ShaderPass(GRADE)
    this.grade.uniforms.resolution.value.set(w, h)
    this.composer.addPass(this.grade)
  }

  /** the studio's light: softboxes on a sphere round the subject, seen only in the reflections */
  lightWith(boxes: Softbox[], fill = 0.0) {
    for (const b of this.boxes) { this.env.remove(b); b.geometry.dispose(); (b.material as THREE.Material).dispose() }
    this.boxes = boxes.map((b) => {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(b.size[0] * 50, b.size[1] * 50), new THREE.MeshBasicMaterial({ color: new THREE.Color(1, 1, 1).multiplyScalar(b.intensity), side: THREE.DoubleSide }))
      const d = new THREE.Vector3(...b.dir).normalize()
      m.position.copy(d.multiplyScalar(50))
      m.lookAt(0, 0, 0)
      if (b.roll) m.rotateZ(b.roll)
      this.env.add(m)
      return m
    })
    this.env.background = new THREE.Color(fill, fill, fill)
    this.envTarget?.dispose()
    this.envTarget = this.pmrem.fromScene(this.env, 0, 0.1, 200)
    this.scene.environment = this.envTarget.texture
  }

  render() { this.composer.render() }
}

/** bead-blasted / machined metal: the roughness wanders a little over the surface (world-space value noise),
 *  so reflections break up the way they do on real parts instead of sliding like on chrome */
function grain(m: THREE.MeshPhysicalMaterial, amount: number, scale: number): THREE.MeshPhysicalMaterial {
  m.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vGrainPos;')
      .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nvGrainPos = (modelMatrix * vec4(transformed, 1.0)).xyz;')
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', `#include <common>
varying vec3 vGrainPos;
float gh(vec3 p){ return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
float gn(vec3 p){ vec3 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(gh(i), gh(i + vec3(1,0,0)), f.x), mix(gh(i + vec3(0,1,0)), gh(i + vec3(1,1,0)), f.x), f.y),
             mix(mix(gh(i + vec3(0,0,1)), gh(i + vec3(1,0,1)), f.x), mix(gh(i + vec3(0,1,1)), gh(i + vec3(1,1,1)), f.x), f.y), f.z); }`)
      .replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>
roughnessFactor = clamp(roughnessFactor + ${amount.toFixed(3)} * (gn(vGrainPos * ${scale.toFixed(3)}) + 0.5 * gn(vGrainPos * ${(scale * 7.3).toFixed(3)}) - 0.75), 0.04, 1.0);`)
  }
  return m
}

export const METALS = {
  alu: () => grain(new THREE.MeshPhysicalMaterial({ color: 0xcfd3d9, metalness: 1, roughness: 0.34, clearcoat: 0.25, clearcoatRoughness: 0.18 }), 0.12, 0.35),
  steel: () => grain(new THREE.MeshPhysicalMaterial({ color: 0xbfc4ca, metalness: 1, roughness: 0.22 }), 0.08, 0.6),
  dark: () => grain(new THREE.MeshPhysicalMaterial({ color: 0x2b2e34, metalness: 0.7, roughness: 0.44, clearcoat: 0.5, clearcoatRoughness: 0.25 }), 0.1, 0.5),
  rubber: () => new THREE.MeshPhysicalMaterial({ color: 0x141518, metalness: 0, roughness: 0.75 }),
  brass: () => grain(new THREE.MeshPhysicalMaterial({ color: 0xd8b27a, metalness: 1, roughness: 0.3 }), 0.1, 0.4),
}
