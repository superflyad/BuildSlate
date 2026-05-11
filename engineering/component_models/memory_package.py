#!/usr/bin/env python3
"""First-pass memory package physics screening model."""
from __future__ import annotations
import argparse, math
from common import mm3_to_cm3, positive_float, print_section

def parse_args():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--capacity-gb',type=positive_float,default=512.0); p.add_argument('--gb-per-package',type=positive_float,default=32.0); p.add_argument('--package-area-mm2',type=positive_float,default=120.0); p.add_argument('--package-thickness-mm',type=positive_float,default=1.2); p.add_argument('--idle-power-per-gb-w',type=positive_float,default=0.005); p.add_argument('--active-power-per-gb-w',type=positive_float,default=0.025); return p.parse_args()

def main():
    a=parse_args(); count=math.ceil(a.capacity_gb/a.gb_per_package); area=count*a.package_area_mm2; vol=mm3_to_cm3(area*a.package_thickness_mm); idle=a.capacity_gb*a.idle_power_per_gb_w; active=a.capacity_gb*a.active_power_per_gb_w
    warnings=[]
    if count>8: warnings.append('large package count creates severe board area, escape routing, and power rail pressure')
    if active>8: warnings.append('active memory power is high enough to be a major thermal load')
    if a.capacity_gb>=256: warnings.append('phone-class 256 GB+ RAM target is likely availability, cost, and packaging constrained')
    print('Memory package physics model')
    print_section('inputs',[f'capacity_gb: {a.capacity_gb:.0f}',f'gb_per_package: {a.gb_per_package:.0f}',f'package_area_mm2: {a.package_area_mm2:.0f}',f'package_thickness_mm: {a.package_thickness_mm:.1f}',f'idle_power_per_gb_w: {a.idle_power_per_gb_w:.3f}',f'active_power_per_gb_w: {a.active_power_per_gb_w:.3f}'])
    print_section('assumptions',['package count is rounded up to whole packages','per-GB power is a coarse LPDDR/HBM-like screening placeholder, not vendor data','area excludes decoupling capacitors, PMICs, routing escape, and keep-out spacing','capacity target is treated as raw installed memory, not usable OS memory'])
    print_section('formulas',['package_count = ceil(capacity_GB / GB_per_package)','total_area_mm2 = package_count * package_area_mm2','total_volume_cm3 = total_area_mm2 * package_thickness_mm / 1000','idle_power_W = capacity_GB * idle_power_per_GB_W','active_power_W = capacity_GB * active_power_per_GB_W','power_per_GB_W = total_power_W / capacity_GB'])
    print_section('outputs',[f'memory_required_gb: {a.capacity_gb:.0f}',f'estimated_package_count: {count}',f'total_package_area_mm2: {area:.0f}',f'total_package_volume_cm3: {vol:.1f}',f'idle_memory_power_w: {idle:.1f}',f'active_memory_power_w: {active:.0f}',f'active_power_per_gb_w: {active/a.capacity_gb:.3f}',f'routing_pressure_note: {count} high-pin-count packages require short routes and wide power delivery'])
    print_section('warnings',warnings); print('confidence: low because package capacity and availability are supplier-specific'); print('basis: capacity-driven first-pass memory packaging screen'); print('primary blocker: sourcing and routing enough high-density memory in phone-class board area'); return 0
if __name__=='__main__': raise SystemExit(main())
