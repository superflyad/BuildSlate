import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import "./style.css";

const colors = {
  exterior: 0x99a8bd,
  display: 0x182d42,
  power: 0xe5b861,
  pcb: 0x3dba9b,
  camera: 0xaa85dd,
  audio: 0x83a7db,
  thermal: 0xee806d,
  compute: 0x6ca6fa,
  memory: 0x8797ee,
  storage: 0xc38bca,
  radio: 0x62c9c1,
  deferred: 0x7d8799,
};
const labels = {
  exterior: "Exterior",
  display: "Display",
  power: "Power",
  pcb: "Circuit board",
  camera: "Camera",
  audio: "Audio",
  thermal: "Thermal",
  compute: "Compute",
  memory: "Memory",
  storage: "Storage",
  radio: "Radio",
  deferred: "Deferred",
};
const groups = Object.keys(labels);
const state = {
  assembly: null,
  selected: null,
  search: "",
  activeGroup: null,
  shell: true,
  keepouts: false,
  deferred: false,
  explode: 0,
  tab: "inspect",
};
const meshes = new Map();
const baseZ = new Map();
const keepoutMeshes = [];
const viewport = document.querySelector("#viewport");
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x101d2b);
const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 2000);
camera.up.set(0, 0, 1);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
viewport.append(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.minDistance = 80;
controls.maxDistance = 650;
controls.target.set(90, 47.5, 4.75);
camera.position.set(250, -185, 145);
controls.update();
scene.add(new THREE.HemisphereLight(0xe8f2ff, 0x34485a, 2.5));
const keyLight = new THREE.DirectionalLight(0xffffff, 2.8);
keyLight.position.set(80, -50, 180);
scene.add(keyLight);
const rimLight = new THREE.DirectionalLight(0x82a9ed, 1.3);
rimLight.position.set(-120, 150, 80);
scene.add(rimLight);
const ground = new THREE.GridHelper(280, 14, 0x385067, 0x23374a);
ground.rotation.x = Math.PI / 2;
ground.position.set(90, 47.5, -8);
scene.add(ground);
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
let selectionBox = null;

function resize() {
  const { width, height } = viewport.getBoundingClientRect();
  if (!width || !height) return;
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
}
new ResizeObserver(resize).observe(viewport);
function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}
animate();

function esc(text) {
  return String(text ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
}
function textBox(box) {
  return `${box[3]} × ${box[4]} × ${box[5]} mm`;
}
function filteredParts() {
  return state.assembly.parts.filter(
    (p) =>
      (!state.activeGroup || p.group === state.activeGroup) &&
      (!state.search ||
        `${p.label} ${p.group} ${p.id}`.toLowerCase().includes(state.search)),
  );
}
function renderGroups() {
  const counts = Object.fromEntries(
    groups.map((group) => [
      group,
      state.assembly.parts.filter((p) => p.group === group).length,
    ]),
  );
  document.querySelector("#groups").innerHTML = groups
    .filter((g) => counts[g])
    .map(
      (group) =>
        `<button class="group-item ${state.activeGroup === group ? "selected" : ""}" data-group="${group}" type="button"><span class="swatch" style="--swatch:#${colors[group].toString(16).padStart(6, "0")}"></span><span>${labels[group]}</span><span class="group-count">${counts[group]}</span></button>`,
    )
    .join("");
  document.querySelectorAll("[data-group]").forEach((button) =>
    button.addEventListener("click", () => {
      state.activeGroup =
        state.activeGroup === button.dataset.group
          ? null
          : button.dataset.group;
      updateVisibility();
      renderGroups();
      renderParts();
    }),
  );
}
function renderParts() {
  const parts = filteredParts();
  document.querySelector("#part-count").textContent = `${parts.length} parts`;
  document.querySelector("#parts").innerHTML =
    parts
      .map(
        (p) =>
          `<button class="part-item ${state.selected === p.id ? "selected" : ""}" data-part="${p.id}" type="button"><span class="part-color" style="--swatch:#${colors[p.group].toString(16).padStart(6, "0")}"></span><span class="part-copy"><strong>${esc(p.label)}</strong><small>${esc(labels[p.group])} · ${esc(p.evidence_class.replaceAll("_", " "))}</small></span>${p.active ? "" : '<span class="part-deferred">OFF</span>'}</button>`,
      )
      .join("") || '<p class="empty-list">No components match.</p>';
  document
    .querySelectorAll("[data-part]")
    .forEach((button) =>
      button.addEventListener("click", () => selectPart(button.dataset.part)),
    );
}
function renderDetail() {
  const part = state.assembly.parts.find((p) => p.id === state.selected);
  if (!part) return;
  document.querySelector("#part-detail").className = "detail-body";
  document.querySelector("#part-detail").innerHTML =
    `<div class="eyebrow">${esc(labels[part.group])} / ${esc(part.id)}</div><div class="detail-title-row"><h2>${esc(part.label)}</h2><span class="swatch large" style="--swatch:#${colors[part.group].toString(16).padStart(6, "0")}"></span></div><div class="detail-status">${part.active ? "In current planning model" : "Deferred from current build"}</div><div class="section-heading">Geometry</div><div class="property"><span>Envelope</span><strong>${textBox(part.box_mm)}</strong></div><div class="property"><span>Origin (x, y, z)</span><strong>${part.box_mm.slice(0, 3).join(", ")} mm</strong></div><div class="property"><span>Geometry type</span><strong>Provisional box</strong></div><div class="section-heading">Engineering basis</div><div class="property"><span>Evidence class</span><strong>${esc(part.evidence_class.replaceAll("_", " "))}</strong></div><div class="source-path"><span>Source</span><code>${esc(part.source)}</code></div>${part.notes ? `<div class="detail-note">${esc(part.notes.replaceAll("_", " "))}</div>` : ""}<p class="detail-caveat">This box is a planning envelope. Verify against supplier CAD and released drawings before treating it as a physical part.</p>`;
}
function renderProgram() {
  const { summary, gates, blockers } = state.assembly;
  const summaryItems = [
    ["Verified", summary.verified],
    ["Available", summary.available_not_verified],
    ["Modeled", summary.modeled_not_verified],
    ["Blockers", summary.external_blockers],
  ];
  document.querySelector("#program-summary").innerHTML = summaryItems
    .map(
      ([label, value]) =>
        `<div><strong>${value}</strong><span>${label}</span></div>`,
    )
    .join("");
  const coverage = state.assembly.component_coverage;
  const counts = Object.fromEntries(
    ["box", "aggregate", "deferred", "unplaced"].map((kind) => [
      kind,
      coverage.filter((c) => c.representation === kind).length,
    ]),
  );
  document.querySelector("#coverage").innerHTML =
    `<p class="coverage-intro">${coverage.length} library roles · ${counts.box} box modeled · ${counts.aggregate} aggregate · ${counts.deferred} deferred · ${counts.unplaced} unplaced</p>` +
    coverage
      .filter((c) => c.representation === "unplaced")
      .map(
        (c) =>
          `<div class="coverage-item"><strong>${esc(c.id.replaceAll("_", " "))}</strong><span>No geometry or placement</span></div>`,
      )
      .join("");
  document.querySelector("#zones").innerHTML = Object.entries(
    state.assembly.zones,
  )
    .map(([id, zone]) => {
      const layers = zone.layers || zone.additional_layers || [];
      const total = layers.reduce(
        (sum, layer) => sum + Number(layer.thickness_mm || 0),
        0,
      );
      return `<details class="blocker-item"><summary>${esc(id.replaceAll("_", " "))}</summary><p>${zone.inherits ? `Additional layers on ${esc(zone.inherits.replaceAll("_", " "))}` : `${layers.length} layers · ${total.toFixed(2)} mm nominal sum`}</p><div class="zone-layers">${layers.map((layer) => `<div><span>${esc(layer.id.replaceAll("_", " "))}</span><strong>${layer.thickness_mm} mm</strong></div>`).join("")}</div></details>`;
    })
    .join("");
  document.querySelector("#gates").innerHTML = gates
    .map(
      (g) =>
        `<div class="gate-item"><strong>${esc(g.id.replaceAll("_", " "))}</strong><span>${esc(g.status.replaceAll("_", " "))}</span></div>`,
    )
    .join("");
  document.querySelector("#blockers").innerHTML = blockers
    .map(
      (b, i) =>
        `<details class="blocker-item"><summary><span>${i + 1}</span>${esc(b.id.replaceAll("_", " "))}</summary><p>${esc(b.missing_evidence)}</p><small>Next: ${esc(b.exact_next_action)}</small></details>`,
    )
    .join("");
}
function updateVisibility() {
  for (const part of state.assembly.parts) {
    const mesh = meshes.get(part.id);
    if (!mesh) continue;
    mesh.visible =
      (!state.activeGroup || part.group === state.activeGroup) &&
      (state.shell || part.group !== "exterior") &&
      (state.deferred || part.active);
    const spread =
      {
        exterior: 2.8,
        display: 1.9,
        pcb: -0.5,
        compute: 0.7,
        memory: 0.9,
        storage: 0.8,
        power: -1.3,
        camera: -1.7,
        audio: -1.9,
        thermal: 1.1,
        radio: 0.6,
        deferred: -2.1,
      }[part.group] || 0;
    mesh.position.z = baseZ.get(part.id) + spread * state.explode * 9;
    mesh.material.opacity =
      part.id === state.selected
        ? 1
        : part.group === "exterior"
          ? 0.38
          : part.group === "display"
            ? 0.78
            : 0.94;
    mesh.material.transparent = mesh.material.opacity < 1;
    mesh.material.depthWrite = mesh.material.opacity >= 1;
  }
  keepoutMeshes.forEach((mesh) => {
    mesh.visible = state.keepouts;
  });
  if (selectionBox) selectionBox.update();
}
function selectPart(id) {
  state.selected = id;
  state.tab = "inspect";
  setTab();
  renderParts();
  renderDetail();
  updateVisibility();
  if (selectionBox) scene.remove(selectionBox);
  const mesh = meshes.get(id);
  if (mesh) {
    selectionBox = new THREE.BoxHelper(mesh, 0xffd47b);
    scene.add(selectionBox);
  }
}
function setTab() {
  for (const tab of ["inspect", "program"]) {
    document
      .querySelector(`#tab-${tab}`)
      .classList.toggle("active", state.tab === tab);
    document
      .querySelector(`#tab-${tab}`)
      .setAttribute("aria-selected", String(state.tab === tab));
    document
      .querySelector(`#${tab}-panel`)
      .classList.toggle("hidden", state.tab !== tab);
  }
}
function setView(view) {
  const target = new THREE.Vector3(90, 47.5, 4.75);
  const delta = {
    iso: [160, -175, 125],
    front: [0, 0, 240],
    rear: [0, 0, -240],
    side: [250, 0, 0],
  }[view];
  camera.position.set(
    target.x + delta[0],
    target.y + delta[1],
    target.z + delta[2],
  );
  controls.target.copy(target);
  controls.update();
  document
    .querySelectorAll("[data-view]")
    .forEach((button) =>
      button.classList.toggle("active", button.dataset.view === view),
    );
}
function makeKeepouts() {
  for (const zone of state.assembly.keepouts) {
    const r = zone.rectangle_mm;
    const geometry = new THREE.BoxGeometry(r.length, r.width, 0.22);
    const material = new THREE.MeshBasicMaterial({
      color: 0xfa9b63,
      transparent: true,
      opacity: 0.25,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(r.x + r.length / 2, r.y + r.width / 2, 7.8);
    scene.add(mesh);
    keepoutMeshes.push(mesh);
    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(geometry),
      new THREE.LineBasicMaterial({
        color: 0xf2ae7e,
        transparent: true,
        opacity: 0.7,
      }),
    );
    mesh.add(edges);
  }
}
renderer.domElement.addEventListener("click", (event) => {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.set(
    ((event.clientX - rect.left) / rect.width) * 2 - 1,
    -((event.clientY - rect.top) / rect.height) * 2 + 1,
  );
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObjects(
    [...meshes.values()].filter((mesh) => mesh.visible),
    false,
  );
  if (hits.length) selectPart(hits[0].object.userData.partId);
});
document.querySelector("#part-search").addEventListener("input", (event) => {
  state.search = event.target.value.trim().toLowerCase();
  renderParts();
});
document.querySelector("#show-all").addEventListener("click", () => {
  state.activeGroup = null;
  state.search = "";
  document.querySelector("#part-search").value = "";
  updateVisibility();
  renderGroups();
  renderParts();
});
document.querySelector("#explode").addEventListener("input", (event) => {
  state.explode = Number(event.target.value) / 100;
  document.querySelector("#explode-value").textContent =
    `${event.target.value}%`;
  updateVisibility();
});
for (const [id, key] of [
  ["shell-toggle", "shell"],
  ["keepouts-toggle", "keepouts"],
  ["deferred-toggle", "deferred"],
])
  document.querySelector(`#${id}`).addEventListener("change", (event) => {
    state[key] = event.target.checked;
    updateVisibility();
  });
document
  .querySelectorAll("[data-view]")
  .forEach((button) =>
    button.addEventListener("click", () => setView(button.dataset.view)),
  );
for (const tab of ["inspect", "program"])
  document.querySelector(`#tab-${tab}`).addEventListener("click", () => {
    state.tab = tab;
    setTab();
  });

try {
  const response = await fetch("/assembly.json");
  if (!response.ok) throw new Error(`assembly data: HTTP ${response.status}`);
  state.assembly = await response.json();
  const gltf = await new GLTFLoader().loadAsync("/assembly.gltf");
  gltf.scene.traverse((object) => {
    if (!object.isMesh) return;
    const id =
      object.parent?.userData?.part_id ||
      object.userData.part_id ||
      object.parent?.name ||
      object.name;
    const part = state.assembly.parts.find((p) => p.id === id);
    if (!part) return;
    object.userData.partId = id;
    object.material = new THREE.MeshStandardMaterial({
      color: colors[part.group],
      metalness: part.group === "exterior" ? 0.5 : 0.15,
      roughness: 0.58,
      flatShading: true,
      side: THREE.DoubleSide,
    });
    meshes.set(id, object);
    baseZ.set(id, object.position.z);
  });
  scene.add(gltf.scene);
  makeKeepouts();
  updateVisibility();
  renderGroups();
  renderParts();
  renderProgram();
  document.querySelector("#model-part-count").textContent =
    state.assembly.parts.length;
  const e = state.assembly.extent_mm;
  document.querySelector("#extent").textContent =
    `${e.length} × ${e.width} × ${e.thickness}`;
  resize();
} catch (error) {
  document
    .querySelector("#viewport")
    .insertAdjacentHTML(
      "beforeend",
      `<div class="load-error">Unable to load assembly: ${esc(error.message)}. Run the geometry generator and start the Vite server.</div>`,
    );
}
