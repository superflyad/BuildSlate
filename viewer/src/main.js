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
const requestedTab = new URLSearchParams(window.location.search).get("tab");
const requestedModel = new URLSearchParams(window.location.search).get("model");
const state = {
  assembly: null,
  assets: null,
  proof: null,
  proofs: null,
  hardware: null,
  model: "concept",
  selected: null,
  search: "",
  activeGroup: null,
  shell: true,
  keepouts: false,
  deferred: false,
  proofConflicts: false,
  explode: 0,
  isolated: null,
  section: { enabled: false, axis: "x", fraction: 0.5 },
  immersive: false,
  view: "iso",
  tab: ["inspect", "program", "proof", "hardware"].includes(requestedTab)
    ? requestedTab
    : "inspect",
};
const meshes = new Map();
const baseZ = new Map();
let modelRoot = null;
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
function memoryBoard(study, side) {
  const [width, height] = study.board_outline_mm;
  const existing = side === "component" ? study.component_side_placements : [];
  const packages = study.placements.filter((item) => item.side === side);
  const rect = (item, className, label) => {
    const [x, y, length, breadth] = item.rect_mm;
    return `<g><title>${esc(item.id.replaceAll("_", " "))}</title><rect class="${className}" x="${esc(x)}" y="${esc(y)}" width="${esc(length)}" height="${esc(breadth)}"/>${label ? `<text x="${esc(x + length / 2)}" y="${esc(y + breadth / 2)}" dominant-baseline="central" text-anchor="middle">${esc(label)}</text>` : ""}</g>`;
  };
  return `<figure class="memory-board"><figcaption>${side === "component" ? "Component side" : "Reverse side"}</figcaption><svg role="img" aria-label="${side === "component" ? "Four reference memory packages beside existing planning blocks" : "Four reference memory packages on the reverse board side"}" viewBox="0 0 ${esc(width)} ${esc(height)}"><rect class="board-outline" x="0" y="0" width="${esc(width)}" height="${esc(height)}"/>${existing.map((item) => rect(item, "existing-part", item.id === "compute_soc" ? "SoC" : item.id === "storage_ufs_1tb_reference" ? "UFS" : "")).join("")}${packages.map((item) => rect(item, "memory-part", "16")).join("")}</svg></figure>`;
}
function sourceLink(reference) {
  const path = reference.split("#", 1)[0];
  return `https://github.com/superflyad/BuildSlate/blob/main/${path.split("/").map(encodeURIComponent).join("/")}`;
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
  const proof =
    state.model !== "assembly"
      ? state.proof.parts.find((item) => item.id === part.id)
      : null;
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
    <div class="property"><span>Geometry type</span><strong>${esc((part.shape || "box").replaceAll("_", " "))}</strong></div>
    ${
      proof
        ? `<div class="property"><span>BREP volume</span><strong>${proof.volume_mm3.toLocaleString()} mm³</strong></div>
    <div class="property"><span>Topology</span><strong>${proof.faces} faces · ${proof.edges} edges</strong></div>
    <div class="property"><span>Integrity checks</span><strong>${Object.values(proof.checks).filter(Boolean).length}/${Object.keys(proof.checks).length} passed</strong></div>
    <div class="property"><span>Solid intersections</span><strong>${proof.interference_ids.length}</strong></div>
    <div class="property"><span>Contacts and gaps ≤0.5 mm</span><strong>${proof.nominal_gap_ids.length}</strong></div>
    <div class="property"><span>Camera path findings</span><strong>${proof.optical_path_ids.length}</strong></div>
    <div class="property"><span>Keepout conflicts</span><strong>${proof.keepout_ids.length}</strong></div>
    ${proof.nominal_gap_ids.length ? `<p class="detail-note">Nominally near: ${esc(proof.nominal_gap_ids.join(", "))}</p>` : ""}
    ${proof.keepout_ids.length ? `<p class="detail-note">Reserved regions: ${esc(proof.keepout_ids.join(", "))}</p>` : ""}
    ${proof.reservation_conflict_ids.length ? `<p class="detail-note">Reservation overlap: ${esc(proof.reservation_conflict_ids.join(", "))}</p>` : ""}`
        : ""
    }
    <div class="section-heading">Engineering basis</div>
    <div class="property"><span>Evidence class</span><strong>${esc(part.evidence_class.replaceAll("_", " "))}</strong></div>
    <div class="source-path"><span>Source</span><a href="${sourceLink(part.source)}" target="_blank" rel="noopener noreferrer"><code>${esc(part.source)}</code></a></div>
    ${part.geometry_source ? `<div class="source-path"><span>Geometry basis · ${esc(part.geometry_evidence_class.replaceAll("_", " "))}</span><a href="${sourceLink(part.geometry_source)}" target="_blank" rel="noopener noreferrer"><code>${esc(part.geometry_source)}</code></a></div>` : ""}
    ${part.notes ? `<div class="detail-note">${esc(part.notes.replaceAll("_", " "))}</div>` : ""}
    <p class="detail-caveat">${esc(state.assembly.caveat)}</p>`;
}
function proofPartButton(id) {
  const proofModel = state.model === "assembly" ? "concept" : state.model;
  const part = state.assets[proofModel].data.parts.find(
    (item) => item.id === id,
  );
  return `<button type="button" class="proof-part" data-proof-part="${esc(id)}">${esc(part?.label || id)}</button>`;
}
function renderProof() {
  const proof = state.proof;
  const summary = proof.summary;
  const proofModel = state.model === "assembly" ? "concept" : state.model;
  const proofTitles = {
    concept: "Baseline concept",
    memory8: "Eight-package reference",
    phonefit: "Rejected phone layout",
  };
  const proofFiles = {
    concept: "proof.json",
    memory8: "memory-8x16-proof.json",
    phonefit: "phone-fit-conflict-proof.json",
  };
  document.querySelector("#proof-method").textContent =
    `${proofTitles[proofModel]} · ${proof.method}`;
  const rawLink = document.querySelector("#proof-raw-link");
  rawLink.href = `${import.meta.env.BASE_URL}${proofFiles[proofModel]}`;
  rawLink.textContent = `${proofTitles[proofModel]} proof JSON`;
  document.querySelector("#proof-summary").innerHTML = [
    [
      "Solids checked",
      `${summary.parts_checked}/${state.assets[proofModel].data.parts.length}`,
    ],
    ["STEP round trip", summary.step_roundtrip_passed ? "PASS" : "FAIL"],
    ["Integrity", summary.integrity_passed ? "PASS" : "FAIL"],
    ["Solid intersections", summary.interferences],
    ["Nominal contacts", summary.nominal_contacts],
    ["Gaps ≤0.5 mm", summary.small_nominal_gaps],
    ["Camera path conflicts", summary.optical_model_conflicts],
    ["Keepout conflicts", summary.keepout_conflicts],
    ["Reservation overlaps", summary.reservation_conflicts],
    ["Stack failures", summary.stack_failures],
    ["Unverified parts", summary.unverified_parts],
  ]
    .map(
      ([label, value]) =>
        `<div><strong>${value}</strong><span>${label}</span></div>`,
    )
    .join("");
  const memoryStudy = proof.memory_study;
  document.querySelector("#proof-memory-study").innerHTML =
    (memoryStudy
      ? `<div class="gate-item"><strong>Eight-package outline</strong><span>${esc(memoryStudy.status.replaceAll("_", " "))} · ${esc(memoryStudy.minimum_screened_planar_gap_mm)} mm minimum screened planar gap</span></div><div class="gate-item"><strong>PCB stack screen</strong><span>${esc(memoryStudy.floorplan_board_thickness_mm)} mm provisional floorplan and ${esc(memoryStudy.mechanical_board_height_mm)} mm mechanical board · ${esc(memoryStudy.stack_issues.join("; ") || "internal geometry aligned; fabricator review required")}</span></div>`
      : "") +
    (proof.phone_extension
      ? `<div class="gate-item"><strong>Phone layout rejected</strong><span>Expanded board ${esc(proof.phone_extension.board_global_box_mm[3])} × ${esc(proof.phone_extension.minimum_whole_mm_board_width)} mm; board conflicts: ${esc(proof.phone_extension.board_3d_conflicts.join(", "))}; module conflicts: ${esc(proof.phone_extension.module_3d_conflicts.join(", "))}. Inspect the solid intersections below.</span></div>`
      : "");
  document.querySelector("#proof-intersections").innerHTML =
    proof.intersections
      .filter((item) => item.kind === "interference")
      .map(
        (item) =>
          `<div class="proof-item">${proofPartButton(item.first)}<span>↔</span>${proofPartButton(item.second)}<small>${item.volume_mm3} mm³ overlap</small></div>`,
      )
      .join("") ||
    '<p class="muted">No positive volume intersections at nominal concept positions. Tolerances and flex routing are not modeled.</p>';
  const gapItem = (item) =>
    `<div class="proof-item">${proofPartButton(item.first)}<span>↔</span>${proofPartButton(item.second)}<small>${item.kind === "contact" ? "nominal contact" : `${item.distance_mm.toFixed(3)} mm nominal gap`}</small></div>`;
  const smallGaps = proof.nominal_gaps
    .filter((item) => item.kind === "small_gap")
    .sort((first, second) => first.distance_mm - second.distance_mm);
  const contacts = proof.nominal_gaps.filter((item) => item.kind === "contact");
  document.querySelector("#proof-nominal-gaps").innerHTML =
    `<details class="coverage-item" open><summary><strong>Gaps through 0.5 mm</strong><span class="coverage-tag">${smallGaps.length}</span></summary><div class="proof-list">${smallGaps.map(gapItem).join("") || '<p class="muted">No small nominal gaps.</p>'}</div></details>` +
    `<details class="coverage-item"><summary><strong>Nominal contacts</strong><span class="coverage-tag">${contacts.length}</span></summary><div class="proof-list">${contacts.map(gapItem).join("") || '<p class="muted">No nominal contacts.</p>'}</div></details>`;
  document.querySelector("#proof-optical-paths").innerHTML = proof.optical_paths
    .map(
      (item) =>
        `<div class="proof-item">${proofPartButton(item.camera_id)}<span>↔</span>${proofPartButton(item.blocking_part_id)}<small>${item.solid_overlap_mm3} mm³ of the nominal pupil prism intersects the concept solid (${item.pupil_prism_overlap_percent}%). Modeled aperture radial margin ${item.aperture_radial_margin_mm} mm. Supplier optical construction and physical performance are unverified.</small></div>`,
    )
    .join("");
  document.querySelector("#proof-reservations").innerHTML = proof.intersections
    .filter((item) => item.kind === "reservation_conflict")
    .map(
      (item) =>
        `<div class="proof-item">${proofPartButton(item.first)}<span>↔</span>${proofPartButton(item.second)}<small>${item.volume_mm3} mm³ reserved volume</small></div>`,
    )
    .join("");
  document.querySelector("#proof-keepouts").innerHTML = proof.keepout_conflicts
    .map(
      (item) =>
        `<div class="proof-item">${proofPartButton(item.part_id)}<small>${esc(item.keepout_id.replaceAll("_", " "))} · ${item.overlap_area_mm2} mm²</small></div>`,
    )
    .join("");
  document.querySelector("#proof-zones").innerHTML = proof.zones
    .map(
      (zone) =>
        `<div class="proof-zone"><strong>${esc(zone.id.replaceAll("_", " "))}</strong><span class="proof-status ${esc(zone.status)}">${esc(zone.status)}</span><small>${zone.total_mm.toFixed(2)} mm · ${zone.margin_mm.toFixed(2)} mm margin</small></div>`,
    )
    .join("");
  document.querySelector("#proof-roles").innerHTML = proof.roles
    .map(
      (role) => `<details class="coverage-item">
        <summary><strong>${esc(role.id.replaceAll("_", " "))}</strong><span class="coverage-tag">${role.missing_evidence.length} gaps</span></summary>
        <p>Geometry integrity ${role.geometry_integrity_passed ? "passed" : "failed"} · ${role.keepout_count} keepout findings · ${esc(role.source_representation)} source representation</p>
        <div class="coverage-parts">${role.part_ids.map(proofPartButton).join("")}</div>
        <p>Still needed:</p><ul class="proof-unknowns">${role.missing_evidence.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>
      </details>`,
    )
    .join("");
  document.querySelector("#proof-caveat").textContent =
    `${proof.caveat} ${state.assets[proofModel].data.caveat}`;
}
function renderHardware() {
  const report = state.hardware;
  const design = report.requirements.filter(
    (item) => item.stage === "design_release",
  );
  const evt0 = report.requirements.filter(
    (item) => item.stage === "functional_evt0",
  );
  const phone = report.requirements.filter(
    (item) => item.stage === "phone_function",
  );
  document.querySelector("#hardware-summary").innerHTML = [
    ["Design release", report.design_release],
    ["Functional EVT0", report.functional_evt0],
    ["Working phone", report.phone_function],
    ["Schematic ERC", design.find((item) => item.id === "erc_report").status],
    ["Routed PCB DRC", design.find((item) => item.id === "routed_pcb").status],
    ["Power design proof", report.power_safety.status],
    ["Thermal design proof", report.thermal_release.status],
    ["RF design proof", report.rf_release.status],
    ["Interconnect pin map", report.interconnect_release.status],
    ["Public platform fit", report.platform_fit.status],
    ["Display active-area fit", report.display_fit.status],
    ["Storage integration", report.storage_fit.integration_status],
    ["Battery integration", report.battery_fit.integration_status],
    ["5G reference outline", report.cellular_reference_fit.status],
    ["128 GB memory package", report.memory_package_fit.integration_status],
    ["Firmware bundle integrity", report.firmware_bundle.status],
    [
      "Camera model paths",
      `${state.proof.summary.optical_model_conflicts}/${state.proof.optical_paths.length} modeled obstructions; unqualified`,
    ],
    [
      "Selected roles",
      `${report.selected_roles.filter((item) => item.selected).length}/${report.selected_roles.length}`,
    ],
    [
      "Evidence records",
      `${report.requirements.filter((item) => item.status === "accepted").length}/${report.requirements.length}`,
    ],
  ]
    .map(
      ([label, value]) =>
        `<div><strong class="hardware-status">${esc(value.replaceAll("_", " "))}</strong><span>${label}</span></div>`,
    )
    .join("");
  const platform = report.platform_fit;
  const memoryBus = report.memory_package_fit.bus_topology_screen;
  const obsolete32 = report.memory_package_fit.obsolete_32gb_reference;
  document.querySelector("#hardware-platforms").innerHTML =
    `<div class="gate-item"><strong>Decision</strong><span>${esc(platform.decision)}</span></div>` +
    platform.candidates
      .map(
        (item) =>
          `<div class="gate-item"><strong>${esc(item.id.replaceAll("_", " "))}</strong><span>${item.public_maximum_memory_gb} GB public maximum · ${item.public_configured_memory_gb === null ? "no public configuration listed" : `${item.public_configured_memory_gb} GB public configuration`} · ${item.observed_oem_memory_gb === null ? "no reviewed OEM package" : `<a href="${esc(item.observed_oem_source)}" target="_blank" rel="noopener noreferrer">${esc(item.observed_oem_memory_gb)} GB OEM memory on package</a> · <a href="${esc(item.physical_package_source)}" target="_blank" rel="noopener noreferrer">physical package analysis</a>`} · ${item.integrated_phone_path ? "integrated phone path" : "no integrated phone path"} · <a href="${esc(item.source)}" target="_blank" rel="noopener noreferrer">source</a></span></div>`,
      )
      .join("") +
    platform.candidates
      .filter((item) => item.module_outline_mm !== null)
      .map(
        (item) =>
          `<div class="gate-item"><strong>${esc(item.id.replaceAll("_", " "))} physical screen</strong><span>${esc(item.module_outline_mm.join(" × "))} mm module face · ${item.module_outline_fits_body_face ? "fits the body face alone" : "exceeds the body face"} (${esc(platform.slate_body_face_mm.join(" × "))} mm) · ${esc(item.minimum_published_power_mode_w)} W minimum published mode, ${esc(item.minimum_published_mode_over_slate_w)} W relative to Slate's ${esc(platform.slate_sustained_screen_w)} W sustained screen. This is a published operating mode, not a measured power draw. <a href="${esc(item.source)}" target="_blank" rel="noopener noreferrer">Manufacturer specification</a></span></div>`,
      )
      .join("");
  document.querySelector("#hardware-parts").innerHTML =
    `<div class="gate-item"><strong>Released part set</strong><span>${esc(report.part_selection.status)}${report.part_selection.errors.length ? ` · ${esc(report.part_selection.errors.join("; "))}` : ""}</span></div>` +
    `<div class="gate-item"><strong>Platform reference and memory map</strong><span>${esc(report.platform_reference.status)} · ${esc(report.platform_reference.errors.join("; "))}</span></div>` +
    `<div class="gate-item"><strong>Power design proof</strong><span>${esc(report.power_safety.status)} · ${esc(report.power_safety.errors.join("; "))}</span></div>` +
    `<div class="gate-item"><strong>Thermal design proof</strong><span>${esc(report.thermal_release.status)} · ${esc(report.thermal_release.errors.join("; "))}</span></div>` +
    `<div class="gate-item"><strong>RF design proof</strong><span>${esc(report.rf_release.status)} · ${esc(report.rf_release.errors.join("; "))}</span></div>` +
    `<div class="gate-item"><strong>Interconnect pin map</strong><span>${esc(report.interconnect_release.status)} · ${esc(report.interconnect_release.errors.join("; "))}</span></div>` +
    `<div class="gate-item"><strong>Firmware bundle integrity</strong><span>${esc(report.firmware_bundle.status)} · ${esc(report.firmware_bundle.errors.join("; "))}</span></div>` +
    `<div class="gate-item"><strong>1 TB UFS candidate</strong><span>${esc(report.storage_fit.manufacturer_part_number)} · ${esc(report.storage_fit.package_mm.join(" × "))} mm · ${esc(report.storage_fit.outline_fit)} outline fit · ${esc(report.storage_fit.board_boundary_clearance_mm)} mm board-edge clearance · <a href="${esc(report.storage_fit.source)}" target="_blank" rel="noopener noreferrer">manufacturer brief</a></span></div>` +
    `<div class="gate-item"><strong>Storage integration blockers</strong><span>${esc(report.storage_fit.rails.map((rail) => `${rail.id}: ${rail.status} (${rail.required_voltage_v.join("–")} V)`).join("; "))} · ${esc(report.storage_fit.missing_design_evidence.join("; "))}</span></div>` +
    `<div class="gate-item"><strong>Battery candidate geometry</strong><span>${esc(report.battery_fit.product)} cell box ${esc(report.battery_fit.cell_box_volume_mm3)} mm³ versus ${esc(report.battery_fit.complete_pack_allocation_mm3)} mm³ complete-pack allocation; concept pack envelope ${esc(report.battery_fit.concept_pack_envelope_mm3)} mm³. <a href="${esc(report.battery_fit.source)}" target="_blank" rel="noopener noreferrer">Manufacturer listing</a></span></div>` +
    `<div class="gate-item"><strong>Battery sourcing</strong><span>${esc(report.battery_fit.supplier_path_finding)} The listed cell remains a geometry benchmark; no Slate pack is selected. <a href="${esc(report.battery_fit.supplier_path_source)}" target="_blank" rel="noopener noreferrer">Enovix filing</a></span></div>` +
    `<div class="gate-item"><strong>Battery charge evidence</strong><span>No published charge limit for this cell. The listed ${esc(report.battery_fit.public_discharge_category)} band is for continuous discharge. ${esc(report.battery_fit.missing_design_evidence.join("; "))}</span></div>` +
    `<div class="gate-item"><strong>Display geometry conflict</strong><span>Target ${esc(report.display_fit.target_diagonal_in)} in ${esc(report.display_fit.target_aspect_ratio)} needs an active rectangle of ${esc(report.display_fit.target_active_mm.join(" × "))} mm. The body is ${esc(report.display_fit.device_face_mm.join(" × "))} mm and the CAD display reserve is ${esc(report.display_fit.cad_display_reserve_mm.join(" × "))} mm. The active short side exceeds the body by ${esc(report.display_fit.short_side_overrun_mm.device_face)} mm and the reserve by ${esc(report.display_fit.short_side_overrun_mm.cad_reserve)} mm. ${esc(report.display_fit.resolution_px.join(" × "))} pixels are ${esc(report.display_fit.resolution_aspect_ratio)}, not the declared ${esc(report.display_fit.target_aspect_ratio)}. Design release stays blocked. <a href="https://github.com/superflyad/BuildSlate/blob/main/docs/engineering/display_geometry_fit.md" target="_blank" rel="noopener noreferrer">Geometry proof</a></span></div>` +
    `<div class="gate-item"><strong>128 GB memory geometry</strong><span>${esc(report.memory_package_fit.planning_sites)} assumed 32 GB sites; exact public ${esc(report.memory_package_fit.public_reference_part)} is ${esc(report.memory_package_fit.public_reference_capacity_gb)} GB and ${esc(report.memory_package_fit.public_reference_package_mm.join(" × "))} mm. It needs ${esc(report.memory_package_fit.required_public_reference_packages)} packages for 128 GB; the current sites fit neither its outline nor height. These separate memory boxes do not represent the observed X2 48 GB memory-on-package configuration. <a href="${esc(report.memory_package_fit.source)}" target="_blank" rel="noopener noreferrer">Manufacturer part</a></span></div>` +
    `<div class="gate-item"><strong>Exact 32 GB package rejected</strong><span>${esc(obsolete32.part_number)} is a ${esc(obsolete32.package_mm.join(" × "))} mm, ${esc(obsolete32.public_part_status)} Micron part. Four reach 128 GB by capacity, but none fit the current 14 × 10 mm sites. Four independent x64 connections need ${esc(obsolete32.independent_bus_width_bits)} data bits against the X2 Extreme's ${esc(memoryBus.controller_bus_width_bits)}-bit bus. This is not a selected part. <a href="${esc(obsolete32.source)}" target="_blank" rel="noopener noreferrer">Manufacturer status</a></span></div>` +
    `<div class="gate-item"><strong>128 GB bus topology</strong><span>Eight x${esc(memoryBus.public_reference_package_bus_width_bits)} packages would need ${esc(memoryBus.independent_connection_width_bits)} data bits if each had an independent host connection; the X2 Extreme lists ${esc(memoryBus.controller_bus_width_bits)} bits. A supplier-qualified shared-channel or other topology is required. <a href="${esc(memoryBus.controller_source)}" target="_blank" rel="noopener noreferrer">Controller brief</a></span></div>` +
    `<div class="gate-item"><strong>Memory integration blockers</strong><span>${esc(report.memory_package_fit.missing_design_evidence.join("; "))}</span></div>` +
    `<div class="gate-item"><strong>Supplier package review</strong><span>${esc(report.part_selection.supplier_packages_unverified.join(", ") || "Verified")}</span></div>` +
    report.selected_roles
      .map(
        (item) =>
          `<div class="gate-item"><strong>${esc(item.id.replaceAll("_", " "))}</strong><span>${item.selected ? `Selected · ${esc(item.mpn)}` : `Selection required${item.reasons.length ? ` · ${esc(item.reasons.join("; "))}` : ""}`}</span></div>`,
      )
      .join("") +
    `<div class="gate-item"><strong>Cellular modem</strong><span>${report.cellular.selected ? "Selected" : esc(report.cellular.status.replaceAll("_", " "))}</span></div>`;
  const cellularFit = report.cellular_reference_fit;
  const cellularGeometry = Object.values(cellularFit.sides).some(
    (side) => side.outline_fits,
  )
    ? "has a nominal outline location on the board; integration remains unqualified"
    : "fits neither side of the current board";
  const cellularSummary = `A ${esc(cellularFit.package_mm.join(" × "))} mm ${esc(cellularFit.candidate)} 5G RedCap reference module ${cellularGeometry} with four 16 GB memory outlines per side and an assumed ${esc(cellularFit.assumed_nominal_package_clearance_mm)} mm gap. Voice is optional on this module. It is not selected. <a href="${esc(cellularFit.source)}" target="_blank" rel="noopener noreferrer">Manufacturer specification</a> · <a href="https://github.com/superflyad/BuildSlate/blob/main/docs/engineering/cellular_module_fit.md" target="_blank" rel="noopener noreferrer">Fit method</a>`;
  const boardExtension = cellularFit.reverse_board_extension;
  const boardExtensionSummary = `The first whole-millimeter reverse-side outline fit needs a ${esc(cellularFit.board_outline_mm[0])} × ${esc(boardExtension.minimum_whole_mm_board_width)} mm board, ${esc(boardExtension.increase_from_current_board_mm)} mm wider than the current board. The expanded board intersects the ${esc(boardExtension.board_3d_conflicts.join(", ").replaceAll("_placeholder", "").replaceAll("_concept", "").replaceAll("_", " "))}; the module itself intersects the ${esc(boardExtension.module_3d_conflicts.join(", ").replaceAll("_placeholder", "").replaceAll("_", " "))}. <a href="?model=phonefit&tab=proof">Inspect the 3D collision study</a>. This is not a released phone layout.`;
  document
    .querySelector("#hardware-parts")
    .insertAdjacentHTML(
      "beforeend",
      `<div class="gate-item"><strong>5G reference package fit</strong><span>${cellularSummary}</span></div><div class="gate-item"><strong>Board expansion conflict</strong><span>${boardExtensionSummary}</span></div>`,
    );
  const study = report.memory_package_fit.eight_package_study;
  document.querySelector("#hardware-memory-layout").innerHTML =
    `<p class="muted">Eight ${esc(report.memory_package_fit.public_reference_capacity_gb)} GB reference outlines: ${esc(study.packages_per_side.component)} on the component side, ${esc(study.packages_per_side.reverse)} on the reverse. Minimum screened planar gap ${esc(study.minimum_screened_planar_gap_mm)} mm under an assumed ${esc(study.assumed_planar_clearance_mm)} mm rule. Geometry status: ${esc(study.status.replaceAll("_", " "))}.</p>` +
    `<p><a href="?model=memory8&tab=hardware">Open the 3D eight-package model</a></p>` +
    `<div class="memory-board-grid">${memoryBoard(study, "component")}${memoryBoard(study, "reverse")}</div>` +
    `<p class="detail-caveat">The floorplan and mechanical model use the same provisional ${esc(study.floorplan_board_thickness_mm)} mm board thickness. Fabrication and two-sided assembly remain unreviewed. ${esc(memoryBus.caveat)} ${esc(study.caveat)} <a href="https://github.com/superflyad/BuildSlate/blob/main/${esc(study.source)}" target="_blank" rel="noopener noreferrer">Study coordinates</a></p>`;
  const campaign = report.evt0_campaign;
  const group = campaign.coherent_evidence_group;
  document.querySelector("#hardware-campaign").innerHTML = `
    <div class="gate-item"><strong>Campaign gate</strong><span>${esc(campaign.gate.replaceAll("_", " "))}</span></div>
    <div class="gate-item"><strong>Required tests on one unit</strong><span>${campaign.passing_required_tests}/${campaign.required_tests} passed${group ? ` · ${esc(group.unit_id)} / ${esc(group.build_id)}` : " · no unit evidence"}</span></div>
    <div class="gate-item"><strong>Missing or nonpassing tests</strong><span>${esc(campaign.missing_tests.join(", ") || "None")}</span></div>
    <div class="gate-item"><strong>Prerequisite gaps</strong><span>${esc(campaign.prerequisite_gaps.join(", ") || "None")}</span></div>`;
  for (const [selector, items] of [
    ["#hardware-design", design],
    ["#hardware-evt0", evt0],
    ["#hardware-phone", phone],
  ]) {
    document.querySelector(selector).innerHTML = items
      .map(
        (item) =>
          `<div class="gate-item"><strong>${esc(item.title)}</strong><span>${esc(item.status)}${item.reasons.length ? ` · ${esc(item.reasons.join("; "))}` : ""}</span></div>`,
      )
      .join("");
  }
  document.querySelector("#hardware-caveat").textContent = report.caveat;
}
function renderCoverageItem(component) {
  const representedParts = (
    state.model === "assembly" ? component.part_ids : component.concept_part_ids
  )
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
    `<p class="coverage-intro">${coverage.length} library roles · ${state.model !== "assembly" ? "all represented in concept CAD; source evidence status follows" : "source envelope status follows"} · ${counts.box} box modeled · ${counts.aggregate} aggregate · ${counts.deferred} deferred · ${counts.unplaced} unplaced</p>` +
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
    const proof =
      state.model !== "assembly"
        ? state.proof.parts.find((item) => item.id === part.id)
        : null;
    const highlight = state.proofConflicts && proof;
    const tint =
      highlight && proof.interference_ids.length
        ? 0xf16d55
        : highlight && proof.keepout_ids.length
          ? 0xe5a45c
          : highlight && proof.reservation_conflict_ids.length
            ? 0xb598e8
            : colors[part.group];
    mesh.material.color.setHex(tint);
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
  for (const tab of ["inspect", "program", "proof", "hardware"]) {
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
document.querySelector("#proof-panel").addEventListener("click", (event) => {
  const id = event.target.closest("[data-proof-part]")?.dataset.proofPart;
  if (!id) return;
  if (state.model === "assembly") displayModel("concept");
  selectPart(id);
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
  ["proof-toggle", "proofConflicts"],
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
for (const tab of ["inspect", "program", "proof", "hardware"])
  document.querySelector(`#tab-${tab}`).addEventListener("click", () => {
    state.tab = tab;
    setTab();
  });

function displayModel(model) {
  for (const [id, mesh] of meshes) mesh.position.z = baseZ.get(id);
  if (modelRoot) scene.remove(modelRoot);
  if (selectionBox) {
    scene.remove(selectionBox);
    selectionBox.geometry.dispose();
    selectionBox.material.dispose();
    selectionBox = null;
  }
  meshes.clear();
  baseZ.clear();
  state.model = model;
  state.proofConflicts = model === "phonefit";
  document.querySelector("#proof-toggle").checked = state.proofConflicts;
  state.proof = state.proofs[model === "assembly" ? "concept" : model];
  state.assembly = state.assets[model].data;
  state.selected = null;
  state.isolated = null;
  state.activeGroup = null;
  const gltf = state.assets[model].gltf;
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
    if (!object.userData.buildslateMaterial) {
      object.material = new THREE.MeshStandardMaterial({
        color: colors[part.group],
        metalness: part.group === "exterior" ? 0.5 : 0.15,
        roughness: 0.58,
        flatShading: model === "assembly",
        side: THREE.DoubleSide,
      });
      object.userData.buildslateMaterial = true;
    }
    meshes.set(id, object);
    baseZ.set(id, object.position.z);
  });
  modelRoot = gltf.scene;
  scene.add(modelRoot);
  if (meshes.size !== state.assembly.parts.length) {
    throw new Error(
      `expected ${state.assembly.parts.length} part meshes, found ${meshes.size}`,
    );
  }
  updateVisibility();
  updateSection();
  renderGroups();
  renderParts();
  renderProgram();
  renderProof();
  renderHardware();
  setTab();
  document.querySelector("#proof-toggle").disabled = model === "assembly";
  document.querySelector("#model-part-count").textContent =
    state.assembly.parts.length;
  document.querySelector("#geometry-label").textContent =
    model === "assembly" ? "source envelopes" : "concept solids";
  document.querySelector("#model-basis").textContent =
    model === "concept"
      ? "Editable assumptions and source geometry"
      : model === "memory8"
        ? "Eight reference packages · stack and topology unresolved"
        : model === "phonefit"
          ? "Rejected modem layout · four measured solid collisions"
          : "Traceable source planning envelopes";
  document.querySelector("#part-detail").className = "detail-placeholder";
  document.querySelector("#part-detail").innerHTML =
    '<div class="detail-icon">◇</div><h2>Select a component</h2><p>Inspect geometry, evidence, and its source.</p>';
  document.querySelectorAll("[data-model]").forEach((button) => {
    button.classList.toggle("active", button.dataset.model === model);
    button.setAttribute("aria-pressed", String(button.dataset.model === model));
  });
  const e = state.assembly.extent_mm;
  document.querySelector("#extent").textContent =
    `${e.length} × ${e.width} × ${e.thickness}`;
  resize();
}
document
  .querySelectorAll("[data-model]")
  .forEach((button) =>
    button.addEventListener("click", () => displayModel(button.dataset.model)),
  );
try {
  const proofResponse = await fetch(`${import.meta.env.BASE_URL}proof.json`);
  if (!proofResponse.ok)
    throw new Error(`proof data: HTTP ${proofResponse.status}`);
  const memoryProofResponse = await fetch(
    `${import.meta.env.BASE_URL}memory-8x16-proof.json`,
  );
  if (!memoryProofResponse.ok)
    throw new Error(`memory CAD proof: HTTP ${memoryProofResponse.status}`);
  const phoneProofResponse = await fetch(
    `${import.meta.env.BASE_URL}phone-fit-conflict-proof.json`,
  );
  if (!phoneProofResponse.ok)
    throw new Error(`phone CAD proof: HTTP ${phoneProofResponse.status}`);
  state.proofs = {
    concept: await proofResponse.json(),
    memory8: await memoryProofResponse.json(),
    phonefit: await phoneProofResponse.json(),
  };
  const hardwareResponse = await fetch(
    `${import.meta.env.BASE_URL}hardware-readiness.json`,
  );
  if (!hardwareResponse.ok)
    throw new Error(`hardware status: HTTP ${hardwareResponse.status}`);
  state.hardware = await hardwareResponse.json();
  const loader = new GLTFLoader();
  const assets = await Promise.all(
    [
      ["concept", "concept"],
      ["memory8", "memory-8x16"],
      ["phonefit", "phone-fit-conflict"],
      ["assembly", "assembly"],
    ].map(async ([key, name]) => {
      const response = await fetch(`${import.meta.env.BASE_URL}${name}.json`);
      if (!response.ok)
        throw new Error(`${name} data: HTTP ${response.status}`);
      return [
        key,
        {
          data: await response.json(),
          gltf: await loader.loadAsync(
            `${import.meta.env.BASE_URL}${name}.gltf`,
          ),
        },
      ];
    }),
  );
  state.assets = Object.fromEntries(assets);
  state.assembly = state.assets.concept.data;
  makeKeepouts();
  displayModel(
    ["concept", "memory8", "phonefit", "assembly"].includes(requestedModel)
      ? requestedModel
      : "concept",
  );
} catch (error) {
  document
    .querySelector("#viewport")
    .insertAdjacentHTML(
      "beforeend",
      `<div class="load-error">Unable to load assembly: ${esc(error.message)}. Run the geometry generator and start the Vite server.</div>`,
    );
}
