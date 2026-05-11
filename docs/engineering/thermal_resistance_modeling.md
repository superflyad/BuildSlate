# Thermal Resistance Modeling

Heat density alone is insufficient for engineering review because it only reports how much power is concentrated in an area. It does not say whether that heat can move from the silicon hotspot to a larger exterior surface quickly enough to keep the product touch-safe. Two designs can have the same hotspot heat density but very different temperatures if one has a lower-resistance path through interfaces, spreaders, frame materials, and the exterior skin.

Thermal resistance describes the temperature rise required to move a watt of heat through a path. In this repository it is reported in °C/W for a first-pass conduction stack. Lower resistance means less temperature rise for the same heat load.

The basic layer equation is:

```text
R = L / (kA)
```

Where `L` is layer thickness in meters, `k` is thermal conductivity in W/mK, and `A` is conduction area in square meters. The modeled layer temperature rise is `delta_T = heat_W * R`.

Contact resistance matters because real assemblies are not perfect mathematical solids. Surface roughness, flatness, clamping pressure, adhesive thickness, oxide layers, TIM quality, and assembly variation can add meaningful resistance at interfaces. In thin devices, an interface can dominate the temperature rise even when the nominal bulk material looks excellent.

Graphite is anisotropic. Its in-plane thermal conductivity can be very high, which is useful for spreading heat laterally, but its through-thickness conductivity is much lower. A single conductivity value is therefore a simplification and must not be read as a complete graphite thermal model.

Vapor chamber effective conductivity is also a simplification. A vapor chamber can spread heat much better than a solid copper plate of the same thickness in some regimes, but its effective performance depends on wick design, fluid charge, orientation, condenser area, heat load, and geometry. The effective conductivity used by the screening model is not bulk copper conductivity.

Skin temperature is the real user-facing limit because users touch the exterior surface, not the die. A design that keeps silicon below a maximum junction temperature can still be unacceptable if it drives the enclosure above comfort or safety limits. BuildSlate therefore reports estimated skin temperature and skin heat flux as screening outputs.

`engineering/component_models/thermal_resistance_network.py` is a screening model, not CFD. It does not solve 3D spreading, transient heat storage, airflow, hand grip, material nonuniformity, firmware control loops, or detailed mechanical contacts. Its purpose is to make assumptions explicit and flag paths that need CAD, supplier data, test coupons, or solver-grade thermal analysis.
