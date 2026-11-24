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
  isolated: null,
  section: { enabled: false, axis: "x", fraction: 0.5 },
  immersive: false,
  view: "iso",
  tab: "inspect",
};
const meshes = new Map();
const baseZ = new Map();
const keepoutMeshes = [];
const viewport = document.querySelector("#viewport");
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x101d2b);
const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 3000);
camera.up.set(0, 0, 1);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.localClippingEnabled = true;
viewport.append(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.minDistance = 8;
controls.maxDistance = 1600;
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
const sectionPlane = new THREE.Plane(new THREE.Vector3(-1, 0, 0), 90);
const sectionGuide = new THREE.Group();
const sectionFace = new THREE.Mesh(
  new THREE.BufferGeometry(),
  new THREE.MeshBasicMaterial({
    color: 0x75c2d8,
    transparent: true,
    opacity: 0.08,
    depthWrite: false,
    side: THREE.DoubleSide,
  }),
);
const sectionEdge = new THREE.LineLoop(
  new THREE.BufferGeometry(),
  new THREE.LineBasicMaterial({ color: 0x75c2d8 }),
);
sectionGuide.add(sectionFace, sectionEdge);
sectionGuide.visible = false;
scene.add(sectionGuide);

function resize() {
  const { width, height } = viewport.getBoundingClientRect();
  if (!width || !height) return;
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
  if (state.assembly && state.view) setView(state.view);
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
      state.isolated = null;
      updateVisibility();
      renderGroups();
      renderParts();
      renderDetail();
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
  document.querySelector("#part-detail").innerHTML = `
    <div class="eyebrow">${esc(labels[part.group])} / ${esc(part.id)}</div>
    <div class="detail-title-row"><h2>${esc(part.label)}</h2><span class="swatch large" style="--swatch:#${colors[part.group].toString(16).padStart(6, "0")}"></span></div>
    <div class="detail-status">${part.active ? "In current planning model" : "Deferred from current build"}</div>
    <div class="detail-actions">
      <button type="button" data-detail-action="focus">Focus part</button>
      <button type="button" data-detail-action="isolate" aria-pressed="${state.isolated === part.id}">${state.isolated === part.id ? "Show assembly" : "Isolate part"}</button>
    </div>
    <div class="section-heading">Geometry</div>
    <div class="property"><span>Envelope</span><strong>${textBox(part.box_mm)}</strong></div>
    <div class="property"><span>Origin (x, y, z)</span><strong>${part.box_mm.slice(0, 3).join(", ")} mm</strong></div>
    <div class="property"><span>Geometry type</span><strong>Provisional box</strong></div>
    <div class="section-heading">Engineering basis</div>
    <div class="property"><span>Evidence class</span><strong>${esc(part.evidence_class.replaceAll("_", " "))}</strong></div>
    <div class="source-path"><span>Source</span><code>${esc(part.source)}</code></div>
    ${part.notes ? `<div class="detail-note">${esc(part.notes.replaceAll("_", " "))}</div>` : ""}
    <p class="detail-caveat">This box is a planning envelope. Verify against supplier CAD and released drawings before treating it as a physical part.</p>`;
}
function renderCoverageItem(component) {
  const representedParts = component.part_ids
    .map((id) => {
      const label =
        state.assembly.parts.find((part) => part.id === id)?.label || id;
      return `<button type="button" data-cover-part="${esc(id)}">${esc(label)}</button>`;
    })
    .join("");
  return `<details class="coverage-item">
    <summary><strong>${esc(component.id.replaceAll("_", " "))}</strong><span class="coverage-tag">${esc(component.representation)}</span></summary>
    <p>${esc(component.function)}</p>
    <div class="coverage-parts">${representedParts || "No geometry or placement"}</div>
    <code>${esc(component.source)}</code>
  </details>`;
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
    coverage.map(renderCoverageItem).join("");
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
      (!state.isolated || part.id === state.isolated) &&
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
    mesh.visible = state.keepouts && !state.isolated;
  });
  if (selectionBox) {
    selectionBox.visible = Boolean(meshes.get(state.selected)?.visible);
    selectionBox.update();
  }
}
function updateSection() {
  if (!state.assembly) return;
  const { axis, fraction, enabled } = state.section;
  const normal = {
    x: [-1, 0, 0],
    y: [0, -1, 0],
    z: [0, 0, -1],
  }[axis];
  sectionPlane.normal.set(...normal);
  const limit = {
    x: state.assembly.extent_mm.length,
    y: state.assembly.extent_mm.width,
    z: state.assembly.extent_mm.thickness,
  }[axis];
  const position = limit * fraction;
  sectionPlane.constant = position;
  const e = state.assembly.extent_mm;
  const corners = {
    x: [
      [position, 0, 0],
      [position, e.width, 0],
      [position, e.width, e.thickness],
      [position, 0, e.thickness],
    ],
    y: [
      [0, position, 0],
      [e.length, position, 0],
      [e.length, position, e.thickness],
      [0, position, e.thickness],
    ],
    z: [
      [0, 0, position],
      [e.length, 0, position],
      [e.length, e.width, position],
      [0, e.width, position],
    ],
  }[axis].map((corner) => new THREE.Vector3(...corner));
  sectionFace.geometry.dispose();
  sectionFace.geometry = new THREE.BufferGeometry().setFromPoints(corners);
  sectionFace.geometry.setIndex([0, 1, 2, 0, 2, 3]);
  sectionEdge.geometry.dispose();
  sectionEdge.geometry = new THREE.BufferGeometry().setFromPoints(corners);
  sectionGuide.visible = enabled;
  const planes = enabled ? [sectionPlane] : [];
  for (const mesh of [...meshes.values(), ...keepoutMeshes]) {
    mesh.material.clippingPlanes = planes;
    for (const child of mesh.children) child.material.clippingPlanes = planes;
  }
  if (selectionBox) selectionBox.material.clippingPlanes = planes;
  document.querySelector("#section-position").disabled = !enabled;
  document.querySelector("#section-value").textContent =
    `${axis.toUpperCase()} ${position.toFixed(1)} mm`;
  document.querySelectorAll("[data-section-axis]").forEach((button) => {
    button.classList.toggle("active", button.dataset.sectionAxis === axis);
    button.setAttribute(
      "aria-pressed",
      String(button.dataset.sectionAxis === axis),
    );
  });
}
function revealPart(part) {
  if (state.activeGroup && state.activeGroup !== part.group) {
    state.activeGroup = null;
    renderGroups();
  }
  if (state.isolated && state.isolated !== part.id) state.isolated = null;
  if (
    state.search &&
    !`${part.label} ${part.group} ${part.id}`
      .toLowerCase()
      .includes(state.search)
  ) {
    state.search = "";
    document.querySelector("#part-search").value = "";
  }
  if (part.group === "exterior") state.shell = true;
  if (!part.active) state.deferred = true;
  document.querySelector("#shell-toggle").checked = state.shell;
  document.querySelector("#deferred-toggle").checked = state.deferred;
}
function selectPart(id) {
  const part = state.assembly.parts.find((p) => p.id === id);
  if (!part) return;
  revealPart(part);
  state.selected = id;
  state.tab = "inspect";
  setTab();
  renderParts();
  renderDetail();
  updateVisibility();
  if (selectionBox) {
    scene.remove(selectionBox);
    selectionBox.geometry.dispose();
    selectionBox.material.dispose();
  }
  const mesh = meshes.get(id);
  if (mesh) {
    selectionBox = new THREE.BoxHelper(mesh, 0xffd47b);
    selectionBox.material.depthTest = false;
    selectionBox.material.clippingPlanes = state.section.enabled
      ? [sectionPlane]
      : [];
    scene.add(selectionBox);
  }
}
function focusSelected() {
  const mesh = meshes.get(state.selected);
  if (!mesh) return;
  const bounds = new THREE.Box3().setFromObject(mesh);
  const center = bounds.getCenter(new THREE.Vector3());
  const size = bounds.getSize(new THREE.Vector3());
  const direction = camera.position.clone().sub(controls.target).normalize();
  const distance = Math.max(25, size.length() * 2.4);
  controls.target.copy(center);
  camera.position.copy(center).addScaledVector(direction, distance);
  controls.update();
  state.view = null;
  document
    .querySelectorAll("[data-view]")
    .forEach((button) => button.classList.remove("active"));
}
function setImmersive(enabled) {
  state.immersive = enabled;
  document.querySelector("#app").classList.toggle("immersive", enabled);
  const button = document.querySelector("#immersive-view");
  button.textContent = enabled ? "Exit expanded view" : "Expand view";
  button.setAttribute("aria-pressed", String(enabled));
  resize();
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
  const extent = state.assembly?.extent_mm || {
    length: 180,
    width: 95,
    thickness: 9.5,
  };
  const target = new THREE.Vector3(
    extent.length / 2,
    extent.width / 2,
    extent.thickness / 2,
  );
  const direction = new THREE.Vector3(
    ...{
      iso: [160, -175, 125],
      front: [0, 0, 240],
      rear: [0, 0, -240],
      side: [250, 0, 0],
    }[view],
  ).normalize();
  const verticalFov = THREE.MathUtils.degToRad(camera.fov);
  const horizontalFov =
    2 * Math.atan(Math.tan(verticalFov / 2) * camera.aspect);
  const radius = Math.hypot(extent.length, extent.width, extent.thickness) / 2;
  const distance =
    (radius / Math.sin(Math.min(verticalFov, horizontalFov) / 2)) * 1.12;
  camera.up.set(
    0,
    view === "front" || view === "rear" ? 1 : 0,
    view === "front" || view === "rear" ? 0 : 1,
  );
  camera.position.copy(target).addScaledVector(direction, distance);
  controls.target.copy(target);
  controls.update();
  state.view = view;
  document
    .querySelectorAll("[data-view]")
    .forEach((button) =>
      button.classList.toggle("active", button.dataset.view === view),
    );
}
controls.addEventListener("start", () => {
  state.view = null;
});
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
  state.isolated = null;
  state.search = "";
  document.querySelector("#part-search").value = "";
  updateVisibility();
  renderGroups();
  renderParts();
  renderDetail();
});
document
  .querySelector("#fit-model")
  .addEventListener("click", () => setView("iso"));
document.querySelector("#immersive-view").addEventListener("click", () => {
  setImmersive(!state.immersive);
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && state.immersive) setImmersive(false);
});
document.querySelector("#part-detail").addEventListener("click", (event) => {
  const action = event.target.closest("[data-detail-action]")?.dataset
    .detailAction;
  if (action === "focus") focusSelected();
  if (action === "isolate") {
    state.isolated = state.isolated === state.selected ? null : state.selected;
    updateVisibility();
    renderDetail();
  }
});
document.querySelector("#coverage").addEventListener("click", (event) => {
  const id = event.target.closest("[data-cover-part]")?.dataset.coverPart;
  if (id) selectPart(id);
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
  .querySelector("#section-toggle")
  .addEventListener("change", (event) => {
    state.section.enabled = event.target.checked;
    updateSection();
  });
document
  .querySelector("#section-position")
  .addEventListener("input", (event) => {
    state.section.fraction = Number(event.target.value) / 100;
    updateSection();
  });
document.querySelectorAll("[data-section-axis]").forEach((button) =>
  button.addEventListener("click", () => {
    state.section.axis = button.dataset.sectionAxis;
    updateSection();
  }),
);
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
  const response = await fetch(`${import.meta.env.BASE_URL}assembly.json`);
  if (!response.ok) throw new Error(`assembly data: HTTP ${response.status}`);
  state.assembly = await response.json();
  const gltf = await new GLTFLoader().loadAsync(
    `${import.meta.env.BASE_URL}assembly.gltf`,
  );
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
  if (meshes.size !== state.assembly.parts.length) {
    throw new Error(
      `expected ${state.assembly.parts.length} part meshes, found ${meshes.size}`,
    );
  }
  makeKeepouts();
  updateVisibility();
  updateSection();
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
