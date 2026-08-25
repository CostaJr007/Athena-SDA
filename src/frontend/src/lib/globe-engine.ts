// GlobeEngine: imperative three.js scene for the live satellite globe.
//
// Scene frame = ECI (z = north pole). The Earth mesh rotates by GMST, so ECI
// satellite positions from SGP4 line up with the ground directly.
//
// Satellite motion: the worker supplies TWO exact SGP4 samples per interval
// (p0,v0 @ t0, p1,v1 @ t1) and the vertex shader cubic-Hermite-interpolates
// between them — curved orbits stay correct at any time warp. Interpolation
// is clamped to the sample interval, so satellites can never fly off their
// orbits along straight lines when the worker falls behind.

import * as THREE from 'three'
import * as satellite from 'satellite.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { CITIES, latLonToUnit } from '@/lib/cities'

export interface EngineCallbacks {
  getSimTime: () => number // ms epoch (simulated)
  onSelect: (index: number | null) => void
  onHover: (index: number | null, clientX: number, clientY: number) => void
  onContextLost: () => void
  onContextRestored: () => void
  /** reported ~once per second */
  onFps?: (fps: number) => void
  /** Fill `past` (t-P/2..t) and `future` (t..t+P/2) with unit ECI points.
   *  Returns the number of points actually written per buffer (RDP decimation). */
  orbitProvider: (
    index: number,
    simMs: number,
    past: Float32Array,
    future: Float32Array,
  ) => number
  footprintProvider: (
    index: number,
    simMs: number,
  ) => { x: number; y: number; z: number; ang: number } | null
}

interface GroupRuntime {
  points: THREE.Points
  mat: THREE.ShaderMaterial
  offset: number
  count: number
  p0: Float32Array
  v0: Float32Array
  p1: Float32Array
  v1: Float32Array
  sizes: Float32Array
  /** Base RGB (0–1) painted at build time; used when clearing risk tints. */
  baseColor: [number, number, number]
  baseSize: number
}

const SAT_VERT = /* glsl */ `
attribute vec3 aV0;
attribute vec3 aP1;
attribute vec3 aV1;
attribute vec3 aColor;
attribute float aSize;
uniform float uS;    // seconds since t0 (CPU float64 -> float32)
uniform float uDur;  // interval duration in seconds
uniform float uScale;
uniform float uPixelRatio;
varying vec3 vColor;
void main() {
  if (aSize <= 0.001) {
    gl_Position = vec4(99999.0, 99999.0, 99999.0, 1.0);
    gl_PointSize = 0.0;
    vColor = vec3(0.0);
    return;
  }
  float s = clamp(uS / uDur, 0.0, 1.0);
  float s2 = s * s;
  float s3 = s2 * s;
  float h00 = 2.0 * s3 - 3.0 * s2 + 1.0;
  float h10 = s3 - 2.0 * s2 + s;
  float h01 = -2.0 * s3 + 3.0 * s2;
  float h11 = s3 - s2;
  vec3 p = h00 * position + h10 * uDur * aV0 + h01 * aP1 + h11 * uDur * aV1;
  vColor = aColor;
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  gl_Position = projectionMatrix * mv;
  float ps = aSize * uScale * uPixelRatio * (3.8 / -mv.z);
  gl_PointSize = clamp(ps, 1.0, 56.0);
}
`

const SAT_FRAG = /* glsl */ `
varying vec3 vColor;
uniform float uIntensity;
void main() {
  vec2 c = gl_PointCoord - 0.5;
  float d = length(c);
  if (d > 0.5) discard;
  float core = smoothstep(0.35, 0.05, d);
  float halo = smoothstep(0.50, 0.08, d) * 0.85;
  vec3 col = mix(vColor, vec3(1.0), core * 0.65) * (0.85 + uIntensity * 1.25);
  float alpha = clamp(core * 1.0 + halo * 0.75, 0.0, 1.0);
  gl_FragColor = vec4(col, alpha);
}
`

const EARTH_VERT = /* glsl */ `
varying vec2 vUv;
varying vec3 vNormalW;
varying vec3 vPosW;
void main() {
  vUv = uv;
  vec4 wp = modelMatrix * vec4(position, 1.0);
  vPosW = wp.xyz;
  vNormalW = normalize(mat3(modelMatrix) * normal);
  gl_Position = projectionMatrix * viewMatrix * wp;
}
`

const EARTH_FRAG = /* glsl */ `
uniform sampler2D uDay;
uniform sampler2D uNight;
uniform vec3 uSunDir;
varying vec2 vUv;
varying vec3 vNormalW;
varying vec3 vPosW;
void main() {
  vec3 n = normalize(vNormalW);
  float sd = dot(n, uSunDir);
  float dayMix = smoothstep(-0.05, 0.15, sd);
  vec3 dayT = texture2D(uDay, vUv).rgb;
  float luma = dot(dayT, vec3(0.299, 0.587, 0.114));
  dayT = clamp(mix(vec3(luma), dayT, 1.15), 0.0, 1.0); // clean, crisp oceans & continents
  vec3 nightT = texture2D(uNight, vUv).rgb;
  float lit = clamp(sd * 1.35, 0.0, 1.0);
  vec3 col = dayT * lit * 1.25 + dayT * 0.12; // vivid, luminous daytime + soft ambient
  col += nightT * (1.0 - dayMix) * 1.30; // crisp, glowing night city lights
  vec3 v = normalize(cameraPosition - vPosW);
  float rim = pow(1.0 - max(dot(n, v), 0.0), 3.2);
  col += vec3(0.26, 0.48, 0.85) * rim * (0.25 + 0.75 * dayMix) * 0.55;
  gl_FragColor = vec4(col, 1.0);
}
`

const ATMO_VERT = /* glsl */ `
varying vec3 vN;
void main() {
  vN = normalize(normalMatrix * normal);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`

const ATMO_FRAG = /* glsl */ `
varying vec3 vN;
void main() {
  float intensity = pow(max(0.60 - dot(normalize(vN), vec3(0.0, 0.0, 1.0)), 0.0), 4.0);
  gl_FragColor = vec4(0.32, 0.58, 1.12, 1.0) * intensity * 2.2;
}
`

const ORBIT_SIDE = 96
const FOOT_POINTS = 96
const EARTH_R_SCENE = 1.0

function makeRingTexture(): THREE.Texture {
  const c = document.createElement('canvas')
  c.width = c.height = 96
  const ctx = c.getContext('2d')!
  ctx.strokeStyle = '#ffffff'
  ctx.lineWidth = 7
  ctx.beginPath()
  ctx.arc(48, 48, 32, 0, Math.PI * 2)
  ctx.stroke()
  const tex = new THREE.CanvasTexture(c)
  tex.colorSpace = THREE.SRGBColorSpace
  return tex
}

/** Soft pin head for city markers. */
function makeCityPinTexture(): THREE.Texture {
  const c = document.createElement('canvas')
  c.width = c.height = 64
  const ctx = c.getContext('2d')!
  const g = ctx.createRadialGradient(32, 32, 2, 32, 32, 28)
  // Tighter core so scaled sprites stay sharp, not bloated glow
  g.addColorStop(0, 'rgba(236, 253, 245, 0.95)')
  g.addColorStop(0.4, 'rgba(52, 211, 153, 0.7)')
  g.addColorStop(0.75, 'rgba(52, 211, 153, 0.2)')
  g.addColorStop(1, 'rgba(52, 211, 153, 0)')
  ctx.fillStyle = g
  ctx.beginPath()
  ctx.arc(32, 32, 18, 0, Math.PI * 2)
  ctx.fill()
  const tex = new THREE.CanvasTexture(c)
  tex.colorSpace = THREE.SRGBColorSpace
  return tex
}

function makeCityLabelTexture(name: string): THREE.Texture {
  const c = document.createElement('canvas')
  c.width = 256
  c.height = 48
  const ctx = c.getContext('2d')!
  ctx.clearRect(0, 0, c.width, c.height)
  ctx.font = '600 22px "IBM Plex Sans", system-ui, sans-serif'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  // soft shadow for readability on bright oceans
  ctx.fillStyle = 'rgba(0, 0, 0, 0.55)'
  ctx.fillText(name, 10, 26)
  ctx.fillStyle = 'rgba(228, 228, 231, 0.88)'
  ctx.fillText(name, 9, 25)
  const tex = new THREE.CanvasTexture(c)
  tex.colorSpace = THREE.SRGBColorSpace
  return tex
}

interface CityMarker {
  pin: THREE.Sprite
  label: THREE.Sprite
  local: THREE.Vector3
  tier: number
}

export class GlobeEngine {
  private container: HTMLElement
  private cb: EngineCallbacks
  private renderer: THREE.WebGLRenderer
  private scene = new THREE.Scene()
  private camera: THREE.PerspectiveCamera
  private controls: OrbitControls

  private earth: THREE.Mesh
  private earthMat: THREE.ShaderMaterial
  private cityLayer: THREE.Group
  private cityMarkers: CityMarker[] = []
  private cityPinTex: THREE.Texture | null = null
  private groups: GroupRuntime[] = []
  /** hidden replacement set during a dataset swap (old groups keep rendering) */
  private replacement: GroupRuntime[] | null = null
  private desiredVisible: boolean[] = []
  /** Last risk/role tint maps — reapplied on revealReplacement. */
  private pendingColors: Map<number, string> | null = null
  private pendingSizes: Map<number, number> | null = null
  private qualityCap = 1.5
  private appliedW = 0
  private appliedH = 0
  private appliedDpr = 0
  private resizeObserver: ResizeObserver | null = null
  private resizeTimer = 0
  private raf = 0
  private hidden = false
  private contextLost = false
  private t0 = 0 // interval start, s
  private t1 = 1 // interval end, s
  private selected: number | null = null
  private hoverIdx: number | null = null
  private marker: THREE.Sprite
  private orbitPast: THREE.Line
  private orbitFuture: THREE.Line
  private pastGeo: THREE.BufferGeometry
  private futureGeo: THREE.BufferGeometry
  private footLine: THREE.Line
  private footGeo: THREE.BufferGeometry
  /** Dual-route compare: closed orbit rings + cross markers */
  private compareOrbitA: THREE.Line
  private compareOrbitB: THREE.Line
  private compareLink: THREE.Line
  private compareGeoA: THREE.BufferGeometry
  private compareGeoB: THREE.BufferGeometry
  private compareLinkGeo: THREE.BufferGeometry
  private crossMarkers: THREE.Points
  private crossMarkersGeo: THREE.BufferGeometry
  private markerB: THREE.Sprite
  private compareIdxA: number | null = null
  private compareIdxB: number | null = null
  private showOrbit = true
  private showFoot = true
  private follow = false
  /** Desired auto-rotate when the user is not holding the globe. */
  private autoRotateEnabled = true
  /** True while a pointer button is down on the canvas (drag / hold). */
  private pointerHolding = false
  private lastOrbitReal = 0
  private lastOrbitSim = -1e15
  private lastFootReal = 0
  private disposed = false
  private tmpV = new THREE.Vector3()
  private tmpV2 = new THREE.Vector3()
  private tmpM = new THREE.Matrix4()
  private downPos = { x: 0, y: 0 }
  private lastHoverCheck = 0
  private frameTimes: number[] = []
  private dprReduced = false
  private lastFrameT = 0
  private fpsCount = 0
  private fpsWindowStart = 0

  constructor(container: HTMLElement, cb: EngineCallbacks) {
    this.container = container
    this.cb = cb

    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
      powerPreference: 'high-performance',
    })
    // Pure black void — chrome UI sits on starfield panels; globe is the star
    this.renderer.setClearColor(0x000000, 1)
    this.renderer.outputColorSpace = THREE.SRGBColorSpace
    // HMR / remount can leave a previous canvas — two contexts flicker.
    container.querySelectorAll('canvas').forEach((c) => c.remove())
    container.appendChild(this.renderer.domElement)

    const initW = Math.max(1, container.clientWidth)
    const initH = Math.max(1, container.clientHeight)
    this.camera = new THREE.PerspectiveCamera(42, initW / initH, 0.05, 400)
    this.camera.up.set(0, 0, 1)
    // large, dominant Earth; lower edge may bleed off the viewport
    this.camera.position.set(1.0, -2.75, 1.35)
    this.applyViewOffset()

    this.controls = new OrbitControls(this.camera, this.renderer.domElement)
    this.controls.enableDamping = true
    this.controls.dampingFactor = 0.08
    this.controls.minDistance = 1.35
    this.controls.maxDistance = 30
    this.autoRotateEnabled = true
    this.controls.autoRotate = true
    this.controls.autoRotateSpeed = 0.25

    // --- Earth ---
    const loader = new THREE.TextureLoader()
    const dayTex = loader.load(`${import.meta.env.BASE_URL}textures/earth-day.jpg`)
    const nightTex = loader.load(`${import.meta.env.BASE_URL}textures/earth-night.jpg`)
    dayTex.colorSpace = THREE.SRGBColorSpace
    nightTex.colorSpace = THREE.SRGBColorSpace
    dayTex.anisotropy = 4
    nightTex.anisotropy = 4

    const geo = new THREE.SphereGeometry(1, 96, 96)
    geo.rotateX(Math.PI / 2) // poles -> +z, lon0 -> +x
    this.earthMat = new THREE.ShaderMaterial({
      uniforms: {
        uDay: { value: dayTex },
        uNight: { value: nightTex },
        uSunDir: { value: new THREE.Vector3(1, 0, 0) },
      },
      vertexShader: EARTH_VERT,
      fragmentShader: EARTH_FRAG,
    })
    this.earth = new THREE.Mesh(geo, this.earthMat)
    this.scene.add(this.earth)

    // City pins (Earth-fixed — child of earth so they rotate with GMST)
    try {
      this.cityLayer = this.buildCityLayer()
      this.earth.add(this.cityLayer)
    } catch (err) {
      console.warn('City layer disabled:', err)
      this.cityLayer = new THREE.Group()
      this.cityMarkers = []
    }

    // --- narrow atmospheric rim ---
    const atmo = new THREE.Mesh(
      new THREE.SphereGeometry(1.09, 64, 64),
      new THREE.ShaderMaterial({
        vertexShader: ATMO_VERT,
        fragmentShader: ATMO_FRAG,
        blending: THREE.AdditiveBlending,
        side: THREE.BackSide,
        transparent: true,
        depthWrite: false,
      }),
    )
    this.scene.add(atmo)

    this.scene.add(this.makeStars())

    // --- selection marker ---
    this.marker = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: makeRingTexture(),
        color: 0xffffff,
        transparent: true,
        depthWrite: false,
      }),
    )
    this.marker.scale.setScalar(0.05)
    this.marker.visible = false
    this.scene.add(this.marker)

    // --- orbit path: past (red) + future (blue) ---
    this.pastGeo = new THREE.BufferGeometry()
    this.pastGeo.setAttribute(
      'position',
      new THREE.BufferAttribute(new Float32Array(ORBIT_SIDE * 3), 3),
    )
    this.pastGeo.setDrawRange(0, 0)
    this.orbitPast = new THREE.Line(
      this.pastGeo,
      new THREE.LineBasicMaterial({
        color: 0xff6b6b,
        transparent: true,
        opacity: 0.75,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      }),
    )
    this.orbitPast.frustumCulled = false
    this.scene.add(this.orbitPast)

    this.futureGeo = new THREE.BufferGeometry()
    this.futureGeo.setAttribute(
      'position',
      new THREE.BufferAttribute(new Float32Array(ORBIT_SIDE * 3), 3),
    )
    this.futureGeo.setDrawRange(0, 0)
    this.orbitFuture = new THREE.Line(
      this.futureGeo,
      new THREE.LineBasicMaterial({
        color: 0x63b3ff,
        transparent: true,
        opacity: 0.8,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      }),
    )
    this.orbitFuture.frustumCulled = false
    this.scene.add(this.orbitFuture)

    // --- ground footprint circle ---
    this.footGeo = new THREE.BufferGeometry()
    this.footGeo.setAttribute(
      'position',
      new THREE.BufferAttribute(new Float32Array((FOOT_POINTS + 1) * 3), 3),
    )
    this.footGeo.setDrawRange(0, 0)
    this.footLine = new THREE.Line(
      this.footGeo,
      new THREE.LineBasicMaterial({
        color: 0x9fd8ff,
        transparent: true,
        opacity: 0.5,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        depthTest: true, // occluded on the far side
      }),
    )
    this.footLine.frustumCulled = false
    this.scene.add(this.footLine)

    // --- dual-route compare orbits (A cyan, B magenta) ---
    const maxRing = 256
    this.compareGeoA = new THREE.BufferGeometry()
    this.compareGeoA.setAttribute(
      'position',
      new THREE.BufferAttribute(new Float32Array(maxRing * 3), 3),
    )
    this.compareGeoA.setDrawRange(0, 0)
    this.compareOrbitA = new THREE.Line(
      this.compareGeoA,
      new THREE.LineBasicMaterial({
        color: 0x5eead4, // teal A — Athena palette
        transparent: true,
        opacity: 0.9,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      }),
    )
    this.compareOrbitA.frustumCulled = false
    this.compareOrbitA.visible = false
    this.scene.add(this.compareOrbitA)

    this.compareGeoB = new THREE.BufferGeometry()
    this.compareGeoB.setAttribute(
      'position',
      new THREE.BufferAttribute(new Float32Array(maxRing * 3), 3),
    )
    this.compareGeoB.setDrawRange(0, 0)
    this.compareOrbitB = new THREE.Line(
      this.compareGeoB,
      new THREE.LineBasicMaterial({
        color: 0xfb923c, // orange B
        transparent: true,
        opacity: 0.9,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      }),
    )
    this.compareOrbitB.frustumCulled = false
    this.compareOrbitB.visible = false
    this.scene.add(this.compareOrbitB)

    this.compareLinkGeo = new THREE.BufferGeometry()
    this.compareLinkGeo.setAttribute(
      'position',
      new THREE.BufferAttribute(new Float32Array(2 * 3), 3),
    )
    this.compareLinkGeo.setDrawRange(0, 0)
    this.compareLink = new THREE.Line(
      this.compareLinkGeo,
      new THREE.LineBasicMaterial({
        color: 0xfbbf24,
        transparent: true,
        opacity: 0.95,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      }),
    )
    this.compareLink.frustumCulled = false
    this.compareLink.visible = false
    this.scene.add(this.compareLink)

    this.crossMarkersGeo = new THREE.BufferGeometry()
    this.crossMarkersGeo.setAttribute(
      'position',
      new THREE.BufferAttribute(new Float32Array(8 * 3), 3),
    )
    this.crossMarkersGeo.setDrawRange(0, 0)
    this.crossMarkers = new THREE.Points(
      this.crossMarkersGeo,
      new THREE.PointsMaterial({
        color: 0xfbbf24,
        size: 10,
        sizeAttenuation: false,
        transparent: true,
        opacity: 0.95,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      }),
    )
    this.crossMarkers.frustumCulled = false
    this.crossMarkers.visible = false
    this.scene.add(this.crossMarkers)

    this.markerB = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: makeRingTexture(),
        color: 0xf472b6,
        transparent: true,
        depthWrite: false,
      }),
    )
    this.markerB.scale.setScalar(0.05)
    this.markerB.visible = false
    this.scene.add(this.markerB)

    this.applySize()

    // --- events ---
    const el = this.renderer.domElement
    el.addEventListener('pointerdown', this.onPointerDown)
    el.addEventListener('pointerup', this.onPointerUp)
    el.addEventListener('pointercancel', this.onPointerUp)
    el.addEventListener('lostpointercapture', this.onPointerUp)
    el.addEventListener('pointermove', this.onPointerMove)
    el.addEventListener('webglcontextlost', this.onContextLost, false)
    el.addEventListener('webglcontextrestored', this.onContextRestored, false)
    // Debounce: opening docks/panels fires many layout ticks.
    this.resizeObserver = new ResizeObserver(() => {
      window.clearTimeout(this.resizeTimer)
      this.resizeTimer = window.setTimeout(() => this.applySize(), 80)
    })
    this.resizeObserver.observe(container)
    document.addEventListener('visibilitychange', this.onVisibility)

    this.loop()
  }

  private buildCityLayer(): THREE.Group {
    const layer = new THREE.Group()
    layer.name = 'city-layer'
    this.cityPinTex = makeCityPinTexture()
    const pinMatBase = new THREE.SpriteMaterial({
      map: this.cityPinTex,
      transparent: true,
      depthWrite: false,
      depthTest: true,
      blending: THREE.AdditiveBlending,
      opacity: 0.85,
    })

    const PIN_R = 1.004
    const LABEL_R = 1.012

    for (const city of CITIES) {
      const [x, y, z] = latLonToUnit(city.lat, city.lon)
      const local = new THREE.Vector3(x, y, z)

      const pin = new THREE.Sprite(pinMatBase.clone())
      pin.position.copy(local).multiplyScalar(PIN_R)
      // Small discreet dots (tier-1 slightly larger)
      pin.scale.setScalar(city.tier === 1 ? 0.014 : 0.011)
      pin.renderOrder = 2
      layer.add(pin)

      const labelTex = makeCityLabelTexture(city.name)
      const label = new THREE.Sprite(
        new THREE.SpriteMaterial({
          map: labelTex,
          transparent: true,
          depthWrite: false,
          depthTest: true,
          opacity: 0.82,
        }),
      )
      // Offset label slightly "east" in local tangent so it sits next to the pin
      const east = new THREE.Vector3(-local.y, local.x, 0)
      if (east.lengthSq() < 1e-8) east.set(0, 1, 0)
      east.normalize().multiplyScalar(0.018)
      label.position.copy(local).multiplyScalar(LABEL_R).add(east)
      const lw = 0.11 + Math.min(city.name.length, 14) * 0.006
      label.scale.set(lw, lw * 0.22, 1)
      label.renderOrder = 3
      layer.add(label)

      this.cityMarkers.push({
        pin,
        label,
        local: local.clone(),
        tier: city.tier ?? 2,
      })
    }
    return layer
  }

  /** Hide far-side cities; show labels only when camera is reasonably close. */
  private updateCityVisibility() {
    if (!this.cityMarkers.length) return
    try {
      const cam = this.camera.position
      const camLen = cam.length()
      // Earth-fixed camera dir: undo earth spin for front-face test
      this.earth.updateMatrixWorld(true)
      this.tmpM.copy(this.earth.matrixWorld).invert()
      const camLocal = this.tmpV2.copy(cam).applyMatrix4(this.tmpM).normalize()

      const showLabels = camLen < 5.5
      const showPins = camLen < 14

      for (const m of this.cityMarkers) {
        const facing = m.local.dot(camLocal)
        const onFront = facing > 0.08
        m.pin.visible = showPins && onFront
        // Tier-1 labels earlier; secondary only when closer
        const labelOk =
          showLabels && onFront && (m.tier === 1 || camLen < 4.2)
        m.label.visible = labelOk
        if (labelOk) {
          const mat = m.label.material as THREE.SpriteMaterial
          mat.opacity = THREE.MathUtils.clamp((facing - 0.08) / 0.35, 0.15, 0.88)
        }
      }
    } catch {
      /* never break the render loop */
    }
  }

  private makeStars(): THREE.Points {
    const N = 1400
    const pos = new Float32Array(N * 3)
    const col = new Float32Array(N * 3)
    for (let i = 0; i < N; i++) {
      let x = Math.random() * 2 - 1
      let y = Math.random() * 2 - 1
      let z = Math.random() * 2 - 1
      const len = Math.sqrt(x * x + y * y + z * z) || 1
      const r = 60 + Math.random() * 120
      x = (x / len) * r
      y = (y / len) * r
      z = (z / len) * r
      pos.set([x, y, z], i * 3)
      const b = 0.2 + Math.random() * 0.45 // sparse and restrained
      col.set([b, b, Math.min(0.8, b + 0.1)], i * 3)
    }
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    g.setAttribute('color', new THREE.BufferAttribute(col, 3))
    const m = new THREE.PointsMaterial({
      size: 1.0,
      sizeAttenuation: false,
      vertexColors: true,
      transparent: true,
      opacity: 0.45,
      depthWrite: false,
    })
    const p = new THREE.Points(g, m)
    p.frustumCulled = false
    return p
  }

  /** Shift Earth right of center on wide layouts to make room for the panel. */
  private applyViewOffset() {
    const w = Math.max(1, this.container.clientWidth)
    const h = Math.max(1, this.container.clientHeight)
    if (w >= 1024 && w > h) {
      // shift Earth right and slightly down, keeping it clear of the HUD
      this.camera.setViewOffset(
        w,
        h,
        -Math.round(w * 0.09),
        -Math.round(h * 0.05),
        w,
        h,
      )
    } else {
      this.camera.clearViewOffset()
    }
  }

  /**
   * Pixel-budget DPR control: a 4K/high-DPI viewport can otherwise allocate
   * large framebuffers and lose the WebGL context on integrated GPUs.
   */
  private computeDpr(w: number, h: number): number {
    const pixelBudgetDpr = Math.sqrt(5_000_000 / (w * h))
    return Math.max(
      0.5,
      Math.min(window.devicePixelRatio || 1, this.qualityCap, pixelBudgetDpr),
    )
  }

  /** Apply container size + DPR; a no-op when neither actually changed. */
  private applySize = () => {
    const w = Math.max(1, this.container.clientWidth)
    const h = Math.max(1, this.container.clientHeight)
    const dpr = this.computeDpr(w, h)
    if (
      Math.abs(w - this.appliedW) < 2 &&
      Math.abs(h - this.appliedH) < 2 &&
      dpr === this.appliedDpr
    ) {
      return
    }
    this.appliedW = w
    this.appliedH = h
    this.appliedDpr = dpr
    this.camera.aspect = w / h
    this.applyViewOffset()
    this.camera.updateProjectionMatrix()
    this.renderer.setPixelRatio(dpr)
    this.renderer.setSize(w, h)
    for (const g of this.groups) g.mat.uniforms.uPixelRatio.value = dpr
    if (this.replacement) {
      for (const g of this.replacement) g.mat.uniforms.uPixelRatio.value = dpr
    }
  }

  /** Track set currently receiving propagation buffers. */
  private newestGroups(): GroupRuntime[] {
    return this.replacement ?? this.groups
  }

  private disposeGroups(list: GroupRuntime[]) {
    for (const g of list) {
      this.scene.remove(g.points)
      g.points.geometry.dispose()
      g.mat.dispose()
    }
  }

  /**
   * Atomic dataset replacement: the old groups (retiredGroups) stay visible
   * while the replacement is built HIDDEN and its worker warms up. Only when
   * the replacement's first valid interval arrives does `revealReplacement`
   * swap visibility — satellites never disappear during a data upgrade.
   */
  buildSatellites(defs: { color: string; size: number; count: number }[]) {
    // discard a previous never-revealed replacement, keep the visible set
    if (this.replacement) {
      this.disposeGroups(this.replacement)
      this.replacement = null
    }
    const list: GroupRuntime[] = []
    let offset = 0
    for (const def of defs) {
      const n = Math.max(def.count, 1)
      const geo = new THREE.BufferGeometry()
      const p0 = new Float32Array(n * 3)
      const v0 = new Float32Array(n * 3)
      const p1 = new Float32Array(n * 3)
      const v1 = new Float32Array(n * 3)
      const col = new Float32Array(n * 3)
      const siz = new Float32Array(n)
      const c = new THREE.Color(def.color)
      for (let i = 0; i < n; i++) {
        col.set([c.r, c.g, c.b], i * 3)
        siz[i] = def.size
      }
      geo.setAttribute('position', new THREE.BufferAttribute(p0, 3))
      geo.setAttribute('aV0', new THREE.BufferAttribute(v0, 3))
      geo.setAttribute('aP1', new THREE.BufferAttribute(p1, 3))
      geo.setAttribute('aV1', new THREE.BufferAttribute(v1, 3))
      geo.setAttribute('aColor', new THREE.BufferAttribute(col, 3))
      geo.setAttribute('aSize', new THREE.BufferAttribute(siz, 1))
      const mat = new THREE.ShaderMaterial({
        vertexShader: SAT_VERT,
        fragmentShader: SAT_FRAG,
        uniforms: {
          uS: { value: 0 },
          uDur: { value: 1 },
          uScale: { value: 1 },
          uPixelRatio: { value: this.appliedDpr || 1 },
          uIntensity: { value: 2.8 },
        },
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        depthTest: true, // Earth hides far-side satellites
      })
      const points = new THREE.Points(geo, mat)
      points.frustumCulled = false
      points.visible = false // hidden until first valid interval arrives
      this.scene.add(points)
      list.push({
        points,
        mat,
        offset,
        count: def.count,
        p0,
        v0,
        p1,
        v1,
        sizes: siz,
        baseColor: [c.r, c.g, c.b],
        baseSize: def.size,
      })
      offset += def.count
    }
    this.replacement = list
  }

  /**
   * Tint individual satellites by global catalog index (post build/reveal).
   * `colors` maps index → CSS hex; missing keys keep the layer base color.
   * Optional `sizes` boosts pixel size for priority tracks.
   */
  applyIndexColors(
    colors: Map<number, string> | null,
    sizes?: Map<number, number> | null,
  ) {
    this.pendingColors = colors
    this.pendingSizes = sizes ?? null
    this.paintIndexColors(this.groups.length ? this.groups : this.replacement)
  }

  private paintIndexColors(groups: GroupRuntime[] | null) {
    if (!groups) return
    const colors = this.pendingColors
    const sizes = this.pendingSizes
    for (const g of groups) {
      const colAttr = g.points.geometry.getAttribute('aColor') as THREE.BufferAttribute
      const sizeAttr = g.points.geometry.getAttribute('aSize') as THREE.BufferAttribute
      const colArr = colAttr.array as Float32Array
      const sizeArr = sizeAttr.array as Float32Array
      const n = g.count
      for (let i = 0; i < n; i++) {
        const globalIdx = g.offset + i
        const hex = colors?.get(globalIdx)
        if (hex) {
          const c = new THREE.Color(hex)
          colArr[i * 3] = c.r
          colArr[i * 3 + 1] = c.g
          colArr[i * 3 + 2] = c.b
        } else {
          colArr[i * 3] = g.baseColor[0]
          colArr[i * 3 + 1] = g.baseColor[1]
          colArr[i * 3 + 2] = g.baseColor[2]
        }
        const sz = sizes?.get(globalIdx)
        sizeArr[i] = sz ?? g.baseSize
      }
      colAttr.needsUpdate = true
      sizeAttr.needsUpdate = true
    }
  }

  /** Swap the hidden replacement in and dispose of the retired groups. */
  revealReplacement() {
    if (!this.replacement) return
    const retired = this.groups
    this.groups = this.replacement
    this.replacement = null
    // restore each group's enabled/disabled state
    for (let i = 0; i < this.groups.length; i++) {
      this.groups[i].points.visible = this.desiredVisible[i] !== false
    }
    this.disposeGroups(retired)
    // Re-tint watchlist after swap (risk colors applied while replacement was hidden)
    this.paintIndexColors(this.groups)
  }

  setGroupVisible(i: number, v: boolean) {
    this.desiredVisible[i] = v
    if (this.groups[i] && !this.replacement) this.groups[i].points.visible = v
  }

  /** Receive a new two-sample SGP4 interval (flat arrays across all groups). */
  updateInterval(
    t0Ms: number,
    t1Ms: number,
    p0: Float32Array,
    v0: Float32Array,
    p1: Float32Array,
    v1: Float32Array,
  ) {
    for (const g of this.newestGroups()) {
      const o = g.offset * 3
      const n = g.count * 3
      g.p0.set(p0.subarray(o, o + n))
      g.v0.set(v0.subarray(o, o + n))
      g.p1.set(p1.subarray(o, o + n))
      g.v1.set(v1.subarray(o, o + n))
      const at = g.points.geometry.attributes
      ;(at.position as THREE.BufferAttribute).needsUpdate = true
      ;(at.aV0 as THREE.BufferAttribute).needsUpdate = true
      ;(at.aP1 as THREE.BufferAttribute).needsUpdate = true
      ;(at.aV1 as THREE.BufferAttribute).needsUpdate = true
      g.mat.uniforms.uDur.value = Math.max((t1Ms - t0Ms) / 1000, 0.001)
    }
    this.t0 = t0Ms / 1000
    this.t1 = t1Ms / 1000
  }

  setShowOrbit(v: boolean) {
    this.showOrbit = v
    this.orbitPast.visible = v && this.selected !== null
    this.orbitFuture.visible = v && this.selected !== null
    this.lastOrbitSim = -1e15
  }

  setShowFootprint(v: boolean) {
    this.showFoot = v
    this.footLine.visible = v && this.selected !== null
  }

  setFollow(v: boolean) {
    this.follow = v
  }

  setSelected(index: number | null, color?: string) {
    this.selected = index
    this.marker.visible = index !== null
    if (color) this.marker.material.color.set(color)
    // Hide single-orbit path while dual-compare rings are active
    const dual =
      this.compareOrbitA.visible || this.compareOrbitB.visible
    this.orbitPast.visible = index !== null && this.showOrbit && !dual
    this.orbitFuture.visible = index !== null && this.showOrbit && !dual
    this.footLine.visible = index !== null && this.showFoot && !dual
    this.lastOrbitSim = -1e15
    if (index === null) {
      this.pastGeo.setDrawRange(0, 0)
      this.futureGeo.setDrawRange(0, 0)
      this.footGeo.setDrawRange(0, 0)
      if (!this.compareIdxA && !this.compareIdxB) {
        this.controls.target.set(0, 0, 0)
      }
    }
  }

  /**
   * Dual-route compare visualization.
   * @param ringA closed orbit in scene units (xyz interleaved)
   * @param ringB closed orbit in scene units
   * @param markers optional cross / closest points (xyz interleaved)
   * @param link optional 2-point segment (6 floats) between closest pair
   * @param liveIdxA optional satellite index for live marker A
   * @param liveIdxB optional satellite index for live marker B
   */
  setCompareRoutes(
    ringA: Float32Array | null,
    ringB: Float32Array | null,
    markers: Float32Array | null = null,
    link: Float32Array | null = null,
    liveIdxA: number | null = null,
    liveIdxB: number | null = null,
  ) {
    this.compareIdxA = liveIdxA
    this.compareIdxB = liveIdxB

    const writeRing = (
      geo: THREE.BufferGeometry,
      line: THREE.Line,
      data: Float32Array | null,
    ) => {
      if (!data || data.length < 6) {
        geo.setDrawRange(0, 0)
        line.visible = false
        return
      }
      const attr = geo.getAttribute('position') as THREE.BufferAttribute
      const cap = attr.array.length
      const n = Math.min(data.length, cap)
      ;(attr.array as Float32Array).set(data.subarray(0, n))
      attr.needsUpdate = true
      geo.setDrawRange(0, Math.floor(n / 3))
      line.visible = true
    }

    writeRing(this.compareGeoA, this.compareOrbitA, ringA)
    writeRing(this.compareGeoB, this.compareOrbitB, ringB)

    if (link && link.length >= 6) {
      const attr = this.compareLinkGeo.getAttribute(
        'position',
      ) as THREE.BufferAttribute
      ;(attr.array as Float32Array).set(link.subarray(0, 6))
      attr.needsUpdate = true
      this.compareLinkGeo.setDrawRange(0, 2)
      this.compareLink.visible = true
    } else {
      this.compareLinkGeo.setDrawRange(0, 0)
      this.compareLink.visible = false
    }

    if (markers && markers.length >= 3) {
      const attr = this.crossMarkersGeo.getAttribute(
        'position',
      ) as THREE.BufferAttribute
      const n = Math.min(markers.length, attr.array.length)
      ;(attr.array as Float32Array).set(markers.subarray(0, n))
      attr.needsUpdate = true
      this.crossMarkersGeo.setDrawRange(0, Math.floor(n / 3))
      this.crossMarkers.visible = true
    } else {
      this.crossMarkersGeo.setDrawRange(0, 0)
      this.crossMarkers.visible = false
    }

    // Switch to dual markers when comparing
    const dual = !!(ringA || ringB)
    if (dual) {
      this.orbitPast.visible = false
      this.orbitFuture.visible = false
      this.footLine.visible = false
      ;(this.marker.material as THREE.SpriteMaterial).color.set(0x5eead4)
      ;(this.markerB.material as THREE.SpriteMaterial).color.set(0xfb923c)
    }
    this.marker.visible = liveIdxA !== null
    this.markerB.visible = liveIdxB !== null
  }

  clearCompareRoutes() {
    this.setCompareRoutes(null, null, null, null, null, null)
    this.markerB.visible = false
    // restore single-selection orbit visibility
    this.orbitPast.visible = this.selected !== null && this.showOrbit
    this.orbitFuture.visible = this.selected !== null && this.showOrbit
    this.footLine.visible = this.selected !== null && this.showFoot
  }

  /** Zero the size of satellites that failed to propagate (dead/decayed). */
  markDead(globalIndices: number[]) {
    for (const g of this.groups) {
      const attr = g.points.geometry.getAttribute('aSize') as THREE.BufferAttribute
      let dirty = false
      for (const idx of globalIndices) {
        if (idx >= g.offset && idx < g.offset + g.count) {
          attr.setX(idx - g.offset, 0)
          g.sizes[idx - g.offset] = 0
          dirty = true
        }
      }
      if (dirty) attr.needsUpdate = true
    }
  }

  /** Current interpolated ECI position of a satellite (unit space). */
  eciPosition(index: number, out: THREE.Vector3): THREE.Vector3 | null {
    const simS = this.cb.getSimTime() / 1000
    const dur = Math.max(this.t1 - this.t0, 0.001)
    const s = Math.min(Math.max((simS - this.t0) / dur, 0), 1)
    const s2 = s * s
    const s3 = s2 * s
    const h00 = 2 * s3 - 3 * s2 + 1
    const h10 = s3 - 2 * s2 + s
    const h01 = -2 * s3 + 3 * s2
    const h11 = s3 - s2
    for (const g of this.groups) {
      if (index >= g.offset && index < g.offset + g.count) {
        const i = (index - g.offset) * 3
        out.set(
          h00 * g.p0[i] + h10 * dur * g.v0[i] + h01 * g.p1[i] + h11 * dur * g.v1[i],
          h00 * g.p0[i + 1] + h10 * dur * g.v0[i + 1] + h01 * g.p1[i + 1] + h11 * dur * g.v1[i + 1],
          h00 * g.p0[i + 2] + h10 * dur * g.v0[i + 2] + h01 * g.p1[i + 2] + h11 * dur * g.v1[i + 2],
        )
        return out
      }
    }
    return null
  }

  /** Segment camera->satellite versus Earth sphere. */
  private isOccluded(p: THREE.Vector3): boolean {
    const c = this.camera.position
    // visible hemisphere test
    if (p.dot(this.tmpV2.copy(c).normalize()) < -0.05) {
      // still might be visible near the limb; fall through to precise test
    }
    const dx = p.x - c.x
    const dy = p.y - c.y
    const dz = p.z - c.z
    const len = Math.sqrt(dx * dx + dy * dy + dz * dz)
    if (len < 1e-6) return false
    const b = (c.x * dx + c.y * dy + c.z * dz) / len // C . dir
    const cc = c.x * c.x + c.y * c.y + c.z * c.z - EARTH_R_SCENE * EARTH_R_SCENE
    const disc = b * b - cc
    if (disc <= 0) return false
    const t = -b - Math.sqrt(disc)
    return t > 0 && t < len - 1e-3
  }

  /** Nearest selectable satellite to a screen point (client coords). */
  private pick(clientX: number, clientY: number, thresholdPx: number): number | null {
    // during a dataset swap the visible groups use the old index space —
    // skip picking for that brief window rather than select the wrong object
    if (this.replacement) return null
    const rect = this.renderer.domElement.getBoundingClientRect()
    const x = clientX - rect.left
    const y = clientY - rect.top
    const v = this.tmpV
    let best: number | null = null
    let bestD = thresholdPx
    for (const g of this.groups) {
      if (!g.points.visible) continue
      for (let i = 0; i < g.count; i++) {
        if (g.sizes[i] === 0) continue // dead/decayed
        const idx = this.eciPosition(g.offset + i, v)
        if (!idx) continue
        if (v.lengthSq() < 1) continue // inside Earth
        v.project(this.camera)
        if (v.z > 1) continue
        const sx = (v.x * 0.5 + 0.5) * rect.width
        const sy = (-v.y * 0.5 + 0.5) * rect.height
        if (sx < -20 || sx > rect.width + 20 || sy < -20 || sy > rect.height + 20) continue
        const d = Math.hypot(sx - x, sy - y)
        if (d < bestD) {
          // precise occlusion check only for the current best candidate
          this.eciPosition(g.offset + i, v)
          if (this.isOccluded(v)) continue
          bestD = d
          best = g.offset + i
        }
      }
    }
    return best
  }

  private syncAutoRotate() {
    // Pause camera orbit while holding / dragging; resume previous state on release.
    this.controls.autoRotate = this.autoRotateEnabled && !this.pointerHolding
  }

  private onPointerDown = (e: PointerEvent) => {
    if (e.button !== 0 && e.pointerType === 'mouse') return
    this.downPos = { x: e.clientX, y: e.clientY }
    this.pointerHolding = true
    this.syncAutoRotate()
    try {
      this.renderer.domElement.setPointerCapture(e.pointerId)
    } catch {
      /* ignore — capture optional */
    }
  }

  private onPointerUp = (e: PointerEvent) => {
    this.pointerHolding = false
    this.syncAutoRotate()

    // Selection only on a real pointerup click (not cancel / lost capture)
    if (e.type !== 'pointerup') return

    try {
      if (this.renderer.domElement.hasPointerCapture?.(e.pointerId)) {
        this.renderer.domElement.releasePointerCapture(e.pointerId)
      }
    } catch {
      /* ignore */
    }

    const moved = Math.hypot(e.clientX - this.downPos.x, e.clientY - this.downPos.y)
    if (moved > 5) return // globe drag — never a selection
    const idx = this.pick(e.clientX, e.clientY, 12)
    this.cb.onSelect(idx)
  }

  private onPointerMove = (e: PointerEvent) => {
    const now = performance.now()
    if (now - this.lastHoverCheck < 120) return
    this.lastHoverCheck = now
    const idx = this.pick(e.clientX, e.clientY, 8)
    if (idx !== this.hoverIdx) {
      this.hoverIdx = idx
      this.renderer.domElement.style.cursor = idx !== null ? 'pointer' : 'grab'
    }
    this.cb.onHover(idx, e.clientX, e.clientY)
  }

  private onContextLost = (e: Event) => {
    e.preventDefault()
    this.contextLost = true
    cancelAnimationFrame(this.raf)
    this.cb.onContextLost()
  }

  private onContextRestored = () => {
    this.contextLost = false
    this.cb.onContextRestored()
    this.loop()
  }

  private onVisibility = () => {
    this.hidden = document.hidden
    if (!this.hidden && !this.contextLost && !this.disposed) {
      cancelAnimationFrame(this.raf)
      this.loop()
    }
  }

  private updateSun(simMs: number) {
    const jd = satellite.jday(new Date(simMs))
    const sun = satellite.sunPos(jd).rsun
    const len = Math.sqrt(sun.x * sun.x + sun.y * sun.y + sun.z * sun.z) || 1
    ;(this.earthMat.uniforms.uSunDir.value as THREE.Vector3).set(
      sun.x / len,
      sun.y / len,
      sun.z / len,
    )
  }

  /** FPS meter + quality cap reduction if the device cannot keep up. */
  private monitorPerf(now: number) {
    // fps meter, reported ~once per second
    this.fpsCount++
    if (this.fpsWindowStart === 0) this.fpsWindowStart = now
    const windowMs = now - this.fpsWindowStart
    if (windowMs >= 1000) {
      this.cb.onFps?.(Math.round((this.fpsCount * 1000) / windowMs))
      this.fpsCount = 0
      this.fpsWindowStart = now
    }
    if (this.dprReduced) return
    if (this.lastFrameT) this.frameTimes.push(now - this.lastFrameT)
    if (this.frameTimes.length >= 120) {
      const avg = this.frameTimes.reduce((a, b) => a + b, 0) / this.frameTimes.length
      this.frameTimes.length = 0
      if (avg > 40 && this.qualityCap > 1) {
        this.dprReduced = true
        this.qualityCap = 1
        this.applySize()
      }
    }
    this.lastFrameT = now
  }

  private loop = () => {
    if (this.disposed || this.contextLost) return
    if (this.hidden) return // paused while the tab is hidden
    this.raf = requestAnimationFrame(this.loop)
    const simMs = this.cb.getSimTime()
    const simS = simMs / 1000
    const nowMs = performance.now()

    this.earth.rotation.z = satellite.gstime(new Date(simMs))
    this.updateSun(simMs)
    this.updateCityVisibility()

    const uS = Math.min(Math.max(simS - this.t0, 0), Math.max(this.t1 - this.t0, 0.001))
    for (const g of this.groups) g.mat.uniforms.uS.value = uS

    // Live markers for dual-compare (or single selection)
    const pulse = 0.045 + 0.01 * Math.sin(nowMs * 0.005)
    if (this.compareIdxA !== null) {
      const pA = this.eciPosition(this.compareIdxA, this.tmpV)
      if (pA) {
        this.marker.position.copy(pA)
        this.marker.scale.setScalar(pulse)
        this.marker.visible = true
      }
    }
    if (this.compareIdxB !== null) {
      const pB = this.eciPosition(this.compareIdxB, this.tmpV2)
      if (pB) {
        this.markerB.position.copy(pB)
        this.markerB.scale.setScalar(pulse * 1.05)
        this.markerB.visible = true
        if (this.follow) this.controls.target.lerp(pB, 0.15)
      }
    }

    if (this.selected !== null && this.compareIdxA === null) {
      const p = this.eciPosition(this.selected, this.tmpV)
      if (p) {
        this.marker.position.copy(p)
        this.marker.scale.setScalar(pulse)
        if (this.follow) this.controls.target.lerp(p, 0.25)
      }
      const nowReal = performance.now()
      if (
        this.showOrbit &&
        !this.compareOrbitA.visible &&
        nowReal - this.lastOrbitReal > 400 &&
        Math.abs(simMs - this.lastOrbitSim) > 6000
      ) {
        const pa = this.pastGeo.getAttribute('position') as THREE.BufferAttribute
        const fu = this.futureGeo.getAttribute('position') as THREE.BufferAttribute
        const used = this.cb.orbitProvider(
          this.selected,
          simMs,
          pa.array as Float32Array,
          fu.array as Float32Array,
        )
        const draw = used ?? ORBIT_SIDE
        this.pastGeo.setDrawRange(0, draw)
        this.futureGeo.setDrawRange(0, draw)
        pa.needsUpdate = true
        fu.needsUpdate = true
        this.lastOrbitReal = nowReal
        this.lastOrbitSim = simMs
      }
      if (this.showFoot && nowReal - this.lastFootReal > 250) {
        this.lastFootReal = nowReal
        const f = this.cb.footprintProvider(this.selected, simMs)
        if (f) {
          const attr = this.footGeo.getAttribute('position') as THREE.BufferAttribute
          const arr = attr.array as Float32Array
          const c = new THREE.Vector3(f.x, f.y, f.z).normalize()
          const up = Math.abs(c.z) > 0.9 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 0, 1)
          const t1v = new THREE.Vector3().crossVectors(c, up).normalize()
          const t2v = new THREE.Vector3().crossVectors(c, t1v).normalize()
          const R = 1.0028
          const cosA = Math.cos(f.ang)
          const sinA = Math.sin(f.ang)
          for (let i = 0; i <= FOOT_POINTS; i++) {
            const a = (i / FOOT_POINTS) * Math.PI * 2
            const dx = Math.cos(a) * sinA
            const dy = Math.sin(a) * sinA
            arr.set(
              [
                (c.x * cosA + t1v.x * dx + t2v.x * dy) * R,
                (c.y * cosA + t1v.y * dx + t2v.y * dy) * R,
                (c.z * cosA + t1v.z * dx + t2v.z * dy) * R,
              ],
              i * 3,
            )
          }
          this.footGeo.setDrawRange(0, FOOT_POINTS + 1)
          attr.needsUpdate = true
        } else {
          this.footGeo.setDrawRange(0, 0)
        }
      }
    }

    this.controls.update()
    this.renderer.render(this.scene, this.camera)
    this.monitorPerf(performance.now())
  }

  dispose() {
    this.disposed = true
    cancelAnimationFrame(this.raf)
    const el = this.renderer.domElement
    el.removeEventListener('pointerdown', this.onPointerDown)
    el.removeEventListener('pointerup', this.onPointerUp)
    el.removeEventListener('pointercancel', this.onPointerUp)
    el.removeEventListener('lostpointercapture', this.onPointerUp)
    el.removeEventListener('pointermove', this.onPointerMove)
    el.removeEventListener('webglcontextlost', this.onContextLost)
    el.removeEventListener('webglcontextrestored', this.onContextRestored)
    this.resizeObserver?.disconnect()
    window.clearTimeout(this.resizeTimer)
    document.removeEventListener('visibilitychange', this.onVisibility)
    this.controls.dispose()
    this.disposeGroups(this.groups)
    if (this.replacement) this.disposeGroups(this.replacement)
    this.groups = []
    this.replacement = null
    this.scene.traverse((obj) => {
      if (obj instanceof THREE.Mesh || obj instanceof THREE.Points || obj instanceof THREE.Line || obj instanceof THREE.Sprite) {
        obj.geometry?.dispose()
        const mat = obj.material as THREE.Material | THREE.Material[] | undefined
        if (Array.isArray(mat)) mat.forEach((m) => m.dispose())
        else if (mat) {
          const withMap = mat as THREE.Material & { map?: THREE.Texture }
          withMap.map?.dispose()
          mat.dispose()
        }
      }
    })
    this.renderer.dispose()
    el.remove()
  }
}
