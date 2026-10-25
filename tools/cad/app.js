/* MCT331s Smart Home - 3D model + control-logic simulation.
 * World frame is the CAD frame (mm): x right, y front->back, z up; the root group maps it to Three.js. */
(function () {
  'use strict';
  const D = JSON.parse(document.getElementById('scene-data').textContent);
  const P = D.params;
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const CAT = {
    sensor: 'Sensor', actuator: 'Actuator', processing: 'Information processing',
    interface: 'User interface', power: 'Power / driver', mech: 'Mechanical'
  };

  /**
   * Read a CSS custom property from :root.
   * @param {string} name token name including leading dashes
   * @returns {string} trimmed value
   */
  function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

  // ------------------------------------------------------------------ renderer / cameras
  const view = $('#view');
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.outputEncoding = THREE.sRGBEncoding;
  view.prepend(renderer.domElement);

  const scene = new THREE.Scene();
  const persp = new THREE.PerspectiveCamera(30, 1, 5, 8000);
  const ortho = new THREE.OrthographicCamera(-1, 1, 1, -1, -6000, 6000);
  const ctlP = new THREE.OrbitControls(persp, renderer.domElement);
  const ctlO = new THREE.OrbitControls(ortho, renderer.domElement);
  [ctlP, ctlO].forEach(c => { c.enableDamping = true; c.dampingFactor = 0.09; c.target.set(0, 95, 0); c.maxPolarAngle = Math.PI * 0.98; });
  ctlO.enabled = false;
  let cam = persp, ctl = ctlP, orthoMode = false, orthoH = 300;

  scene.add(new THREE.HemisphereLight(0xf4f6ff, 0x6b5a48, 0.62));
  const sun = new THREE.DirectionalLight(0xffffff, 0.85);
  sun.position.set(380, 650, 520);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -420, right: 420, top: 420, bottom: -420, near: 50, far: 2000 });
  sun.shadow.bias = -0.0006;
  scene.add(sun);
  const fill = new THREE.DirectionalLight(0xffffff, 0.25);
  fill.position.set(-500, 300, -300);
  scene.add(fill);

  const ground = new THREE.Mesh(new THREE.PlaneGeometry(3000, 3000), new THREE.ShadowMaterial({ opacity: 0.16 }));
  ground.rotation.x = -Math.PI / 2; ground.position.y = -3.05; ground.receiveShadow = true;
  scene.add(ground);
  let grid = null;

  /** Apply theme colours to the 3D background and grid. @returns {void} */
  function applyTheme() {
    scene.background = new THREE.Color(css('--viewbg') || '#dfe4ea');
    if (grid) { scene.remove(grid); grid.geometry.dispose(); }
    const dark = scene.background.getHSL({}).l < 0.3;
    grid = new THREE.GridHelper(1200, 24, dark ? 0x2a333d : 0xc4ccd5, dark ? 0x1b2128 : 0xd4dae1);
    grid.position.y = -3.1;
    scene.add(grid);
    $$('.lbl3d').forEach(e => e.remove()); labelEls.length = 0;
    if (state.labels) buildLabels();
  }

  // root: CAD world (x, y, z) -> three (x-150, z, 110-y)
  const root = new THREE.Group();
  root.matrixAutoUpdate = false;
  root.matrix.set(1, 0, 0, -P.W / 2, 0, 0, 1, 0, 0, -1, 0, P.D / 2, 0, 0, 0, 1);
  scene.add(root);

  // ------------------------------------------------------------------ materials
  /**
   * Procedural MDF texture (fine fibre noise) on a canvas.
   * @param {string} base hex colour
   * @returns {THREE.CanvasTexture}
   */
  function mdfTexture(base) {
    const c = document.createElement('canvas'); c.width = c.height = 256;
    const g = c.getContext('2d');
    g.fillStyle = base; g.fillRect(0, 0, 256, 256);
    for (let i = 0; i < 9000; i++) {
      const a = Math.random() * 0.07;
      g.fillStyle = Math.random() < 0.5 ? `rgba(80,50,25,${a})` : `rgba(255,240,220,${a})`;
      g.fillRect(Math.random() * 256, Math.random() * 256, 1 + Math.random() * 2, 1);
    }
    const t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(1 / 120, 1 / 120); t.encoding = THREE.sRGBEncoding;
    return t;
  }
  const MAT = {
    face: new THREE.MeshStandardMaterial({ color: 0xffffff, map: mdfTexture('#c79c6c'), roughness: 0.86, metalness: 0 }),
    roof: new THREE.MeshStandardMaterial({ color: 0xffffff, map: mdfTexture('#a9774b'), roughness: 0.9 }),
    door: new THREE.MeshStandardMaterial({ color: 0xffffff, map: mdfTexture('#8f6038'), roughness: 0.8 }),
    edge: new THREE.MeshStandardMaterial({ color: 0x4a2f1d, roughness: 0.95 }),
    hl: new THREE.MeshStandardMaterial({ color: 0xffd27a, emissive: 0x6a4a00, roughness: 0.7 }),
    hlEdge: new THREE.MeshStandardMaterial({ color: 0xffb020, emissive: 0x553300 })
  };
  const XRAY = ['face', 'roof', 'door', 'edge'].reduce((o, k) => {
    o[k] = MAT[k].clone(); o[k].transparent = true; o[k].opacity = k === 'edge' ? 0.35 : 0.16; o[k].depthWrite = false; return o;
  }, {});

  // ------------------------------------------------------------------ scene state
  const state = {
    variant: 'B', dims: true, labels: false, xray: false, roofOpen: false, explode: 0,
    code: '1234', buf: '', msgUntil: 0, msg: null,
    doorOpen: false, doorCloseAt: 0, doorAng: 0,
    armed: false, win: false, winAng: 0, alarm: false, muted: false, motionUntil: 0,
    amb: 70, thr: 40, manual: false, temp: 26, set: 30, fan: false, roofAng: 0, propSpeed: 0, page: 0, pageT: 0
  };
  let build = null;           // current variant objects
  const labelEls = [];

  /**
   * Build a Three geometry for a laser-cut part from its 2D outline.
   * @param {object} p part record from scene JSON
   * @returns {THREE.ExtrudeGeometry}
   */
  function partGeometry(p) {
    const sh = new THREE.Shape(p.outer.map(([u, v]) => new THREE.Vector2(u, v)));
    p.holes.forEach(h => sh.holes.push(new THREE.Path(h.map(([u, v]) => new THREE.Vector2(u, v)))));
    p.circles.forEach(([u, v, r]) => { const c = new THREE.Path(); c.absarc(u, v, r, 0, Math.PI * 2, true); sh.holes.push(c); });
    return new THREE.ExtrudeGeometry(sh, { depth: P.T, bevelEnabled: false, curveSegments: 30 });
  }

  const EXPLODE = {
    FRONT: [0, -70, 0], BACK: [0, 70, 0], LEFT: [-70, 0, 0], RIGHT: [70, 0, 0], BASE: [0, 0, -45],
    PARTITION: [0, 30, 25], FANPLATE: [-30, 0, 25], FANRIB: [-45, 0, 25], SHELF: [0, -40, 40],
    DOOR: [0, -95, 0], SASH: [100, 0, 0], ROOF: [0, 0, 120], TRUSS: [0, 0, 85],
    LID: [0, 0, 130], LOCATOR: [0, 0, 95], KNOB: [0, 0, 160]
  };

  /**
   * Create a primitive mesh for a component in world coordinates.
   * @param {object} pr primitive record
   * @param {object} comp owning component
   * @returns {THREE.Object3D}
   */
  function prim(pr, comp) {
    const mat = () => new THREE.MeshStandardMaterial({ color: pr.col || '#888', roughness: 0.55, metalness: pr.col === '#c9ccd1' || pr.col === '#c0c4ca' ? 0.6 : 0.05 });
    let o;
    const [cx, cy, cz] = pr.c;
    if (pr.t === 'box') {
      o = new THREE.Mesh(new THREE.BoxGeometry(pr.s[0], pr.s[1], pr.s[2]), mat());
    } else if (pr.t === 'cyl') {
      o = new THREE.Mesh(new THREE.CylinderGeometry(pr.r, pr.r, pr.h, 28), mat());
      if (pr.axis === 'z') o.rotation.x = Math.PI / 2;
      if (pr.axis === 'x') o.rotation.z = Math.PI / 2;
    } else if (pr.t === 'sph') {
      o = new THREE.Mesh(new THREE.SphereGeometry(pr.r, 28, 16, 0, Math.PI * 2, 0, Math.PI / 2),
        new THREE.MeshStandardMaterial({ color: pr.col, roughness: 0.35, transparent: true, opacity: 0.93 }));
      o.rotation.x = Math.PI;   // cap +Y -> -y: dome points out of the front wall
    } else if (pr.t === 'led') {
      o = new THREE.Group();
      const m = new THREE.MeshStandardMaterial({ color: 0xf2f6ff, roughness: 0.15, transparent: true, opacity: 0.9, emissive: 0x000000 });
      const body = new THREE.Mesh(new THREE.CylinderGeometry(pr.r, pr.r, pr.h, 20), m);
      const dome = new THREE.Mesh(new THREE.SphereGeometry(pr.r, 20, 12), m);
      dome.position.y = -pr.h / 2;
      o.add(body, dome);
      const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: 0xfff3c4, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending }));
      glow.scale.set(34, 34, 1); glow.position.y = -pr.h / 2 - 2;
      o.add(glow);
      const light = new THREE.PointLight(0xfff1cf, 0, pr.light === 'ext' ? 260 : 300, 1.6);
      light.position.y = -pr.h / 2 - 6;
      o.add(light);
      o.userData.led = { m, glow, light, kind: pr.light };
    } else if (pr.t === 'lcd') {
      lcdCanvas = document.createElement('canvas'); lcdCanvas.width = 512; lcdCanvas.height = 128;
      lcdTex = new THREE.CanvasTexture(lcdCanvas); lcdTex.encoding = THREE.sRGBEncoding;
      o = new THREE.Mesh(new THREE.PlaneGeometry(pr.s[0], pr.s[2]), new THREE.MeshBasicMaterial({ map: lcdTex }));
      o.rotation.x = Math.PI / 2;
    } else if (pr.t === 'keypad') {
      o = new THREE.Mesh(new THREE.PlaneGeometry(pr.s[0], pr.s[2]), new THREE.MeshStandardMaterial({ map: keypadTexture(), roughness: 0.5 }));
      o.rotation.x = Math.PI / 2;
      o.userData.keypad = true;
    } else if (pr.t === 'tog') {
      o = new THREE.Group();
      const lever = new THREE.Mesh(new THREE.CylinderGeometry(pr.r * 0.7, pr.r, pr.h, 14), mat());
      lever.position.y = -pr.h / 2;
      o.add(lever);
      o.userData.toggle = true;
    } else if (pr.t === 'prop') {
      o = new THREE.Group();
      const m = new THREE.MeshStandardMaterial({ color: 0x2b6cb0, roughness: 0.45 });
      const hub = new THREE.Mesh(new THREE.CylinderGeometry(4, 4, 6, 18), m);
      hub.rotation.z = Math.PI / 2;
      o.add(hub);
      for (let k = 0; k < 4; k++) {
        const arm = new THREE.Group();
        const blade = new THREE.Mesh(new THREE.BoxGeometry(1.6, pr.r - 4, 10), m);
        blade.position.y = (pr.r - 4) / 2 + 3; blade.rotation.y = 0.45;
        arm.add(blade); arm.rotation.x = k * Math.PI / 2;
        o.add(arm);
      }
      o.userData.prop = true;
    } else if (pr.t === 'glass') {
      o = new THREE.Mesh(new THREE.BoxGeometry(pr.s[0], pr.s[1], pr.s[2]),
        new THREE.MeshStandardMaterial({ color: 0xbfe3ff, transparent: true, opacity: 0.28, roughness: 0.05, depthWrite: false }));
    }
    o.position.set(cx, cy, cz);
    o.traverse(m => { if (m.isMesh) { m.castShadow = !m.material.transparent; m.receiveShadow = true; m.userData.comp = comp.id; } });
    return o;
  }

  const glowTex = (() => {
    const c = document.createElement('canvas'); c.width = c.height = 64;
    const g = c.getContext('2d'); const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.25, 'rgba(255,240,200,.6)'); gr.addColorStop(1, 'rgba(255,230,180,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
    return new THREE.CanvasTexture(c);
  })();
  let lcdCanvas = null, lcdTex = null;
  const KEYS = ['1', '2', '3', 'A', '4', '5', '6', 'B', '7', '8', '9', 'C', '*', '0', '#', 'D'];

  /** Draw the membrane keypad face. @returns {THREE.CanvasTexture} */
  function keypadTexture() {
    const c = document.createElement('canvas'); c.width = 276; c.height = 304;
    const g = c.getContext('2d');
    g.fillStyle = '#10141c'; g.fillRect(0, 0, 276, 304);
    for (let i = 0; i < 16; i++) {
      const col = i % 4, row = Math.floor(i / 4);
      const x = 10 + col * 66, y = 10 + row * 73;
      g.fillStyle = col === 3 ? '#b42318' : (KEYS[i] === '*' || KEYS[i] === '#') ? '#1f4fb8' : '#2d3442';
      g.beginPath(); g.roundRect ? g.roundRect(x, y, 58, 64, 9) : g.rect(x, y, 58, 64); g.fill();
      g.fillStyle = '#f5f7fa'; g.font = '600 34px monospace'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText(KEYS[i], x + 29, y + 33);
    }
    const t = new THREE.CanvasTexture(c); t.encoding = THREE.sRGBEncoding; return t;
  }

  /**
   * Text sprite for dimension labels.
   * @param {string} text label
   * @param {number} h height in mm
   * @returns {THREE.Sprite}
   */
  function textSprite(text, h) {
    const c = document.createElement('canvas');
    const g = c.getContext('2d');
    const fs = 44; g.font = `600 ${fs}px "JetBrains Mono", monospace`;
    const w = Math.ceil(g.measureText(text).width) + 28;
    c.width = w; c.height = 64;
    const g2 = c.getContext('2d');
    g2.fillStyle = css('--panel') || '#fff';
    g2.strokeStyle = css('--accent') || '#2350d8'; g2.lineWidth = 3;
    g2.beginPath(); g2.roundRect ? g2.roundRect(2, 2, w - 4, 60, 12) : g2.rect(2, 2, w - 4, 60); g2.fill(); g2.stroke();
    g2.fillStyle = css('--accent') || '#2350d8'; g2.font = `600 ${fs}px "JetBrains Mono", monospace`;
    g2.textAlign = 'center'; g2.textBaseline = 'middle'; g2.fillText(text, w / 2, 34);
    const t = new THREE.CanvasTexture(c); t.encoding = THREE.sRGBEncoding;
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, depthTest: false, transparent: true }));
    s.scale.set(h * w / 64, h, 1); s.renderOrder = 20;
    return s;
  }

  /**
   * Add a linear dimension (extension lines, dim line, ticks, label) in world mm.
   * @param {THREE.Group} g target group
   * @param {number[]} a start point  @param {number[]} b end point
   * @param {number[]} off offset vector for the dimension line
   * @param {string} text label
   * @returns {void}
   */
  function dim(g, a, b, off, text) {
    const A = new THREE.Vector3(...a), B = new THREE.Vector3(...b), O = new THREE.Vector3(...off);
    const A2 = A.clone().add(O), B2 = B.clone().add(O);
    const on = O.clone().normalize();
    const dir = B2.clone().sub(A2).normalize();
    const tick = dir.clone().add(on).normalize().multiplyScalar(4);
    const pts = [A, A2.clone().addScaledVector(on, 4), B, B2.clone().addScaledVector(on, 4), A2, B2,
      A2.clone().sub(tick), A2.clone().add(tick), B2.clone().sub(tick), B2.clone().add(tick)];
    const geo = new THREE.BufferGeometry().setFromPoints(pts);
    const ln = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({ color: new THREE.Color(css('--accent') || '#2350d8'), depthTest: false, transparent: true, opacity: 0.95 }));
    ln.renderOrder = 19;
    g.add(ln);
    const s = textSprite(text, 11);
    s.position.copy(A2.clone().add(B2).multiplyScalar(0.5));
    g.add(s);
  }

  /**
   * Dimension set for a variant.
   * @param {string} v variant
   * @returns {THREE.Group}
   */
  function buildDims(v) {
    const g = new THREE.Group();
    dim(g, [0, 0, 0], [P.W, 0, 0], [0, -34, 0], `${P.W}`);
    dim(g, [P.W, 0, 0], [P.W, P.D, 0], [34, 0, 0], `${P.D}`);
    dim(g, [0, 0, 0], [0, 0, P.H], [-28, -6, 0], `${P.H}`);
    if (v === 'A') dim(g, [0, P.D / 2, 0], [0, P.D / 2, P.H + P.rise], [-30, 0, 0], `${P.H + P.rise}`);
    else dim(g, [0, P.D / 2, 0], [0, P.D / 2, P.H + 3 * P.T], [-30, 0, 0], `${P.H + 3 * P.T}`);
    dim(g, [-10, -10, -3], [P.W + 10, -10, -3], [0, -58, 0], `BASE ${P.W + 20}×${P.D + 20}`);
    dim(g, [40, 0, 100], [100, 0, 100], [0, -2, 14], 'DOOR 60');
    dim(g, [40, 0, 0], [40, 0, 100], [-12, -2, 0], '100');
    dim(g, [P.W, 45, 125], [P.W, 115, 125], [8, 0, 16], 'WINDOW 70×55');
    dim(g, [0, 69, 116], [0, 131, 116], [-6, 0, 12], 'FAN Ø62');
    dim(g, [0, 0, 152], [0, 139, 152], [-6, 0, 0], 'BAY @139');
    return g;
  }

  /**
   * Build the whole model for one variant.
   * @param {string} v "A" or "B"
   * @returns {void}
   */
  function buildVariant(v) {
    while (root.children.length) {
      const c = root.children.pop();
      c.traverse(o => { if (o.geometry) o.geometry.dispose(); });
    }
    const V = D.variants[v];
    const b = { pivots: {}, groups: {}, meshes: [], partMeshes: {}, compObjs: {}, leds: [], prop: null, toggle: null, dims: null, buzzer: null };
    const mkPivot = (name, x, y, z) => {
      const pv = new THREE.Group(); pv.position.set(x, y, z); root.add(pv);
      const inner = new THREE.Group(); inner.position.set(-x, -y, -z); pv.add(inner);
      b.pivots[name] = { pv, inner };
      return inner;
    };
    const struct = new THREE.Group(); root.add(struct);
    b.pivots.struct = { pv: struct, inner: struct };
    mkPivot('door', P.servo[0], P.servo[1], 0);
    mkPivot('sash', P.W, P.sash_y, 0);
    mkPivot('roof', 0, P.D, P.H);
    V.parts.forEach(p => {
      const eg = new THREE.Group();
      eg.userData.dir = new THREE.Vector3(...(EXPLODE[p.id] || [0, 0, 0]));
      (b.pivots[p.group] || b.pivots.struct).inner.add(eg);
      b.groups[p.id] = eg;
      const geo = partGeometry(p);
      b.partMeshes[p.id] = [];
      p.places.forEach(pl => {
        const isRoof = p.role === 'roof';
        const skin = isRoof ? 'roof' : (p.id === 'DOOR' || p.id === 'SASH') ? 'door' : 'face';
        const m = new THREE.Mesh(geo, [MAT[skin], MAT.edge]);
        m.matrixAutoUpdate = false;
        m.matrix.makeBasis(new THREE.Vector3(...pl.U), new THREE.Vector3(...pl.V), new THREE.Vector3(...pl.W)).setPosition(...pl.O);
        m.castShadow = true; m.receiveShadow = true;
        m.userData.part = p.id; m.userData.skin = skin;
        eg.add(m); b.meshes.push(m); b.partMeshes[p.id].push(m);
      });
    });
    D.components.forEach(c => {
      const parentId = c.group === 'sash' ? 'SASH' : c.mount;
      const parent = b.groups[parentId] || b.groups.BASE;
      const g = new THREE.Group();
      c.prims.forEach(pr => g.add(prim(pr, c)));
      parent.add(g);
      b.compObjs[c.id] = g;
      g.traverse(o => {
        if (o.isMesh) b.meshes.push(o);
        if (o.userData.led) b.leds.push(o.userData.led);
        if (o.userData.prop) b.prop = o;
        if (o.userData.toggle) b.toggle = o;
      });
      if (c.id === 'buzz') b.buzzer = g.children[0];
      if (c.id === 'pot') b.pot = g.children[0];
    });
    b.dims = buildDims(v);
    b.dims.visible = state.dims;
    root.add(b.dims);
    build = b;
    applyXray();
    $('#spec').textContent = v === 'A'
      ? `3 mm MDF · ${P.W} × ${P.D} mm footprint · ridge ${P.H + P.rise} mm · gable roof on 2 rear hinges · ${V.sheets} sheets 600×400`
      : `3 mm MDF · ${P.W} × ${P.D} mm footprint · height ${P.H + 3 * P.T} mm · flat lid with corner locators · ${V.sheets} sheets 600×400`;
    $('#tRoof').textContent = v === 'A' ? 'Open roof' : 'Lift lid';
    renderPanels(); renderBom();
    $$('.lbl3d').forEach(e => e.remove()); labelEls.length = 0;
    if (state.labels) buildLabels();
    drawLCD(true);
  }

  /** Apply/clear x-ray materials on walls and roof. @returns {void} */
  function applyXray() {
    if (!build) return;
    build.meshes.forEach(m => {
      if (!m.userData.part || m.userData.hl) return;
      const id = m.userData.part;
      const see = state.xray && id !== 'BASE' && id !== 'DOOR';
      const face = m.userData.skin;
      m.material = see ? [XRAY[face], XRAY.edge] : [MAT[face], MAT.edge];
      m.castShadow = !see;
    });
  }

  // ------------------------------------------------------------------ labels
  const SHORT = { uno: 'Arduino UNO', bb: 'Breadboard', lcd: 'LCD 16×2', kp: 'Keypad 4×4', pir: 'PIR', extled: 'Exterior LED', servo: 'Servo SG90', tog: 'ARM toggle', pot: 'Set-point pot', ldr: 'LDR', reed: 'MC-38 reed', motor: 'Fan F130', dht: 'DHT11', inled2: 'Indoor LEDs', buzz: 'Buzzer', esp: 'ESP8266', btnL: 'Buttons' };
  const LABEL_IDS = ['uno', 'bb', 'lcd', 'kp', 'pir', 'extled', 'servo', 'tog', 'pot', 'ldr', 'reed', 'motor', 'dht', 'inled2', 'buzz', 'esp', 'btnL'];
  /** Create HTML labels for key components. @returns {void} */
  function buildLabels() {
    LABEL_IDS.forEach(id => {
      const c = D.components.find(x => x.id === id); if (!c) return;
      const el = document.createElement('div'); el.className = 'lbl3d';
      el.style.borderLeftColor = css('--c-' + c.cat);
      el.textContent = SHORT[id] || c.name;
      view.appendChild(el);
      labelEls.push({ el, id });
    });
  }
  const tmpV = new THREE.Vector3(), box3 = new THREE.Box3();
  /** Position HTML labels every frame. @returns {void} */
  function updateLabels() {
    if (!labelEls.length || !build) return;
    const r = renderer.domElement.getBoundingClientRect();
    labelEls.forEach(({ el, id }) => {
      const o = build.compObjs[id]; if (!o) return;
      box3.setFromObject(o); box3.getCenter(tmpV); tmpV.y = box3.max.y;
      tmpV.project(cam);
      const vis = tmpV.z < 1 && Math.abs(tmpV.x) < 1.05 && Math.abs(tmpV.y) < 1.05;
      el.hidden = !vis;
      el.style.left = ((tmpV.x + 1) / 2 * r.width) + 'px';
      el.style.top = ((1 - tmpV.y) / 2 * r.height - 4) + 'px';
    });
  }

  // ------------------------------------------------------------------ views
  const VIEWS = {
    iso: { dir: [0.62, 0.52, 0.72], name: 'Isometric', ortho: null },
    front: { dir: [0, 0.0001, 1], name: 'Front view', ortho: true },
    back: { dir: [0, 0.0001, -1], name: 'Back view', ortho: true },
    left: { dir: [-1, 0.0001, 0], name: 'Left view', ortho: true },
    right: { dir: [1, 0.0001, 0], name: 'Right view', ortho: true },
    top: { dir: [0, 1, 0.0001], name: 'Top view', ortho: true }
  };
  let tween = null;

  /**
   * Fit the orthographic frustum to the viewport.
   * @returns {void}
   */
  function fitOrtho() {
    const w = view.clientWidth, h = view.clientHeight, a = w / h;
    ortho.left = -orthoH * a; ortho.right = orthoH * a; ortho.top = orthoH; ortho.bottom = -orthoH;
    ortho.updateProjectionMatrix();
  }

  /**
   * Switch projection, carrying the camera pose across.
   * @param {boolean} on orthographic?
   * @returns {void}
   */
  function setOrtho(on) {
    if (on === orthoMode) return;
    const from = cam, fromCtl = ctl;
    orthoMode = on;
    cam = on ? ortho : persp; ctl = on ? ctlO : ctlP;
    cam.position.copy(from.position); ctl.target.copy(fromCtl.target);
    if (on) { const d = from.position.distanceTo(fromCtl.target); orthoH = d * Math.tan(THREE.MathUtils.degToRad(persp.fov / 2)); ortho.zoom = 1; fitOrtho(); }
    fromCtl.enabled = false; ctl.enabled = true; ctl.update();
    $('#tOrtho').setAttribute('aria-pressed', String(on));
  }

  /**
   * Animate to a named view.
   * @param {string} key view key
   * @returns {void}
   */
  function goView(key) {
    const vw = VIEWS[key];
    $$('[data-view]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.view === key)));
    $('#viewname').textContent = vw.name;
    if (vw.ortho) setOrtho(true);
    const target = new THREE.Vector3(0, key === 'top' ? 0 : 95, 0);
    const a = view.clientWidth / Math.max(1, view.clientHeight), widen = a < 1.25 ? 1.25 / a : 1;
    const dist = (key === 'iso' ? 900 : 1400) * (key === 'iso' ? widen : 1);
    const dest = new THREE.Vector3(...vw.dir).normalize().multiplyScalar(dist).add(target);
    if (orthoMode) { orthoH = (key === 'top' ? 230 : 210) * widen; ortho.zoom = 1; fitOrtho(); }
    tween = { s: performance.now(), dur: reduceMotion ? 1 : 650, p0: cam.position.clone(), p1: dest, t0: ctl.target.clone(), t1: target };
  }

  // ------------------------------------------------------------------ resize
  /** Resize renderer and cameras to the viewport. @returns {void} */
  function resize() {
    const w = view.clientWidth, h = view.clientHeight;
    renderer.setSize(w, h, false);
    persp.aspect = w / h; persp.updateProjectionMatrix();
    fitOrtho();
  }
  new ResizeObserver(resize).observe(view);

  // ------------------------------------------------------------------ picking / tooltip
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
  const tip = $('#tip');
  let hovered = null, downAt = null;

  /**
   * Raycast at a pointer event.
   * @param {PointerEvent} e event
   * @returns {THREE.Intersection|null}
   */
  function pick(e) {
    if (!build) return null;
    const r = renderer.domElement.getBoundingClientRect();
    ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, cam);
    const hits = ray.intersectObjects(build.meshes, false).filter(h => {
      if (!state.xray) return true;
      const id = h.object.userData.part;
      return !id || id === 'BASE' || id === 'DOOR';
    });
    return hits[0] || null;
  }

  /**
   * Highlight a part or component.
   * @param {object|null} key {part}|{comp}
   * @returns {void}
   */
  function setHighlight(key) {
    if (hovered && build) {
      if (hovered.part) (build.partMeshes[hovered.part] || []).forEach(m => { m.userData.hl = false; });
      if (hovered.comp) build.compObjs[hovered.comp] && build.compObjs[hovered.comp].traverse(o => { if (o.isMesh && o.material.emissive && o.userData.e0 !== undefined) o.material.emissive.setHex(o.userData.e0); });
      applyXray();
    }
    hovered = key;
    if (!key || !build) return;
    if (key.part) (build.partMeshes[key.part] || []).forEach(m => { m.userData.hl = true; m.material = [MAT.hl, MAT.hlEdge]; });
    if (key.comp) build.compObjs[key.comp] && build.compObjs[key.comp].traverse(o => {
      if (o.isMesh && o.material.emissive) { if (o.userData.e0 === undefined) o.userData.e0 = o.material.emissive.getHex(); o.material.emissive.setHex(0x7a5200); }
    });
  }

  /**
   * Tooltip HTML for a part or component.
   * @param {object} key {part}|{comp}
   * @returns {string}
   */
  function tipHtml(key) {
    if (key.comp) {
      const c = D.components.find(x => x.id === key.comp);
      return `<b>${c.name}</b><br><span class="k">${CAT[c.cat]}</span> · ${c.owned ? 'in your kit' : '<span style="color:var(--warn)">to buy</span>'}<br>${c.func}<br><span class="k">Size</span> ${c.dims}<br><span class="k">Where</span> ${c.where}${ACTIONS[c.id] ? '<br><i>Click to ' + ACTIONS[c.id][0] + '</i>' : ''}`;
    }
    const p = D.variants[state.variant].parts.find(x => x.id === key.part);
    return `<b>${p.name}</b><br><span class="k">3 mm MDF · laser cut</span> · qty ${p.qty}<br><span class="k">Flat size</span> ${p.size[0]} × ${p.size[1]} mm${p.id === 'SASH' ? '<br><i>Click to open / close the window</i>' : ''}${p.id === 'DOOR' ? '<br><i>Use the keypad to open</i>' : ''}`;
  }

  const ACTIONS = {
    tog: ['arm / disarm', () => setArmed(!state.armed)],
    btnL: ['toggle the light override', () => setManual(!state.manual)],
    btnM: ['mute / reset the alarm', () => mute()],
    mag: ['open / close the window', () => setWindow(!state.win)],
    reed: ['open / close the window', () => setWindow(!state.win)],
    pir: ['simulate motion', () => motion()],
    kp: ['press a key', null]
  };

  renderer.domElement.addEventListener('pointermove', e => {
    const h = pick(e);
    const key = h ? (h.object.userData.comp ? { comp: h.object.userData.comp } : { part: h.object.userData.part }) : null;
    const same = (a, b) => a && b && a.comp === b.comp && a.part === b.part;
    if (!same(key, hovered)) { setHighlight(key); }
    if (key) {
      tip.innerHTML = tipHtml(key); tip.hidden = false;
      const r = view.getBoundingClientRect();
      let x = e.clientX - r.left + 14, y = e.clientY - r.top + 14;
      if (x + 290 > r.width) x = Math.max(4, e.clientX - r.left - 294);
      if (y + tip.offsetHeight > r.height - 4) y = Math.max(4, e.clientY - r.top - tip.offsetHeight - 10);
      tip.style.left = x + 'px'; tip.style.top = y + 'px';
      renderer.domElement.style.cursor = (key.comp && ACTIONS[key.comp]) || key.part === 'SASH' ? 'pointer' : 'grab';
    } else { tip.hidden = true; renderer.domElement.style.cursor = 'grab'; }
  });
  renderer.domElement.addEventListener('pointerleave', () => { tip.hidden = true; setHighlight(null); });
  renderer.domElement.addEventListener('pointerdown', e => { downAt = [e.clientX, e.clientY]; });
  renderer.domElement.addEventListener('pointerup', e => {
    if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 5) return;
    const h = pick(e); if (!h) return;
    unlockAudio();
    const id = h.object.userData.comp;
    if (h.object.userData.keypad && h.uv) {
      const col = Math.min(3, Math.floor(h.uv.x * 4)), row = Math.min(3, Math.floor((1 - h.uv.y) * 4));
      pressKey(KEYS[row * 4 + col]);
    } else if (id && ACTIONS[id] && ACTIONS[id][1]) ACTIONS[id][1]();
    else if (h.object.userData.part === 'SASH') setWindow(!state.win);
  });

  // ------------------------------------------------------------------ simulation logic
  const logEl = $('#log');
  /**
   * Append an event to the log.
   * @param {string} text message  @param {boolean} alert red alert style
   * @returns {void}
   */
  function log(text, alert) {
    const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const d = document.createElement('div'); if (alert) d.className = 'al';
    d.innerHTML = `<b>${t}</b> ${text}`;
    logEl.prepend(d);
    while (logEl.children.length > 40) logEl.lastChild.remove();
  }

  /**
   * Show a temporary LCD message.
   * @param {string} l1 line 1  @param {string} l2 line 2  @param {number} ms duration
   * @returns {void}
   */
  function flash(l1, l2, ms) { state.msg = [l1, l2]; state.msgUntil = performance.now() + ms; }

  /**
   * Handle a keypad key.
   * @param {string} k key label
   * @returns {void}
   */
  function pressKey(k) {
    beep(1800, 0.04);
    if (/\d/.test(k)) { if (state.buf.length < 6) state.buf += k; flash('Enter code:', '*'.repeat(state.buf.length).padEnd(16), 4000); }
    else if (k === '*') { state.buf = ''; flash('Enter code:', 'cleared', 1200); }
    else if (k === '#') {
      if (state.buf === state.code) {
        openDoor();
      } else {
        flash('ACCESS DENIED', 'wrong code', 1800); log('Wrong door code entered'); beep(300, 0.35);
      }
      state.buf = '';
    } else { flash('Key ' + k, 'not assigned', 1000); }
    $('#codeShow').textContent = state.buf ? '•'.repeat(state.buf.length) : '––––';
  }

  /** Open the door for 5 s (servo to 90°). @returns {void} */
  function openDoor() {
    state.doorOpen = true; state.doorCloseAt = performance.now() + 5000;
    flash('ACCESS GRANTED', 'Door OPEN  5s', 1800); log('Correct code - door opened (auto-close 5 s)');
  }
  /** @param {boolean} on security armed @returns {void} */
  function setArmed(on) {
    state.armed = on;
    if (!on) { state.alarm = false; state.muted = false; state.motionUntil = 0; }
    log(on ? 'Security mode ARMED' : 'Security mode disarmed');
    flash('SECURITY', on ? 'ARMED' : 'DISARMED', 1300);
    syncUI();
  }
  /** @param {boolean} open window open @returns {void} */
  function setWindow(open) {
    state.win = open;
    log(open ? 'Window opened (reed contact open)' : 'Window closed');
    syncUI();
  }
  /** PIR event: exterior light for 10 s when armed. @returns {void} */
  function motion() {
    log('PIR: motion near the main door' + (state.armed ? ' - exterior light ON 10 s' : ' (ignored, disarmed)'));
    if (state.armed) state.motionUntil = performance.now() + 10000;
  }
  /** Mute and reset the alarm latch. @returns {void} */
  function mute() {
    if (state.alarm) { state.muted = true; log('Alarm muted by user'); }
    if (!state.win) { state.alarm = false; state.muted = false; }
    syncUI();
  }
  /** @param {boolean} on manual override @returns {void} */
  function setManual(on) { state.manual = on; log('Light override ' + (on ? 'ON' : 'off (auto)')); syncUI(); }

  // audio
  let actx = null, nextBeep = 0;
  /** Create the audio context after a user gesture. @returns {void} */
  function unlockAudio() { if (!actx) { try { actx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { actx = null; } } }
  /**
   * Short square-wave beep.
   * @param {number} f frequency Hz  @param {number} dur seconds
   * @returns {void}
   */
  function beep(f, dur) {
    if (!actx) return;
    const o = actx.createOscillator(), g = actx.createGain();
    o.type = 'square'; o.frequency.value = f; g.gain.value = 0.035;
    o.connect(g); g.connect(actx.destination); o.start(); o.stop(actx.currentTime + dur);
  }
  document.addEventListener('pointerdown', unlockAudio, { once: true });

  /**
   * One control-loop step (mirrors the planned Arduino loop()).
   * @param {number} now ms timestamp
   * @returns {void}
   */
  function control(now) {
    if (state.doorOpen && now > state.doorCloseAt) { state.doorOpen = false; log('Door auto-closed'); }
    if (state.armed && state.win && !state.alarm) {
      state.alarm = true; state.muted = false;
      log('INTRUSION - window opened while armed. Alert sent to recipients (ESP8266 → Telegram)', true);
    }
    if (state.armed && state.motionUntil && now > state.motionUntil) state.motionUntil = 0;
    const indoor = state.manual || state.amb < state.thr;
    const ext = state.armed && now < state.motionUntil;
    if (!state.fan && state.temp > state.set) { state.fan = true; log(`Fan ON (${state.temp.toFixed(1)} °C > ${state.set.toFixed(1)} °C)`); }
    else if (state.fan && state.temp < state.set - 0.5) { state.fan = false; log('Fan OFF'); }
    state.indoor = indoor; state.ext = ext;
    if (state.alarm && !state.muted && now > nextBeep) { beep(2600, 0.18); nextBeep = now + 450; }
  }

  /**
   * Render the 16x2 LCD (3D texture + HTML mirror).
   * @param {boolean} force redraw even when unchanged
   * @returns {void}
   */
  let lastLcd = '';
  function drawLCD(force) {
    const now = performance.now();
    let l1, l2;
    if (state.alarm) { l1 = '!! INTRUSION !!'; l2 = state.muted ? 'muted - close win' : 'ALERT SENT >ESP'; }
    else if (state.msg && now < state.msgUntil) { [l1, l2] = state.msg; }
    else if (state.page === 0) {
      l1 = `Door:${state.doorOpen ? 'OPEN  ' : 'CLOSED'} ${state.armed ? 'ARM' : 'OFF'}`;
      l2 = `T:${state.temp.toFixed(1)}C Set:${Math.round(state.set)}C`;
    } else {
      l1 = `Light:${state.indoor ? 'ON ' : 'OFF'} ${state.manual ? 'MAN' : 'AUTO'}`;
      l2 = `Fan:${state.fan ? 'ON ' : 'OFF'} Win:${state.win ? 'OPEN' : 'SHUT'}`;
    }
    l1 = (l1 || '').slice(0, 16).padEnd(16); l2 = (l2 || '').slice(0, 16).padEnd(16);
    const key = l1 + l2;
    if (key === lastLcd && !force) return;
    lastLcd = key;
    $('#lcdMirror').textContent = l1 + '\n' + l2;
    if (!lcdCanvas) return;
    const g = lcdCanvas.getContext('2d');
    g.fillStyle = '#1d3fbf'; g.fillRect(0, 0, 512, 128);
    const cw = 512 / 16;
    for (let r = 0; r < 2; r++) for (let i = 0; i < 16; i++) { g.fillStyle = 'rgba(255,255,255,.06)'; g.fillRect(i * cw + 2, r * 64 + 6, cw - 4, 52); }
    g.fillStyle = '#eef3ff'; g.font = '600 46px "JetBrains Mono", monospace'; g.textBaseline = 'middle'; g.textAlign = 'center';
    [l1, l2].forEach((l, r) => { for (let i = 0; i < 16; i++) g.fillText(l[i], i * cw + cw / 2, r * 64 + 34); });
    lcdTex.needsUpdate = true;
  }

  // ------------------------------------------------------------------ UI wiring
  const kpEl = $('#keypad');
  KEYS.forEach(k => {
    const b = document.createElement('button'); b.className = 'key' + (/[A-D]/.test(k) ? ' fn' : ''); b.textContent = k;
    b.addEventListener('click', () => pressKey(k));
    kpEl.appendChild(b);
  });
  $('#bArm').addEventListener('click', () => setArmed(!state.armed));
  $('#bWin').addEventListener('click', () => setWindow(!state.win));
  $('#bPir').addEventListener('click', motion);
  $('#bMute').addEventListener('click', mute);
  $('#bLight').addEventListener('click', () => setManual(!state.manual));
  $('#sAmb').addEventListener('input', e => { state.amb = +e.target.value; syncUI(); });
  $('#sTemp').addEventListener('input', e => { state.temp = +e.target.value; syncUI(); });
  $('#sSet').addEventListener('input', e => { state.set = +e.target.value; syncUI(); });
  window.addEventListener('keydown', e => {
    if (e.target.closest && e.target.closest('input,textarea')) return;
    const k = e.key === 'Enter' ? '#' : e.key === 'Backspace' ? '*' : e.key.toUpperCase();
    if (KEYS.includes(k) && /[\d#*]/.test(k)) pressKey(k);
  });

  /** Sync side-rail controls and chips with the state. @returns {void} */
  function syncUI() {
    const a = $('#bArm'); a.setAttribute('aria-pressed', String(state.armed)); a.textContent = state.armed ? 'ARMED' : 'Disarmed';
    const w = $('#bWin'); w.setAttribute('aria-pressed', String(state.win)); w.textContent = state.win ? 'Open' : 'Closed';
    const l = $('#bLight'); l.setAttribute('aria-pressed', String(state.manual)); l.textContent = state.manual ? 'Manual ON' : 'Auto';
    $('#vAmb').textContent = `${state.amb} %  (thr ${state.thr} %)`;
    $('#vTemp').textContent = `${state.temp.toFixed(1)} °C`;
    $('#vSet').textContent = `${state.set.toFixed(1)} °C`;
  }
  let lastChips = '';
  /** Update status chips. @returns {void} */
  function chips() {
    const c = [
      ['Door ' + (state.doorOpen ? 'OPEN' : 'closed'), state.doorOpen],
      ['Security ' + (state.armed ? 'ARMED' : 'off'), state.armed],
      ['Window ' + (state.win ? 'OPEN' : 'shut'), state.win],
      ['Ext light ' + (state.ext ? 'ON' : 'off'), state.ext],
      ['Indoor ' + (state.indoor ? 'ON' : 'off'), state.indoor],
      ['Fan ' + (state.fan ? 'ON' : 'off'), state.fan]
    ];
    const html = (state.alarm ? '<span class="chip alarm">ALARM' + (state.muted ? ' (muted)' : '') + '</span>' : '') +
      c.map(([t, on]) => `<span class="chip${on ? ' on' : ''}">${t}</span>`).join('');
    if (html !== lastChips) { $('#chips').innerHTML = html; lastChips = html; }
  }

  $('#varA').addEventListener('click', () => setVariant('A'));
  $('#varB').addEventListener('click', () => setVariant('B'));
  /** @param {string} v variant key @returns {void} */
  function setVariant(v) {
    state.variant = v;
    $('#varA').setAttribute('aria-pressed', String(v === 'A')); $('#varB').setAttribute('aria-pressed', String(v === 'B'));
    hovered = null; buildVariant(v);
  }
  $$('[data-view]').forEach(b => b.addEventListener('click', () => goView(b.dataset.view)));
  /**
   * Wire a toolbar toggle button.
   * @param {string} id element id  @param {string} key state key  @param {Function} fn side effect
   * @returns {void}
   */
  function toggle(id, key, fn) {
    $(id).addEventListener('click', () => { state[key] = !state[key]; $(id).setAttribute('aria-pressed', String(state[key])); fn && fn(); });
  }
  toggle('#tDims', 'dims', () => { build.dims.visible = state.dims; });
  toggle('#tLabels', 'labels', () => { $$('.lbl3d').forEach(e => e.remove()); labelEls.length = 0; if (state.labels) buildLabels(); });
  toggle('#tXray', 'xray', applyXray);
  toggle('#tRoof', 'roofOpen');
  $('#tOrtho').addEventListener('click', () => setOrtho(!orthoMode));
  $('#explode').addEventListener('input', e => { state.explode = +e.target.value / 100; });

  // legend
  $('#legend').innerHTML = Object.keys(CAT).map(k => `<span class="legend"><span class="dot" style="background:var(--c-${k})"></span>${CAT[k]}</span>`).join('');

  // tabs
  $$('.tab').forEach(t => t.addEventListener('click', () => {
    $$('.tab').forEach(x => x.setAttribute('aria-selected', String(x === t)));
    $$('.pane').forEach(p => { p.hidden = p.id !== 'pane-' + t.dataset.tab; });
  }));

  // ------------------------------------------------------------------ panes
  /** Render the laser panel drawings for the current variant. @returns {void} */
  function renderPanels() {
    const V = D.variants[state.variant];
    const cards = V.parts.map(p => {
      const feats = V.features[p.id] || [];
      const rows = feats.map(f => `<tr><td>${f.label}</td><td class="m">${f.size}</td><td class="m">${f.pts.map(q => `(${q[0]}, ${q[1]})`).join(' ')}</td></tr>`).join('');
      return `<article class="pcard" data-part="${p.id}"><header><h3>${p.name}</h3><span class="id">${p.id.toLowerCase()}_x${p.qty}.dxf</span></header>
        <div class="mono" style="font-size:12.5px">${p.size[0]} × ${p.size[1]} mm · qty ${p.qty}</div>
        ${V.drawings[p.id]}
        ${rows ? `<details class="feat"><summary>${feats.length} feature${feats.length > 1 ? 's' : ''} · centres from bottom-left, as cut</summary><table class="ftab"><thead><tr><th>Feature</th><th>Size</th><th>Centre (x, y)</th></tr></thead><tbody>${rows}</tbody></table></details>` : ''}
      </article>`;
    }).join('');
    const sheets = V.sheet_svgs.map((s, i) => `<article class="pcard"><header><h3>Sheet ${i + 1} of ${V.sheets}</h3><span class="id">sheet_${i + 1}_of_${V.sheets}_600x400.dxf</span></header>${s}</article>`).join('');
    $('#pane-panels').innerHTML = `
      <div class="stats">
        <div><b>${V.parts.reduce((a, p) => a + p.qty, 0)}</b><span>parts (${V.parts.length} designs)</span></div>
        <div><b>${V.sheets}</b><span>MDF sheets 600 × 400 × 3</span></div>
        <div><b>${V.area_m2} m²</b><span>net part area</span></div>
        <div><b>${V.cut_m} m</b><span>cut length</span></div>
        <div><b>${P.finger} mm</b><span>finger pitch (7 per corner)</span></div>
      </div>
      <div class="callout prose" style="margin-bottom:12px"><b>Before cutting:</b> measure your MDF with calipers. Slots are cut at ${(P.T + 0.1).toFixed(1)} mm for ${P.T} mm sheet. If the sheet measures 2.8 or 3.2 mm, change <span class="mono">T</span> in <span class="mono">house_geometry.py</span> and run it again. Red lines are the <span class="mono">CUT</span> layer. Dashed blue lines are the <span class="mono">ENGRAVE</span> layer (front-wall labels, keypad outline, and the team name plate on the base underside; the base is drawn as seen from below on purpose). Text is already converted to outlines, so any laser software reads it. The DXF files are in your <span class="mono">smart home/laser_dxf</span> folder.</div>
      <h2 style="margin:6px 0 10px">Nested sheets</h2>
      <div class="grid-panels">${sheets}</div>
      <h2 style="margin:18px 0 10px">Parts (as cut, outside face up)</h2>
      <div class="grid-panels">${cards}</div>`;
  }

  /** Render BOM grouped by class. @returns {void} */
  function renderBom() {
    const V = D.variants[state.variant];
    const order = ['sensor', 'actuator', 'processing', 'interface', 'power', 'mech'];
    const comps = D.components.slice().filter(c => !/^inled[23]$/.test(c.id)).sort((a, b) => order.indexOf(a.cat) - order.indexOf(b.cat));
    const rows = comps.map(c => `<tr data-comp="${c.id}"><td><b>${c.id === 'inled1' ? 'Indoor light LEDs (×3)' : c.name}</b></td><td><span class="cls"><span class="dot" style="background:var(--c-${c.cat})"></span>${CAT[c.cat]}</span></td><td>${c.func}</td><td>${c.where}</td><td class="m">${c.dims}</td><td><span class="stat ${c.owned ? 'own' : 'buy'}">${c.owned ? 'in kit' : 'buy'}</span></td></tr>`).join('');
    const mech = V.parts.map(p => `<tr data-part="${p.id}"><td><b>${p.name}</b></td><td><span class="cls"><span class="dot" style="background:var(--c-mech)"></span>Mechanical</span></td><td>${PART_FN[p.id] || ''}</td><td>Structure</td><td class="m">${p.size[0]} × ${p.size[1]} × ${P.T} · qty ${p.qty}</td><td><span class="stat own">MDF 3 mm</span></td></tr>`).join('');
    const hw = HARDWARE[state.variant].map(h => `<tr><td><b>${h[0]}</b></td><td><span class="cls"><span class="dot" style="background:var(--c-mech)"></span>Mechanical</span></td><td>${h[1]}</td><td>${h[2]}</td><td class="m">${h[3]}</td><td><span class="stat buy">buy</span></td></tr>`).join('');
    $('#pane-bom').innerHTML = `<p class="prose foot">Bill of material classified as the report asks (sensor, actuator, information processing, mechanical). Hover a row to highlight the part in the 3D model.</p>
      <div class="tablewrap"><table class="bom"><thead><tr><th>Item</th><th>Class</th><th>Function</th><th>Location</th><th>Size / material</th><th>Status</th></tr></thead><tbody>${rows}${mech}${hw}</tbody></table></div>`;
    $$('#pane-bom tr[data-comp], #pane-bom tr[data-part]').forEach(tr => {
      tr.addEventListener('mouseenter', () => setHighlight(tr.dataset.comp ? { comp: tr.dataset.comp } : { part: tr.dataset.part }));
      tr.addEventListener('mouseleave', () => setHighlight(null));
    });
  }
  const PART_FN = {
    BASE: 'Floor + mounting plate; slots locate every wall, Arduino standoff holes, door pivot hole', FRONT: 'Door, keypad, LCD, PIR, exterior light, control column',
    BACK: 'USB / DC access, aux 5 V jack, vents' + '', LEFT: 'Exhaust fan opening', RIGHT: 'Window, LDR, reed switch',
    PARTITION: 'Separates the electronics bay; carries indoor LEDs and DHT11', FANPLATE: 'Holds the F130 motor (D-hole)', FANRIB: 'Fan duct sides, stiffen the plate',
    SHELF: 'Holds the inverted SG90 above the door hinge', DOOR: 'Main door, driven by the servo horn', SASH: 'Hinged window frame; carries the MC-38 magnet',
    ROOF: 'Gable roof slopes (score-engraved shingles)', TRUSS: 'Keep the roof square and locate it on the walls', LID: 'Removable flat roof',
    LOCATOR: 'Corner locators: register the lid inside the walls', KNOB: 'Lift knob (2 discs glued)'
  };
  const HARDWARE = {
    A: [['Mini hinge 25 mm ×3', 'Roof (2) and window (1)', 'Back eave, window', 'brass + M2 screws'], ['M3 standoffs ×4 + screws', 'Arduino mount', 'Base', 'M3 × 6 mm'], ['M3 screws + nuts ×4', 'LCD mount', 'Front wall', 'M3 × 10'], ['Wood glue (PVA) + hot glue', 'Joints, LEDs, sensors', '-', '-']],
    B: [['Mini hinge 25 mm ×1', 'Window', 'Right wall', 'brass + M2 screws'], ['M3 standoffs ×4 + screws', 'Arduino mount', 'Base', 'M3 × 6 mm'], ['M3 screws + nuts ×4', 'LCD mount', 'Front wall', 'M3 × 10'], ['Wood glue (PVA) + hot glue', 'Joints, LEDs, sensors', '-', '-']]
  };

  /** Render pin map, assembly and progress panes (static). @returns {void} */
  function renderStatic() {
    const pins = [
      ['D2', 'MC-38 reed (window)', 'INPUT_PULLUP (interrupt), HIGH = open', 'Security'], ['D3', 'PIR HC-SR501 OUT', 'INPUT (interrupt)', 'Security'],
      ['D4', 'DHT11 data', 'INPUT (module has pull-up)', 'Climate'], ['D5', 'Fan driver base (1 kΩ → TIP120)', 'OUTPUT / PWM', 'Climate'],
      ['D6', 'Light override button', 'INPUT_PULLUP', 'Lighting'], ['D7', 'ARM toggle switch', 'INPUT_PULLUP', 'Security'],
      ['D8', 'Buzzer', 'OUTPUT (tone)', 'Security'], ['D9', 'Servo SG90 signal', 'Servo lib (Timer1)', 'Door'],
      ['D10', 'Exterior LED (220 Ω)', 'OUTPUT (digital only, Timer1 used by servo)', 'Security'], ['D11', 'Indoor LEDs ×3 (220 Ω each, or via 2N2222)', 'OUTPUT', 'Lighting'],
      ['D12', 'Alarm mute button', 'INPUT_PULLUP', 'Security'], ['D13', 'Spare / status', '-', '-'],
      ['A0', 'LDR + 10 kΩ divider', 'analogRead', 'Lighting'], ['A1', 'Pot 10 kΩ wiper (set-point)', 'analogRead → 20–40 °C', 'Climate'],
      ['A4 / A5', 'I2C bus: LCD backpack 0x27 + PCF8574 keypad 0x20', 'Wire', 'UI / Door'], ['D1 (TX)', 'ESP8266 RX via 1k/2k divider', 'Serial 9600, one-way alerts', 'Security'],
      ['5V aux', 'Servo V+, fan motor V+ (5 V 2 A adapter)', 'common GND with UNO', 'Power']
    ];
    $('#pane-pins').innerHTML = `<div class="two"><div class="tablewrap"><table class="bom" style="min-width:560px"><thead><tr><th>Pin</th><th>Connected to</th><th>Mode</th><th>Subsystem</th></tr></thead><tbody>${pins.map(r => `<tr><td class="m"><b>${r[0]}</b></td><td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td></tr>`).join('')}</tbody></table></div>
      <div class="prose"><div class="callout"><b>Pin budget.</b> Wired directly, the 4×4 keypad needs 8 pins and the full system needs about 20, but the UNO has 16 free (A4/A5 are taken by I2C). A <b>PCF8574 I2C module</b> (about 60 EGP) puts the keypad on the same two wires as the LCD and frees 8 pins. That is the layout shown here.<br><br>Without it, you can read buttons + toggle through one analog resistor ladder and drop the A–D keypad column. It works but is tight.</div>
      <h3 style="margin:14px 0 6px">Driver notes</h3><ul class="tight"><li>F130 draws 150–400 mA, so never drive it from a pin. Use TIP120 (or 2N2222 at light load), a 1 kΩ base resistor, and a 1N4007 across the motor.</li><li>SG90 stall current spikes reset the UNO on USB power. Feed the servo and fan from the 5 V 2 A rail and tie the grounds together.</li><li>LDR divider: LDR from 5 V to A0, 10 kΩ from A0 to GND. Brighter light gives a higher reading.</li><li>ESP8266 is 3.3 V. Divide the UNO TX with 1 kΩ / 2 kΩ and power it from a 3.3 V regulator (an ESP-01 adapter board has one).</li></ul></div></div>`;
    $('#pane-build').innerHTML = `<div class="two"><div class="prose"><h2 style="margin-bottom:10px">Assembly order</h2><ol class="steps">
      <li><b>Measure the MDF</b> and set <span class="mono">T</span> if needed. Cut the 2 sheets. Ask for CUT at full power and ENGRAVE as a light score.</li>
      <li><b>Dry-fit everything</b> before glue: walls into the base slots, corner fingers, partition tabs through the side walls.</li>
      <li><b>Glue the shell:</b> the base is cut upside down, so its engraved face (the team name plate) goes <b>down</b>. Glue front + left, then right, then back, onto it. Check the diagonals are equal (square) and clamp with tape for 20 min.</li>
      <li><b>Inner parts:</b> partition, fan ribs + fan plate (duct), servo shelf (its tabs lock into the front wall above the door).</li>
      <li><b>Front wall hardware:</b> LCD on 4× M3, keypad sticker on the engraved outline (ribbon through the slot), PIR dome through Ø23.5, LED, buttons on a small perfboard, toggle + pot with their nuts.</li>
      <li><b>Door:</b> drop a Ø2 pin under the hinge corner into the base hole. Seat the inverted SG90 in the shelf and glue the single-arm horn to the door top. Set the servo to 0° first.</li>
      <li><b>Window:</b> mini hinge on the front edge, acrylic glued behind the frame. MC-38 reed on the wall, magnet on the sash, gap under 10 mm. Wires go through the Ø5 hole.</li>
      <li><b>Left wall fan:</b> F130 press-fit in the D-hole, prop on the shaft (spins inside the Ø62 opening, blowing outwards).</li>
      <li><b>Electronics bay:</b> UNO on standoffs (USB aligned with the back-wall hole), breadboard on the engraved outline, aux 5 V jack in the back wall.</li>
      <li><b>Wiring:</b> route along the floor through the two partition notches. Heat-shrink every joint, label both ends, and bundle with ties. Neat wiring is worth 10 %.</li>
      <li><b>Roof:</b> ${'A: glue the two slopes onto the 2 trusses, then fix 2 mini hinges on the engraved marks at the back eave. The roof opens about 70°; add a small stay. B: put the lid on the walls, slide the 4 corner locators under it into the inside corners, glue them to the lid, then glue the 2-disc knob on top.'}</li></ol></div>
      <div class="prose"><h2 style="margin-bottom:10px">Design decisions</h2><ul class="tight">
      <li><b>Electronics bay behind a partition</b> (75 mm deep) keeps the living room clean and the wiring hidden, and the USB port stays reachable from outside.</li>
      <li><b>Finger joints + tab/slot base</b> make the box self-squaring, so it needs no screws and stays rigid (Robust assembly, 10 %).</li>
      <li><b>LDR outside on the right wall</b>, so the indoor LEDs can't light their own sensor and make the light flicker on and off.</li>
      <li><b>DHT11 near the fan duct</b>, so the demo is quick: warm the sensor and the fan reacts.</li>
      <li><b>Window opens outward on a hinge</b> with the reed switch beside its free edge. A 10 mm opening already breaks the contact.</li>
      <li><b>Servo shaft on the door hinge axis</b>, so the door is driven directly and needs no linkage. It opens inward by 90°.</li>
      <li>Variant A looks more like a house and the hinged roof gives full access. Variant B nests on 2 sheets, has the least cutting, is quicker to build, and lifts straight off.</li></ul></div></div>`;
    $('#pane-prog').innerHTML = `<div class="two"><div class="prose"><h2 style="margin-bottom:8px">Progress session · 21–22 Oct</h2>
      <p>The TA asked for (1) the home structure, presentable and engineering grade, and (2) a working window intrusion alert sent to the designated recipients.</p>
      <ul class="tight check"><li>House cut, glued and square, with all openings matching the parts</li><li>Arduino, breadboard and LCD mounted and powered</li><li>MC-38 on the window with the security toggle wired</li><li>Armed + window opened → buzzer + LCD “INTRUSION” + message to the recipient</li><li>Recipient alert: ESP8266 sends a Telegram bot message (or a Firebase push) when the UNO prints <span class="mono">ALERT:WINDOW</span> on serial</li><li>Bring the BOM and the CAD views from this page (front, side, top, iso)</li></ul></div>
      <div class="callout prose"><b>Not on your receipt, but needed:</b><ul class="tight" style="margin-top:6px">
      <li>PIR HC-SR501 (motion near the door)</li><li>10 kΩ potentiometer, panel type, with knob (temperature set-point)</li><li>10 kΩ resistor for the LDR divider (you only bought 220 Ω)</li><li>TIP120 or 2N2222 + 1N4007 + 1 kΩ (fan driver)</li><li>PCF8574 I2C module (keypad, see Pin map)</li><li>ESP8266 (ESP-01 + adapter, or NodeMCU) for the recipient alert</li><li>5 V 2 A adapter + panel DC jack</li><li>4× M3 standoffs, M3 screws, mini hinges, PVA glue, 2 mm acrylic (optional)</li></ul></div></div>`;
  }

  // ------------------------------------------------------------------ animation loop
  const clock = new THREE.Clock();
  /**
   * Ease a value towards a target at a constant rate.
   * @param {number} cur current  @param {number} target target  @param {number} rate units/s  @param {number} dt seconds
   * @returns {number}
   */
  function approach(cur, target, rate, dt) { const d = target - cur; const s = rate * dt; return Math.abs(d) <= s ? target : cur + Math.sign(d) * s; }

  /** Per-frame update. @returns {void} */
  function frame() {
    requestAnimationFrame(frame);
    const dt = Math.min(clock.getDelta(), 0.05), now = performance.now();
    control(now);
    state.pageT += dt; if (state.pageT > 3) { state.pageT = 0; state.page = 1 - state.page; }
    drawLCD(false); chips();
    $('#clock').textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    if (build) {
      state.doorAng = approach(state.doorAng, state.doorOpen ? Math.PI / 2 : 0, 2.2, dt);
      build.pivots.door.pv.rotation.z = state.doorAng;
      state.winAng = approach(state.winAng, state.win ? 1.15 : 0, 2.5, dt);
      build.pivots.sash.pv.rotation.z = -state.winAng;
      if (state.variant === 'A') {
        state.roofAng = approach(state.roofAng, state.roofOpen ? 1.2 : 0, 1.4, dt);
        build.pivots.roof.pv.rotation.x = -state.roofAng; build.pivots.roof.pv.position.z = P.H;
      } else {
        state.roofAng = approach(state.roofAng, state.roofOpen ? 1 : 0, 1.8, dt);
        build.pivots.roof.pv.rotation.x = 0;
        build.pivots.roof.pv.position.z = P.H + state.roofAng * 110;
      }
      state.propSpeed = approach(state.propSpeed, state.fan ? 38 : 0, 30, dt);
      if (build.prop) build.prop.rotation.x += state.propSpeed * dt;
      if (build.toggle) build.toggle.rotation.x = state.armed ? -0.5 : 0.5;
      if (build.pot) build.pot.rotation.y = (state.set - 30) / 10 * 2.2;
      build.leds.forEach(l => {
        const on = l.kind === 'ext' ? state.ext : state.indoor;
        l.m.emissive.setHex(on ? 0xfff2cc : 0x000000); l.m.emissiveIntensity = on ? 1.2 : 0;
        l.glow.material.opacity = on ? 0.9 : 0; l.light.intensity = on ? 1.1 : 0;
      });
      if (build.buzzer) build.buzzer.material.emissive.setHex(state.alarm && !state.muted && Math.floor(now / 225) % 2 ? 0xb00000 : 0x000000);
      Object.values(build.groups).forEach(g => g.position.copy(g.userData.dir).multiplyScalar(state.explode));
    }
    if (tween) {
      const k = Math.min(1, (now - tween.s) / tween.dur), e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      cam.position.lerpVectors(tween.p0, tween.p1, e); ctl.target.lerpVectors(tween.t0, tween.t1, e);
      if (k >= 1) tween = null;
    }
    ctl.update();
    renderer.render(scene, cam);
    updateLabels();
  }

  // ------------------------------------------------------------------ boot
  const labelsReady = () => { applyTheme(); };
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', labelsReady);
  new MutationObserver(() => { applyTheme(); if (build) { root.remove(build.dims); build.dims = buildDims(state.variant); build.dims.visible = state.dims; root.add(build.dims); renderPanels(); } })
    .observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  resize();
  applyTheme();
  renderStatic();
  setVariant('B');
  const a0 = view.clientWidth / Math.max(1, view.clientHeight);
  persp.position.set(0, 95, 0).add(new THREE.Vector3(...VIEWS.iso.dir).normalize().multiplyScalar(900 * (a0 < 1.25 ? 1.25 / a0 : 1)));
  ctlP.update();
  syncUI();
  log('System boot - default code 1234');
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { if (build) { root.remove(build.dims); build.dims = buildDims(state.variant); build.dims.visible = state.dims; root.add(build.dims); } drawLCD(true); });
  window.__sim = { state, pressKey, setArmed, setWindow, motion, goView, setVariant };
  frame();
})();
