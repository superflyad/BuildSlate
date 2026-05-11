#!/usr/bin/env python3
"""First-pass SoC/NPU package physics screening model."""
from __future__ import annotations
import argparse
from common import mm2_to_cm2, mm3_to_cm3, positive_float, print_section

def parse_args():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--package-length-mm',type=positive_float,default=18.0); p.add_argument('--package-width-mm',type=positive_float,default=18.0); p.add_argument('--package-thickness-mm',type=positive_float,default=1.2); p.add_argument('--sustained-power-w',type=positive_float,default=12.0); p.add_argument('--peak-power-w',type=positive_float,default=28.0); p.add_argument('--npu-tops',type=positive_float,default=100.0); return p.parse_args()

def main():
    a=parse_args(); area=a.package_length_mm*a.package_width_mm; area_cm2=mm2_to_cm2(area); vol=mm3_to_cm3(area*a.package_thickness_mm); sustained_density=a.sustained_power_w/area_cm2; peak_density=a.peak_power_w/area_cm2; contact_sust=a.sustained_power_w/4.0; contact_peak=a.peak_power_w/4.0
    warnings=[]
    if peak_density>5: warnings.append('peak package heat flux is high for passive phone-class spreading')
    if a.peak_power_w/a.sustained_power_w>2: warnings.append('peak power is more than 2x sustained; throttling or short bursts should be expected')
    if a.npu_tops>=100: warnings.append('100 TOPS-class claim needs memory bandwidth and sustained thermal validation')
    print('SoC/NPU package physics model')
    print_section('inputs',[f'package_length_mm: {a.package_length_mm:.0f}',f'package_width_mm: {a.package_width_mm:.0f}',f'package_thickness_mm: {a.package_thickness_mm:.1f}',f'sustained_power_w: {a.sustained_power_w:.0f}',f'peak_power_w: {a.peak_power_w:.0f}',f'npu_tops: {a.npu_tops:.0f}'])
    print_section('assumptions',['package footprint is rectangular and approximates thermal contact footprint','passive spreading target is roughly 4 W/cm2 at the contact patch for screening','package volume excludes nearby PMIC, memory, shields, and underfill allowances','TOPS is reported as capability context, not a performance guarantee'])
    print_section('formulas',['package_area_mm2 = length_mm * width_mm','power_density_W_per_cm2 = power_W / (package_area_mm2 / 100)','heat_flux_W_per_cm2 = package_power_W / package_area_cm2','required_contact_area_cm2 = power_W / 4 W_per_cm2','package_volume_cm3 = package_area_mm2 * thickness_mm / 1000'])
    print_section('outputs',[f'package_area_mm2: {area:.0f}',f'package_volume_cm3: {vol:.1f}',f'sustained_power_density_w_per_cm2: {sustained_density:.1f}',f'peak_heat_flux_w_per_cm2: {peak_density:.1f}',f'required_contact_area_cm2_sustained: {contact_sust:.1f}',f'required_contact_area_cm2_peak: {contact_peak:.1f}',f'npu_tops_context: {a.npu_tops:.0f}'])
    print_section('warnings',warnings); print('confidence: medium for package arithmetic; low for die stack and real thermal resistance'); print('basis: first-pass phone-class passive thermal spreading screen'); print('primary blocker: sustained SoC/NPU heat removal without throttling or hot spots'); return 0
if __name__=='__main__': raise SystemExit(main())
