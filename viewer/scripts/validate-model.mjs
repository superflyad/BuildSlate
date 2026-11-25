import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { Box3 } from "three";

globalThis.ProgressEvent ??= class ProgressEvent {
  constructor(type, values) {
    this.type = type;
    Object.assign(this, values);
  }
};

const root = resolve(import.meta.dirname, "..");
for (const model of [
  "assembly",
  "concept",
  "memory-8x16",
  "memory-8x16-compact",
  "phone-fit-conflict",
  "usb4525-outline",
  "lp4473109-pack-outline",
]) {
  const assembly = JSON.parse(
    readFileSync(resolve(root, `public/${model}.json`), "utf8"),
  );
  const geometry = readFileSync(resolve(root, `public/${model}.gltf`), "utf8");
  const gltf = await new GLTFLoader().parseAsync(geometry, "");
  const names = new Set();
  const meshes = new Map();
  gltf.scene.traverse((object) => {
    if (object.isMesh) {
      const id = object.userData.part_id ?? object.name;
      names.add(id);
      meshes.set(id, object);
    }
  });
  assert.deepEqual(names, new Set(assembly.parts.map((part) => part.id)));
  assert.equal(names.size, assembly.parts.length);
  for (const part of assembly.parts) {
    const [x, y, z, length, width, height] = part.box_mm;
    const box = new Box3().setFromObject(meshes.get(part.id));
    const expected = [
      [x, y, z],
      [x + length, y + width, z + height],
    ];
    for (const [actual, values] of [
      [box.min, expected[0]],
      [box.max, expected[1]],
    ]) {
      for (const [axis, value] of ["x", "y", "z"].map((axis, index) => [
        axis,
        values[index],
      ])) {
        assert.ok(
          Math.abs(actual[axis] - value) < 0.25,
          `${model}: ${part.id} ${axis} bounds drift`,
        );
      }
    }
  }
  if (model !== "assembly") {
    assert.equal(assembly.component_coverage.length, 22);
    assert.ok(
      assembly.component_coverage.every((role) => role.concept_part_ids.length),
    );
  }
  console.log(`PASS: ${model} glTF loads ${names.size} distinct meshes`);
}
for (const [modelName, proofName] of [
  ["concept", "proof"],
  ["memory-8x16", "memory-8x16-proof"],
  ["memory-8x16-compact", "memory-8x16-compact-proof"],
  ["phone-fit-conflict", "phone-fit-conflict-proof"],
  ["usb4525-outline", "usb4525-outline-proof"],
  ["lp4473109-pack-outline", "lp4473109-pack-outline-proof"],
]) {
  const proof = JSON.parse(
    readFileSync(resolve(root, `public/${proofName}.json`), "utf8"),
  );
  const concept = JSON.parse(
    readFileSync(resolve(root, `public/${modelName}.json`), "utf8"),
  );
  assert.deepEqual(
    new Set(proof.parts.map((part) => part.id)),
    new Set(concept.parts.map((part) => part.id)),
  );
  assert.ok(
    proof.parts.every((part) => Object.values(part.checks).every(Boolean)),
  );
  assert.equal(proof.summary.parts_checked, concept.parts.length);
  assert.deepEqual(
    new Set(proof.roles.map((role) => role.id)),
    new Set(concept.component_coverage.map((role) => role.id)),
  );
  assert.equal(proof.summary.keepout_conflicts, proof.keepout_conflicts.length);
  if (modelName === "phone-fit-conflict") {
    assert.equal(proof.summary.interferences, 4);
    assert.equal(proof.phone_extension.status, "mechanical_relayout_required");
  }
  if (modelName === "usb4525-outline") {
    assert.equal(proof.summary.interferences, 1);
    assert.equal(proof.usb_candidate.mpn, "USB4525-03-A");
    assert.ok(
      proof.intersections.some(
        (item) =>
          item.kind === "interference" &&
          item.first === "frame_bottom" &&
          item.second === "usb_c_port_concept",
      ),
    );
  }
  if (modelName === "lp4473109-pack-outline") {
    assert.equal(proof.battery_pack_candidate.mpn, "LP4473109");
    assert.equal(
      proof.battery_pack_candidate.status,
      "rejected_current_layout_and_power",
    );
    assert.ok(
      proof.intersections.some(
        (item) =>
          item.kind === "interference" &&
          item.first === "battery_reference" &&
          item.second === "main_pcb_placeholder",
      ),
    );
  }
  console.log(`PASS: ${modelName} has ${proof.parts.length} CAD proof records`);
}
