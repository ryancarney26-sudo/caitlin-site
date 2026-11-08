/* The brush as a real object, for big screens with a mouse. The opener (the brush that paints the
   line under her name) is plain CSS and never waits for this. Once the opener has finished, this
   brings a three.js brush down to rest beside the line, where it breathes and turns to follow the
   pointer, lit by a violet lamp that follows the pointer too, casting its shadow on the page.
   Phones, touch screens, reduced motion and browsers without WebGL never fetch the library. */
const CCT = window.CCT || (window.CCT = {});
const canvas = document.getElementById('brush-gl');
const ink = document.getElementById('stencil-path');
const pen = document.querySelector('.ink .pen');
const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const fine = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

function standDown() { if (canvas) { canvas.style.display = 'none'; } }

if (!canvas || !ink || reduce || !fine || CCT.lite) {
  standDown();
} else {
  import('/assets/vendor/three.module.min.js')
    .then((THREE) => { try { run(THREE); } catch (e) { standDown(); } })
    .catch(standDown);
}

function run(THREE) {
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
  let W = 1, H = 1, k = 1;

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
  [wood, steel, dark, hair, inkMat, capMat].forEach(m => { m.transparent = true; m.opacity = 0; mats.push(m); });
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

  // Where the end of the line is, and where the brush rests beside it. The line is a 600 by 18
  // drawing stretched to the line's box, so its units map straight onto that box.
  const L = ink.getTotalLength();
  let end = new THREE.Vector3(), restPos = new THREE.Vector3(), restZ = -1.15;
  const toWorld = (px, py) => new THREE.Vector3(px - W / 2, H / 2 - py, 0);

  function resize() {
    W = hero.clientWidth; H = hero.clientHeight;
    renderer.setSize(W, H, false);
    camera.aspect = W / H;
    camera.position.set(0, 0, (H / 2) / Math.tan(THREE.MathUtils.degToRad(FOV / 2)));
    camera.lookAt(0, 0, 0);
    camera.updateProjectionMatrix();
    floor.scale.set(W * 3, H * 3, 1);
    const sc = key.shadow.camera;
    sc.left = -W; sc.right = W; sc.top = H; sc.bottom = -H; sc.near = 1; sc.far = 4000;
    sc.updateProjectionMatrix();
    const r = lineSvg.getBoundingClientRect(), hr = hero.getBoundingClientRect();
    const p = ink.getPointAtLength(L);
    end = toWorld(r.left - hr.left + p.x * r.width / 600, r.top - hr.top + p.y * r.height / 18);
    k = Math.max(170, Math.min(420, r.width * 0.62)) / 300;
    brush.scale.setScalar(k);
    // Rest beside the end of the line, handle to the right if there is room, else standing up
    const room = (end.x + W / 2) + 320 * k < W;
    restPos = new THREE.Vector3(room ? end.x + 90 * k : end.x - 12 * k, room ? end.y - 26 * k : end.y - 6 * k, 0);
    restZ = room ? -1.15 : 0.38;
  }
  resize();
  window.addEventListener('resize', resize);

  const easeInOut = (x) => x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
  const lerp = (a, b, t) => a + (b - a) * t;
  const setOpacity = (o) => { mats.forEach(m => { m.opacity = o; }); };

  let settleAt = null, phase = 'wait';
  let pointer = { x: 0, y: 0, has: false };

  function update(now) {
    const t = now / 1000 - settleAt;
    const p = brush.position, r = brush.rotation;
    if (t < 0.9) {
      // Down from up and to the right, where the painting brush lifted away, to rest by the line
      phase = 'settle';
      const u = easeInOut(Math.max(0, t) / 0.9);
      setOpacity(Math.min(1, u * 1.8));
      p.set(lerp(end.x + 130 * k, restPos.x, u), lerp(end.y + 230 * k, restPos.y, u), lerp(420, 0, u));
      r.set(lerp(1.1, 0.35, u), lerp(-0.8, 0, u), lerp(0.1, restZ, u));
      return;
    }
    // At rest: a slow breath, and it turns towards the pointer; it lifts when the pointer comes close
    phase = 'rest';
    setOpacity(1);
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

  document.addEventListener('mousemove', (e) => {
    const hr = hero.getBoundingClientRect();
    pointer = { x: e.clientX - hr.left, y: e.clientY - hr.top, has: true };
    lamp.position.set(pointer.x - W / 2, H / 2 - pointer.y, 420);
  });

  // Render only once the opener is done, and only while the hero is on screen; at rest, half rate
  let visible = true, last = 0, running = false;
  function frame(now) {
    if (!visible) { running = false; return; }
    running = true;
    requestAnimationFrame(frame);
    if (phase === 'rest' && now - last < 30) { return; }
    last = now;
    update(now);
    renderer.render(scene, camera);
  }
  const go = () => { if (settleAt !== null && visible && !running) { requestAnimationFrame(frame); } };
  if ('IntersectionObserver' in window) {
    new IntersectionObserver((es) => { visible = es[0].isIntersecting; go(); }, { threshold: 0 }).observe(hero);
  }
  const anims = pen && pen.getAnimations ? pen.getAnimations() : [];
  Promise.all(anims.map(a => a.finished.catch(() => null))).then(() => {
    settleAt = performance.now() / 1000;
    go();
  });

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
