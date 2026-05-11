#!/usr/bin/env python3
"""First-pass storage package physics screening model."""
from __future__ import annotations
import argparse, math
from common import mm3_to_cm3, positive_float, print_section

def parse_args():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--capacity-tb',type=positive_float,default=4.0); p.add_argument('--tb-per-package',type=positive_float,default=2.0); p.add_argument('--package-area-mm2',type=positive_float,default=180.0); p.add_argument('--package-thickness-mm',type=positive_float,default=1.5); p.add_argument('--idle-power-w',type=positive_float,default=0.5); p.add_argument('--active-power-w',type=positive_float,default=5.0); return p.parse_args()

def main():
    a=parse_args(); count=math.ceil(a.capacity_tb/a.tb_per_package); area=count*a.package_area_mm2; vol=mm3_to_cm3(area*a.package_thickness_mm); idle=count*a.idle_power_w; active=count*a.active_power_w
    warnings=[]
    if active>=8: warnings.append('active storage heat can throttle sustained writes and warm nearby battery/display areas')
    if a.capacity_tb>=4: warnings.append('multi-TB phone storage is package-height, cost, and availability constrained')
    warnings.append('PCIe Gen5-class storage increases controller thermal risk unless bandwidth is capped or well spread')
    print('Storage package physics model')
    print_section('inputs',[f'capacity_tb: {a.capacity_tb:.0f}',f'tb_per_package: {a.tb_per_package:.0f}',f'package_area_mm2: {a.package_area_mm2:.0f}',f'package_thickness_mm: {a.package_thickness_mm:.1f}',f'idle_power_w_per_package: {a.idle_power_w:.1f}',f'active_power_w_per_package: {a.active_power_w:.1f}'])
    print_section('assumptions',['storage package count is rounded up to whole packages','power values are per package and include controller/NAND activity as a screening placeholder','package area excludes PMIC, shielding, decoupling, and thermal pad clearance','capacity is raw installed storage before filesystem reserves and wear management'])
    print_section('formulas',['package_count = ceil(capacity_TB / TB_per_package)','total_area_mm2 = package_count * package_area_mm2','volume_cm3 = total_area_mm2 * package_thickness_mm / 1000','idle_power_W = package_count * idle_power_W_per_package','active_power_W = package_count * active_power_W_per_package'])
    print_section('outputs',[f'estimated_package_count: {count}',f'total_area_mm2: {area:.0f}',f'total_volume_cm3: {vol:.1f}',f'idle_power_w: {idle:.1f}',f'active_power_w: {active:.0f}',f'active_heat_warning_threshold_w: 8'])
    print_section('warnings',warnings); print('confidence: medium for count arithmetic; low for sustained bandwidth and controller thermals'); print('basis: first-pass NAND/UFS/NVMe-like package screening'); print('primary blocker: sustained storage heat and package placement near battery, SoC, and RF zones'); return 0
if __name__=='__main__': raise SystemExit(main())
