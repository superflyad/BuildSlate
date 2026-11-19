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
const assembly = JSON.parse(
  readFileSync(resolve(root, "public/assembly.json"), "utf8"),
);
const geometry = readFileSync(resolve(root, "public/assembly.gltf"), "utf8");
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
        Math.abs(actual[axis] - value) < 0.001,
        `${part.id} ${axis} bounds drift`,
      );
    }
  }
}
console.log(`PASS: glTF loads ${names.size} distinct assembly meshes`);
