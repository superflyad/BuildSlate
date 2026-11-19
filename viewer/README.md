# Assembly viewer

The viewer is a read-only local web application for the provisional Slate Pocket v1R assembly. It shows enclosure and internal planning boxes, PCB placements, keepouts, local stack data, and program gates from generated repository assets.

```bash
python -m buildslate.assembly
cd viewer
npm ci
npm run dev
```

Use `npm run build` to produce a static site in `dist/`. No account, API, or backend is required. The build includes generated JSON and glTF from `public/`.

Controls: drag to orbit, scroll to zoom, click a part or list entry to inspect, filter by system or search term, switch camera views, explode the assembly, hide the exterior, and display keepouts or deferred concepts. The Program tab shows current gates and blockers.

Every solid is a planning box. This viewer cannot establish fit, part selection, thermal or RF performance, or release readiness. Replace boxes only through a reviewed source and geometry import workflow.
