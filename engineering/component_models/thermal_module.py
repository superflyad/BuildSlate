#!/usr/bin/env python3
"""First-pass thermal module physics screening model."""
from __future__ import annotations
import argparse
from common import fraction, mm3_to_cm3, positive_float, print_section

def parse_args():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--device-length-mm',type=positive_float,default=180.0); p.add_argument('--device-width-mm',type=positive_float,default=95.0); p.add_argument('--vapor-chamber-area-fraction',type=fraction,default=0.45); p.add_argument('--vapor-chamber-thickness-mm',type=positive_float,default=0.8); p.add_argument('--graphite-area-fraction',type=fraction,default=0.75); p.add_argument('--graphite-thickness-mm',type=positive_float,default=0.1); p.add_argument('--sustained-w',type=positive_float,default=28.0); return p.parse_args()

def main():
    a=parse_args(); face=a.device_length_mm*a.device_width_mm; vc_area=face*a.vapor_chamber_area_fraction; gr_area=face*a.graphite_area_fraction; vc_vol=mm3_to_cm3(vc_area*a.vapor_chamber_thickness_mm); gr_vol=mm3_to_cm3(gr_area*a.graphite_thickness_mm); tim_vol=mm3_to_cm3(350*0.08); vc_mass=vc_vol*3.5; gr_mass=gr_vol*1.8; tim_mass=tim_vol*2.5; mass=vc_mass+gr_mass+tim_mass; coverage=max(a.vapor_chamber_area_fraction,a.graphite_area_fraction)*100; passive_ref=8.0
    warnings=[]
    if a.sustained_w>passive_ref*2: warnings.append('sustained heat is far above conservative passive phone reference and likely needs throttling or active cooling')
    if a.vapor_chamber_thickness_mm>=0.8: warnings.append('vapor chamber thickness consumes meaningful z-height in an 8-9 mm device')
    if coverage<70: warnings.append('heat spreading coverage may be too small to avoid localized hot spots')
    print('Thermal module physics model')
    print_section('inputs',[f'device_length_mm: {a.device_length_mm:.0f}',f'device_width_mm: {a.device_width_mm:.0f}',f'vapor_chamber_area_fraction: {a.vapor_chamber_area_fraction:.2f}',f'vapor_chamber_thickness_mm: {a.vapor_chamber_thickness_mm:.1f}',f'graphite_area_fraction: {a.graphite_area_fraction:.2f}',f'graphite_thickness_mm: {a.graphite_thickness_mm:.1f}',f'sustained_w: {a.sustained_w:.0f}'])
    print_section('assumptions',['vapor chamber effective density is 3.5 g/cm3 including walls and wick voids','graphite sheet density is 1.8 g/cm3','TIM patch is approximated as 350 mm2 by 0.08 mm','passive reference is 8 W sustained for conservative phone-class comfort screening'])
    print_section('formulas',['component_area_mm2 = device_face_area_mm2 * area_fraction','volume_cm3 = area_mm2 * thickness_mm / 1000','mass_g = volume_cm3 * density_g_per_cm3','heat_path_coverage_percent = max(vapor_chamber_fraction, graphite_fraction) * 100','passive_ratio = sustained_W / passive_reference_W'])
    print_section('outputs',[f'vapor_chamber_volume_cm3: {vc_vol:.1f}',f'vapor_chamber_mass_g: {vc_mass:.0f}',f'graphite_sheet_volume_cm3: {gr_vol:.1f}',f'graphite_sheet_mass_g: {gr_mass:.0f}',f'tim_layer_volume_cm3_estimate: {tim_vol:.2f}',f'combined_thermal_module_mass_g: {mass:.0f}',f'heat_path_coverage_percent: {coverage:.0f}',f'sustained_to_passive_reference_ratio: {a.sustained_w/passive_ref:.1f}x'])
    print_section('warnings',warnings); print('confidence: medium for volume/mass; low for thermal resistance and skin temperature'); print('basis: first-pass passive spreading module screen'); print('primary blocker: rejecting sustained heat while staying thin, light, and touch-safe'); return 0
if __name__=='__main__': raise SystemExit(main())
