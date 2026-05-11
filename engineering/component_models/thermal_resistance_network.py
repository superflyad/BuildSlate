#!/usr/bin/env python3
"""First-pass thermal resistance network screening model."""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from common import mm2_to_cm2, positive_float, print_section


@dataclass(frozen=True)
class ThermalLayer:
    name: str
    thickness_mm: float
    conductivity_w_mk: float
    note: str

    def resistance_c_per_w(self, area_m2: float) -> float:
        thickness_m = self.thickness_mm / 1000.0
        return thickness_m / (self.conductivity_w_mk * area_m2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--heat-w", type=positive_float, default=28.0)
    parser.add_argument("--hotspot-area-mm2", type=positive_float, default=324.0)
    parser.add_argument("--skin-area-cm2", type=positive_float, default=250.0)
    parser.add_argument("--ambient-c", type=float, default=25.0)
    parser.add_argument("--max-skin-c", type=positive_float, default=43.0)
    parser.add_argument("--tim-thickness-mm", type=positive_float, default=0.08)
    parser.add_argument("--tim-k-w-mk", type=positive_float, default=5.0)
    parser.add_argument("--vapor-thickness-mm", type=positive_float, default=0.8)
    parser.add_argument("--vapor-k-effective-w-mk", type=positive_float, default=5000.0)
    parser.add_argument("--graphite-thickness-mm", type=positive_float, default=0.1)
    parser.add_argument("--graphite-k-in-plane-w-mk", type=positive_float, default=900.0)
    parser.add_argument("--frame-thickness-mm", type=positive_float, default=0.8)
    parser.add_argument("--frame-k-w-mk", type=positive_float, default=170.0)
    parser.add_argument("--contact-resistance-cm2k-w", type=positive_float, default=1.0)
    return parser.parse_args()


def warning_rows(warnings: list[str]) -> list[str]:
    if not warnings:
        return ["none"]
    return [f"- {warning}" for warning in warnings]


def main() -> int:
    args = parse_args()
    hotspot_area_m2 = args.hotspot_area_mm2 * 1e-6
    hotspot_area_cm2 = mm2_to_cm2(args.hotspot_area_mm2)
    skin_heat_flux_w_cm2 = args.heat_w / args.skin_area_cm2

    layers = [
        ThermalLayer("TIM", args.tim_thickness_mm, args.tim_k_w_mk, "through-thickness interface layer"),
        ThermalLayer(
            "copper_vapor_chamber",
            args.vapor_thickness_mm,
            args.vapor_k_effective_w_mk,
            "effective spreading value, not bulk copper conductivity",
        ),
        ThermalLayer(
            "graphite_spreader",
            args.graphite_thickness_mm,
            args.graphite_k_in_plane_w_mk,
            "anisotropic in-plane spreading approximation",
        ),
        ThermalLayer("aluminum_magnesium_frame", args.frame_thickness_mm, args.frame_k_w_mk, "frame conduction path"),
    ]

    layer_results = []
    total_resistance_c_per_w = 0.0
    for layer in layers:
        resistance = layer.resistance_c_per_w(hotspot_area_m2)
        delta_t = args.heat_w * resistance
        total_resistance_c_per_w += resistance
        layer_results.append((layer, resistance, delta_t))

    contact_resistance_c_per_w = args.contact_resistance_cm2k_w / hotspot_area_cm2
    contact_delta_t_c = args.heat_w * contact_resistance_c_per_w
    total_resistance_c_per_w += contact_resistance_c_per_w
    estimated_skin_delta_t_c = args.heat_w * total_resistance_c_per_w
    estimated_skin_c = args.ambient_c + estimated_skin_delta_t_c
    passed = estimated_skin_c <= args.max_skin_c

    warnings = []
    if estimated_skin_c > args.max_skin_c:
        warnings.append("estimated skin temperature exceeds max skin temperature")
    if skin_heat_flux_w_cm2 > 0.05:
        warnings.append("skin heat flux exceeds 0.05 W/cm2 comfort screening threshold")
    if total_resistance_c_per_w > 0.6:
        warnings.append("total thermal resistance is too high for sustained AI-class heat without throttling")
    if args.heat_w >= 28.0 and args.hotspot_area_mm2 < 400.0:
        warnings.append("hotspot area is small for a 28 W-class load")
    if contact_resistance_c_per_w > max(resistance for _, resistance, _ in layer_results):
        warnings.append("contact resistance dominates the modeled layer stack")

    per_layer_resistance_rows = [
        f"{layer.name}: {resistance:.4f} C/W ({layer.note})" for layer, resistance, _ in layer_results
    ]
    per_layer_resistance_rows.append(f"contact_interfaces: {contact_resistance_c_per_w:.4f} C/W")
    per_layer_delta_rows = [f"{layer.name}: {delta_t:.2f} C" for layer, _, delta_t in layer_results]
    per_layer_delta_rows.append(f"contact_interfaces: {contact_delta_t_c:.2f} C")

    print("Thermal resistance network model")
    print_section(
        "inputs",
        [
            f"heat_w: {args.heat_w:.1f}",
            f"hotspot_area_mm2: {args.hotspot_area_mm2:.1f}",
            f"skin_area_cm2: {args.skin_area_cm2:.1f}",
            f"ambient_c: {args.ambient_c:.1f}",
            f"max_skin_c: {args.max_skin_c:.1f}",
            f"tim_thickness_mm: {args.tim_thickness_mm:.3f}",
            f"tim_k_w_mk: {args.tim_k_w_mk:.1f}",
            f"vapor_thickness_mm: {args.vapor_thickness_mm:.3f}",
            f"vapor_k_effective_w_mk: {args.vapor_k_effective_w_mk:.0f}",
            f"graphite_thickness_mm: {args.graphite_thickness_mm:.3f}",
            f"graphite_k_in_plane_w_mk: {args.graphite_k_in_plane_w_mk:.0f}",
            f"frame_thickness_mm: {args.frame_thickness_mm:.3f}",
            f"frame_k_w_mk: {args.frame_k_w_mk:.0f}",
            f"contact_resistance_cm2k_w: {args.contact_resistance_cm2k_w:.2f}",
        ],
    )
    print_section(
        "assumptions",
        [
            "1D screening path: SoC/NPU hotspot -> TIM -> vapor chamber -> graphite -> frame -> exterior skin",
            "spreading is collapsed into effective layer conductivities and contact resistance",
            "vapor chamber effective conductivity is not the same as bulk copper conductivity",
            "graphite is anisotropic; in-plane spreading and through-thickness transfer differ",
            "contact resistance can dominate real assemblies",
            "model is not CFD and does not represent transient control, airflow, grip, or local skin nonuniformity",
        ],
    )
    print_section(
        "formulas",
        [
            "A_m2 = hotspot_area_mm2 * 1e-6",
            "R_layer = L / (k * A)",
            "contact_R_total = contact_resistance_cm2k_w / hotspot_area_cm2",
            "delta_T_layer = heat_w * R_layer",
            "skin_heat_flux_w_cm2 = heat_w / skin_area_cm2",
            "estimated_skin_temperature_C = ambient_C + heat_W * total_R_C_per_W",
        ],
    )
    print_section("per-layer thermal resistance", per_layer_resistance_rows)
    print_section("per-layer delta T", per_layer_delta_rows)
    print_section(
        "outputs",
        [
            f"total_thermal_resistance_c_per_w: {total_resistance_c_per_w:.4f}",
            f"estimated_skin_delta_t_above_ambient_c: {estimated_skin_delta_t_c:.2f}",
            f"estimated_skin_temperature_c: {estimated_skin_c:.2f}",
            f"skin_heat_flux_w_cm2: {skin_heat_flux_w_cm2:.3f}",
            f"pass_max_skin_temp: {passed}",
        ],
    )
    print_section("warnings", warning_rows(warnings))
    print("confidence: low to medium; suitable for first-pass heat-path risk ranking only")
    print("basis: modeled estimate using 1D conduction, effective spreading conductivities, and assumed contact resistance")
    print("primary blocker: sustained high-power hotspot rejection while keeping exterior skin touch-safe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
