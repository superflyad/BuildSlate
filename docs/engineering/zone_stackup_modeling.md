# Zone Stackup Modeling

Phone thickness is not one uniform global stack. A single total thickness number can hide local conflicts because different regions contain different parts, clearances, and keepouts. The display region, battery region, compute region, storage region, camera region, wireless charging region, and antenna edge each have different z-height pressures.

Zone-based stackup modeling checks those local conflicts separately. A battery zone must account for the cell, pack wrapper, swelling allowance, and rear housing. A SoC/memory zone must reserve room for PCB thickness, package height, vapor chamber or graphite, and interface allowances. A storage zone may have different package and spreader needs. A camera zone can be dominated by module depth and folded-optics prism path allowances. A wireless charging zone must account for the battery, coil, ferrite or shield layer, and housing. An antenna edge zone must preserve clearance and frame geometry.

This matters because the global thickness can look acceptable while one local zone fails. For example, an average stack may fit an 8.8 mm target, while the camera zone exceeds the target or the wireless charging region leaves too little clearance above a battery pack. Those failures are integration blockers even if the nominal product thickness looks plausible.

`engineering/component_models/zone_stackup.py` is a nominal arithmetic screen. It is useful for exposing contradictions early, but it is not a substitute for mechanical CAD. CAD is eventually required to model local cutouts, stepped housings, tolerance stackups, fasteners, flex cables, seals, adhesive squeeze, bend radii, thermal compression, battery swelling envelopes, antenna keepouts, and manufacturing constraints.
