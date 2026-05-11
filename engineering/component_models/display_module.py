#!/usr/bin/env python3
"""First-pass display module physics screening model."""
from __future__ import annotations
import argparse, math
from common import mm3_to_cm3, positive_float, print_section

def parse_args():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--diagonal-in',type=positive_float,default=7.5); p.add_argument('--aspect-width',type=positive_float,default=16.0); p.add_argument('--aspect-height',type=positive_float,default=10.0)
    p.add_argument('--device-length-mm',type=positive_float,default=180.0); p.add_argument('--device-width-mm',type=positive_float,default=95.0); p.add_argument('--thickness-mm',type=positive_float,default=1.2); p.add_argument('--power-w',type=positive_float,default=3.5)
    return p.parse_args()

def main():
    a=parse_args(); diag_mm=a.diagonal_in*25.4; aspect_diag=math.hypot(a.aspect_width,a.aspect_height)
    active_w=diag_mm*a.aspect_width/aspect_diag; active_h=diag_mm*a.aspect_height/aspect_diag; active_area=active_w*active_h
    module_area=active_area*1.08; device_face=a.device_length_mm*a.device_width_mm; surface_pct=active_area/device_face*100
    vol_low=mm3_to_cm3(module_area*a.thickness_mm*0.9); vol_high=mm3_to_cm3(module_area*a.thickness_mm*1.2)
    mass_low=module_area*0.0018; mass_high=module_area*0.0030; power_low=a.power_w*0.6; power_high=a.power_w*1.8
    warnings=[]
    if surface_pct>80: warnings.append('active display consumes most of the front face; bezels, corners, cameras, and antennas are constrained')
    if power_high>6: warnings.append('high brightness or high refresh operation creates a major front-surface heat load')
    if a.thickness_mm<1.0: warnings.append('module thickness is below conservative allowance for cover interfaces and touch stack')
    if not warnings: warnings.append('no aggressive warning from defaults; optical stack and supplier data remain required')
    print('Display module physics model')
    print_section('inputs',[f'diagonal_in: {a.diagonal_in:.1f}',f'aspect_ratio: {a.aspect_width:.0f}:{a.aspect_height:.0f}',f'device_length_mm: {a.device_length_mm:.0f}',f'device_width_mm: {a.device_width_mm:.0f}',f'thickness_mm: {a.thickness_mm:.1f}',f'power_w: {a.power_w:.1f}'])
    print_section('assumptions',['active area is derived from diagonal and rectangular aspect ratio','module area adds 8% for driver border, rounded corners, and bonding margin','mass range is 1.8-3.0 mg/mm2 for display/touch support stack','power range is 0.6-1.8x nominal for content, brightness, refresh, and APL'])
    print_section('formulas',['diagonal_mm = diagonal_in * 25.4','active_width_mm = diagonal_mm * aspect_width / sqrt(aspect_width^2 + aspect_height^2)','active_height_mm = diagonal_mm * aspect_height / sqrt(aspect_width^2 + aspect_height^2)','module_area_mm2 = active_area_mm2 * 1.08','volume_cm3 = module_area_mm2 * thickness_mm / 1000','surface_percent = active_area_mm2 / device_face_area_mm2 * 100'])
    print_section('outputs',[f'active_width_mm: {active_w:.0f}',f'active_height_mm: {active_h:.0f}',f'active_area_mm2: {active_area:.0f}',f'module_area_mm2: {module_area:.0f}',f'estimated_mass_g_range: {mass_low:.0f}-{mass_high:.0f}',f'estimated_volume_cm3_range: {vol_low:.0f}-{vol_high:.0f}',f'power_w_range: {power_low:.1f}-{power_high:.1f}',f'heat_load_w_range: {power_low:.1f}-{power_high:.1f}',f'device_face_coverage_percent: {surface_pct:.0f}'])
    print_section('warnings',warnings); print('confidence: medium for geometry; low for supplier-specific OLED/LCD mass and power'); print('basis: phone/tablet-class display screening assumptions'); print('primary blocker: front-face area, display heat, camera openings, and border electronics packaging'); return 0
if __name__=='__main__': raise SystemExit(main())
