#!/usr/bin/env python3
"""First-pass structural stackup physics screening model."""
from __future__ import annotations
import argparse
from common import positive_float, print_section

def parse_args():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--target-thickness-mm',type=positive_float,default=8.8); p.add_argument('--cover-glass-mm',type=positive_float,default=0.6); p.add_argument('--display-mm',type=positive_float,default=1.2); p.add_argument('--adhesive-mm',type=positive_float,default=0.2); p.add_argument('--vapor-chamber-mm',type=positive_float,default=0.8); p.add_argument('--pcb-mm',type=positive_float,default=0.8); p.add_argument('--max-package-mm',type=positive_float,default=1.5); p.add_argument('--battery-mm',type=positive_float,default=4.5); p.add_argument('--rear-housing-mm',type=positive_float,default=0.8); return p.parse_args()

def main():
    a=parse_args(); layers=[('cover_glass_mm',a.cover_glass_mm),('display_mm',a.display_mm),('adhesive_mm',a.adhesive_mm),('vapor_chamber_mm',a.vapor_chamber_mm),('pcb_mm',a.pcb_mm),('max_package_mm',a.max_package_mm),('battery_mm',a.battery_mm),('rear_housing_mm',a.rear_housing_mm)]; total=sum(v for _,v in layers); remaining=a.target_thickness_mm-total
    warnings=[]
    if remaining<0: warnings.append('stack exceeds target thickness before camera bumps, ribs, tolerances, seals, and local reinforcements')
    if a.battery_mm+a.max_package_mm+a.pcb_mm>6.5: warnings.append('battery, PCB, and package rigid zones cannot all occupy the same z-stack everywhere')
    warnings.append('rigid-zone overlap must be resolved by side-by-side placement, pockets, steps, flexes, or local thickness growth')
    print('Structural stackup physics model')
    print_section('inputs',[f'target_thickness_mm: {a.target_thickness_mm:.1f}',*(f'{name}: {value:.1f}' for name,value in layers)])
    print_section('assumptions',['layers are summed as a worst-case local vertical stack','no credit is taken for cavities, offsets, local recesses, compression, or curved surfaces','manufacturing tolerances, seals, screws, ribs, camera bump, and drop margins are not included','overlap warning is qualitative until CAD placement zones exist'])
    print_section('formulas',['stacked_thickness_mm = sum(layer_thickness_mm)','remaining_thickness_mm = target_thickness_mm - stacked_thickness_mm','overflow_thickness_mm = max(0, stacked_thickness_mm - target_thickness_mm)'])
    outputs=[f'stacked_thickness_mm: {total:.1f}',f'target_thickness_mm: {a.target_thickness_mm:.1f}']
    if remaining>=0: outputs.append(f'remaining_thickness_mm: {remaining:.1f}')
    else: outputs.append(f'overflow_thickness_mm: {-remaining:.1f}')
    outputs.append('rigid_zone_overlap_warning: battery/PCB/package stack should not be assumed co-located')
    print_section('outputs',outputs); print_section('warnings',warnings); print('confidence: medium for arithmetic; low for real mechanical packaging without CAD'); print('basis: first-pass local z-stack screening'); print('primary blocker: fitting battery, PCB packages, cooling, structure, and display within target thickness'); return 0
if __name__=='__main__': raise SystemExit(main())
