/* The brush as a real object. A three.js scene sits on a canvas over the home page hero, with the
   page itself as the floor: the brush flies in from in front of the page, lands on the line under
   her name, paints it in step with the stroke, lifts away, then comes to rest beside the line and
   turns to follow the pointer. Its shadow falls on the page through a shadow-only plane.
   If WebGL is missing, or motion is reduced, the flat brush in site.js runs instead. */
import * as THREE from '/assets/vendor/three.module.min.js';

const CCT = window.CCT || (window.CCT = {});
const canvas = document.getElementById('brush-gl');
const ink = document.getElementById('stencil-path');
const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const fine = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

function fallback() { if (CCT.startFlatBrush) { CCT.startFlatBrush(); } }

if (!canvas || !ink || reduce) {
  fallback();
} else {
  try { run(); } catch (e) { if (canvas) { canvas.style.display = 'none'; } fallback(); }
}

function run() {
  const hero = canvas.parentElement;
  const lineSvg = ink.ownerSVGElement;
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.25));
  renderer.setClearColor(0x000000, 0);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  const FOV = 40;
  const camera = new THREE.PerspectiveCamera(FOV, 1, 1, 6000);
  let W = 1, H = 1, D = 1000, k = 1;

  // The page as a floor: catches the shadow, shows nothing else
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.ShadowMaterial({ opacity: 0.55 }));
  floor.receiveShadow = true;
  floor.position.z = -3;
  scene.add(floor);

  // Lights: a warm key from the top left, a violet lamp that follows the pointer, a little fill
  scene.add(new THREE.AmbientLight(0xffffff, 0.7));
  const key = new THREE.DirectionalLight(0xfff1dc, 2.8);
  key.position.set(-500, 700, 900);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  key.shadow.radius = 4;
  key.shadow.bias = -0.0005;
  scene.add(key);
  scene.add(key.target);
  const lamp = new THREE.PointLight(0x9a7fd1, 1.4, 2200, 1.2);
  lamp.position.set(300, 200, 500);
  scene.add(lamp);
  const rim = new THREE.DirectionalLight(0x9a7fd1, 0.8);
  rim.position.set(600, -200, 300);
  scene.add(rim);

  // The brush, tip at its origin, handle up the +Y axis, 300 units long
  const brush = new THREE.Group();
  const mats = [];
  const wood = new THREE.MeshStandardMaterial({ map: woodTexture(), roughness: 0.42, metalness: 0.05 });
  const steel = new THREE.MeshStandardMaterial({ color: 0xd8d8d8, roughness: 0.22, metalness: 0.95 });
  const dark = new THREE.MeshStandardMaterial({ color: 0x3a3a3a, roughness: 0.4, metalness: 0.8 });
  const hair = new THREE.MeshStandardMaterial({ color: 0xe6dcc6, roughness: 0.92, metalness: 0 });
  const inkMat = new THREE.MeshStandardMaterial({ color: 0x9a7fd1, roughness: 0.35, metalness: 0.05 });
  const capMat = new THREE.MeshStandardMaterial({ color: 0x2f1b0b, roughness: 0.5 });
  [wood, steel, dark, hair, inkMat, capMat].forEach(m => { m.transparent = true; mats.push(m); });
  const add = (geo, mat, y) => { const m = new THREE.Mesh(geo, mat); m.position.y = y; m.castShadow = true; brush.add(m); return m; };
  add(new THREE.CylinderGeometry(8, 12.5, 190, 28), wood, 110 + 95);
  add(new THREE.SphereGeometry(8, 20, 12), capMat, 300);
  add(new THREE.CylinderGeometry(13.2, 12, 50, 32), steel, 85);
  add(new THREE.TorusGeometry(13.3, 0.8, 10, 40), dark, 98).rotation.x = Math.PI / 2;
  add(new THREE.TorusGeometry(12.6, 0.8, 10, 40), dark, 70).rotation.x = Math.PI / 2;
  const hairPts = [[0, 0], [3, 5], [6.6, 14], [9.4, 28], [11, 44], [10.8, 60]].map(p => new THREE.Vector2(p[0], p[1]));
  add(new THREE.LatheGeometry(hairPts, 36), hair, 0);
  const tipPts = [[0, 0], [3.4, 5], [7, 14], [8.4, 21]].map(p => new THREE.Vector2(p[0], p[1]));
  add(new THREE.LatheGeometry(tipPts, 36), inkMat, 0.2);
  scene.add(brush);

  // Where the line is, in page pixels relative to the hero, and the same in world units
  const L = ink.getTotalLength();
  let s = 1, lineLeft = 0, lineTop = 0;
  const toWorld = (px, py) => new THREE.Vector3(px - W / 2, H / 2 - py, 0);
  const pointAt = (t) => { const p = ink.getPointAtLength(t * L); return toWorld(lineLeft + p.x * s, lineTop + p.y * s); };

  function resize() {
    W = hero.clientWidth; H = hero.clientHeight;
    renderer.setSize(W, H, false);
    camera.aspect = W / H;
    D = (H / 2) / Math.tan(THREE.MathUtils.degToRad(FOV / 2));
    camera.position.set(0, 0, D);
    camera.lookAt(0, 0, 0);
    camera.updateProjectionMatrix();
    floor.scale.set(W * 3, H * 3, 1);
    const sc = key.shadow.camera;
    sc.left = -W; sc.right = W; sc.top = H; sc.bottom = -H; sc.near = 1; sc.far = 4000;
    sc.updateProjectionMatrix();
    const r = lineSvg.getBoundingClientRect(), hr = hero.getBoundingClientRect();
    s = r.width / 600;
    lineLeft = r.left - hr.left;
    lineTop = r.top - hr.top + (r.height - 18 * s) / 2;
    // The brush is sized from the line it paints: about two thirds of the line's length, tip to cap
    k = Math.max(170, Math.min(420, r.width * 0.62)) / 300;
    brush.scale.setScalar(k);
  }
  resize();
  window.addEventListener('resize', resize);

  // Easing to match the stroke's CSS ease-out, plus a couple of others
  const bez = (x1, y1, x2, y2) => (x) => {
    let lo = 0, hi = 1, t = x;
    for (let i = 0; i < 24; i++) { const cx = 3 * x1 * t * (1 - t) * (1 - t) + 3 * x2 * t * t * (1 - t) + t * t * t; if (cx < x) { lo = t; } else { hi = t; } t = (lo + hi) / 2; }
    return 3 * y1 * t * (1 - t) * (1 - t) + 3 * y2 * t * t * (1 - t) + t * t * t;
  };
  const easeOut = bez(0, 0, 0.58, 1), swoop = bez(0.2, 0.8, 0.2, 1), easeInOut = bez(0.45, 0, 0.55, 1), easeIn = bez(0.4, 0, 0.9, 0.5);
  const lerp = (a, b, t) => a + (b - a) * t;

  // One clock for everything. It starts the moment this script is ready, and the line follows the
  // brush: the stylesheet's own stroke animation is switched off and the dash offset is set by hand
  // every frame, so the two can never drift apart however long the library took to arrive.
  const DASH = 598;
  const wet = lineSvg.querySelector('path.wet');
  [ink, wet].forEach(p => { if (p) { p.style.animation = 'none'; p.style.strokeDashoffset = DASH; } });
  const t0 = 0;
  const clockStart = performance.now() / 1000;
  if (CCT.lightName) { CCT.lightName(0); }
  let strokeDone = false;
  const setStroke = (u) => {
    const off = (DASH * (1 - u)).toFixed(1);
    ink.style.strokeDashoffset = off;
    if (wet) { wet.style.strokeDashoffset = off; }
  };
  const REST = { x: 0, y: 0 };
  const base = { rx: 0.55, ry: 0, rz: -0.5 };
  let pointer = { x: 0, y: 0, has: false };
  let phase = 'wait', done = false;
  let flecked = false, lit = false;
  const start = pointAt(0), end = pointAt(1);
  // It comes to rest beside the end of the line, handle pointing right if there is room, else left
  const room = (end.x + W / 2) + 320 * k < W;
  const restPos = new THREE.Vector3(room ? end.x + 90 * k : end.x + 16 * k, room ? end.y - 26 * k : end.y - 8 * k, 0);
  const restZ = room ? -1.15 : -0.35;

  function setOpacity(o) { mats.forEach(m => { m.opacity = o; }); }

  function update(now) {
    const t = now / 1000 - clockStart;
    const p = brush.position, r = brush.rotation;
    if (t < 0.3) { phase = 'wait'; setOpacity(0); return; }
    if (t < 1.1) {
      phase = 'swoop';
      const u = swoop((t - 0.3) / 0.8);
      setOpacity(Math.min(1, u * 2));
      p.set(lerp(start.x + W * 0.38, start.x, u), lerp(start.y + H * 0.75, start.y, u), lerp(1050, 0, u));
      r.set(lerp(1.5, base.rx, u), lerp(1.3, base.ry, u), lerp(0.9, base.rz, u));
      if (u > 0.9) { const dab = 1 - (u - 0.9) * 6; brush.scale.setScalar(k * (1 - 0.04 * Math.max(0, dab))); }
      if (!lit && t > 1.0 && CCT.lightName) { lit = true; CCT.lightName(t0 * 1000); }
      return;
    }
    if (t < 2.7) {
      phase = 'paint';
      const u = easeOut((t - 1.1) / 1.6);
      const at = pointAt(u);
      const wob = Math.sin(u * Math.PI * 3) * 0.05;
      p.set(at.x, at.y, 0);
      r.set(base.rx - wob * 0.6, base.ry, base.rz + wob);
      brush.scale.setScalar(k);
      setOpacity(1);
      setStroke(u);
      return;
    }
    if (!strokeDone) { strokeDone = true; setStroke(1); }
    // The wet paint dries once the brush has passed
    if (wet && t < 4.3) {
      const v = Math.max(0, Math.min(1, (t - 2.8) / 1.4));
      wet.style.opacity = (0.32 * (1 - easeOut(v))).toFixed(3);
      wet.style.strokeWidth = (12 - 7 * v).toFixed(1) + 'px';
    }
    if (t < 3.45) {
      phase = 'lift';
      const u = easeIn((t - 2.7) / 0.75);
      p.set(lerp(end.x, end.x + 160 * k, u), lerp(end.y, end.y + 220 * k, u), lerp(0, 520, u));
      r.set(lerp(base.rx, 1.1, u), lerp(base.ry, -0.8, u), lerp(base.rz, 0.1, u));
      if (!flecked && CCT.flecks) {
        flecked = true;
        const host = document.querySelector('.hero-copy');
        if (host) {
          const hr2 = host.getBoundingClientRect(), hh = hero.getBoundingClientRect();
          const lr = lineSvg.getBoundingClientRect();
          CCT.flecks(host, lr.left - hr2.left + 598 * s, lr.top - hr2.top + (lr.height - 18 * s) / 2 + 8 * s, 2680);
        }
      }
      return;
    }
    if (t < 4.3) {
      phase = 'settle';
      const u = easeInOut((t - 3.45) / 0.85);
      const from = { x: end.x + 160 * k, y: end.y + 220 * k, z: 520 };
      p.set(lerp(from.x, restPos.x, u), lerp(from.y, restPos.y, u), lerp(from.z, 0, u));
      r.set(lerp(1.1, 0.35, u), lerp(-0.8, 0, u), lerp(0.1, restZ, u));
      return;
    }
    // At rest: a slow breath, and it turns towards the pointer
    phase = 'rest';
    const breathe = Math.sin(t * 1.3) * 3 * k;
    let tx = 0, ty = 0, lift = 0;
    if (pointer.has) {
      const dx = pointer.x - (restPos.x + W / 2), dy = pointer.y - (H / 2 - restPos.y);
      tx = THREE.MathUtils.clamp(-dy / H, -0.5, 0.5);
      ty = THREE.MathUtils.clamp(dx / W, -0.5, 0.5);
      const dist = Math.hypot(dx, dy);
      lift = dist < 160 * k ? (1 - dist / (160 * k)) * 70 : 0;
    }
    p.x = restPos.x; p.y = lerp(p.y, restPos.y + breathe + lift * 0.4, 0.08); p.z = lerp(p.z, lift, 0.08);
    r.x = lerp(r.x, 0.35 + tx * 0.6, 0.06);
    r.y = lerp(r.y, ty * 0.9, 0.06);
    r.z = lerp(r.z, restZ + ty * 0.15, 0.06);
  }

  // The lamp follows the pointer; so does the brush's attention
  if (fine) {
    document.addEventListener('mousemove', (e) => {
      const hr = hero.getBoundingClientRect();
      pointer = { x: e.clientX - hr.left, y: e.clientY - hr.top, has: true };
      lamp.position.set(pointer.x - W / 2, H / 2 - pointer.y, 420);
    });
  }

  // Render only while the hero is on screen
  let visible = true;
  if ('IntersectionObserver' in window) {
    new IntersectionObserver((es) => { visible = es[0].isIntersecting; if (visible) { requestAnimationFrame(frame); } }, { threshold: 0 }).observe(hero);
  }
  // At rest it only needs half the frames; while it moves it gets them all
  let last = 0;
  function frame(now) {
    if (!visible) { return; }
    requestAnimationFrame(frame);
    if (phase === 'rest' && now - last < 30) { return; }
    last = now;
    update(now);
    renderer.render(scene, camera);
  }
  requestAnimationFrame(frame);

  // A turned wooden handle, drawn once
  function woodTexture() {
    const c = document.createElement('canvas');
    c.width = 256; c.height = 1024;
    const g = c.getContext('2d');
    g.fillStyle = '#7a4d24';
    g.fillRect(0, 0, 256, 1024);
    for (let i = 0; i < 260; i++) {
      const x = Math.random() * 256, w = 1 + Math.random() * 7;
      const shade = Math.random() < 0.5 ? 'rgba(40,20,8,' + (0.08 + Math.random() * 0.25) + ')' : 'rgba(220,170,110,' + (0.05 + Math.random() * 0.18) + ')';
      g.fillStyle = shade;
      g.fillRect(x, 0, w, 1024);
    }
    g.globalAlpha = 0.5;
    for (let y = 0; y < 1024; y += 2) {
      g.fillStyle = 'rgba(0,0,0,' + (Math.random() * 0.06) + ')';
      g.fillRect(0, y, 256, 1);
    }
    g.globalAlpha = 1;
    const tex = new THREE.CanvasTexture(c);
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 4;
    return tex;
  }
}
