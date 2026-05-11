#!/usr/bin/env python3
"""First-pass wireless charging physics screening model."""
from __future__ import annotations
import argparse, math
from common import bool_arg, fraction, mm3_to_cm3, positive_float, print_section

def parse_args():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--coil-diameter-mm',type=positive_float,default=45.0); p.add_argument('--coil-thickness-mm',type=positive_float,default=0.6); p.add_argument('--charging-power-w',type=positive_float,default=50.0); p.add_argument('--efficiency',type=fraction,default=0.75); p.add_argument('--rear-metal-present',type=bool_arg,default=True); return p.parse_args()

def main():
    a=parse_args(); area=math.pi*(a.coil_diameter_mm/2)**2; vol=mm3_to_cm3(area*a.coil_thickness_mm); input_power=a.charging_power_w/a.efficiency; loss=input_power-a.charging_power_w
    warnings=[]
    if loss>10: warnings.append('wireless charging loss heat is high and must be spread away from battery hot spots')
    if a.rear_metal_present: warnings.append('rear metal blocks or heats under inductive charging unless broken by RF/charging window or ferrite stack')
    if a.charging_power_w>=50: warnings.append('50 W wireless charging is aggressive for phone-class temperature limits')
    print('Wireless charging physics model')
    print_section('inputs',[f'coil_diameter_mm: {a.coil_diameter_mm:.0f}',f'coil_thickness_mm: {a.coil_thickness_mm:.1f}',f'charging_power_w: {a.charging_power_w:.0f}',f'efficiency: {a.efficiency:.2f}',f'rear_metal_present: {a.rear_metal_present}'])
    print_section('assumptions',['coil is circular and represented by its outer diameter','coil volume excludes ferrite, adhesives, alignment magnets, shielding, and controller electronics','loss heat equals input electrical power minus delivered charging power','rear material compatibility is binary screening, not electromagnetic simulation'])
    print_section('formulas',['coil_area_mm2 = pi * (coil_diameter_mm / 2)^2','coil_volume_cm3 = coil_area_mm2 * coil_thickness_mm / 1000','input_power_W = charging_power_W / efficiency','charging_loss_heat_W = input_power_W - charging_power_W'])
    print_section('outputs',[f'coil_area_mm2: {area:.0f}',f'coil_volume_cm3: {vol:.1f}',f'input_power_w_estimate: {input_power:.0f}',f'charging_loss_heat_w: {loss:.0f}',f'rear_material_compatibility_warning: {"metal rear requires window/ferrite isolation" if a.rear_metal_present else "rear material input is not metal"}',f'conflict_with_metal_thermal_frame: {"yes" if a.rear_metal_present else "reduced"}'])
    print_section('warnings',warnings); print('confidence: medium for loss arithmetic; low for electromagnetic coupling and temperature'); print('basis: first-pass inductive charging geometry and heat screen'); print('primary blocker: wireless charge heat and metal rear/thermal-frame compatibility'); return 0
if __name__=='__main__': raise SystemExit(main())
