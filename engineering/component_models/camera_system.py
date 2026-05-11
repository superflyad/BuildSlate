#!/usr/bin/env python3
"""First-pass camera system physics screening model."""
from __future__ import annotations
import argparse
from common import mm3_to_cm3, positive_float, print_section

def parse_args():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--rear-module-length-mm',type=positive_float,default=35.0); p.add_argument('--rear-module-width-mm',type=positive_float,default=12.0); p.add_argument('--rear-module-thickness-mm',type=positive_float,default=5.0); p.add_argument('--prism-path-length-mm',type=positive_float,default=40.0); p.add_argument('--device-thickness-mm',type=positive_float,default=8.8); return p.parse_args()

def main():
    a=parse_args(); vol=mm3_to_cm3(a.rear_module_length_mm*a.rear_module_width_mm*a.rear_module_thickness_mm); z_margin=a.device_thickness_mm-a.rear_module_thickness_mm-1.4; lateral_ratio=a.prism_path_length_mm/a.rear_module_length_mm
    warnings=[]
    if z_margin<2: warnings.append('rear camera z-height leaves little room for cover glass, OIS motion, adhesive, and housing')
    if a.prism_path_length_mm>35: warnings.append('long folded-optics prism path creates lateral packaging conflict with battery and PCB zones')
    warnings.append('front camera/display conflict requires notch, hole, under-display tradeoff, or bezel allocation')
    print('Camera system physics model')
    print_section('inputs',[f'rear_module_length_mm: {a.rear_module_length_mm:.0f}',f'rear_module_width_mm: {a.rear_module_width_mm:.0f}',f'rear_module_thickness_mm: {a.rear_module_thickness_mm:.1f}',f'prism_path_length_mm: {a.prism_path_length_mm:.0f}',f'device_thickness_mm: {a.device_thickness_mm:.1f}'])
    print_section('assumptions',['rear module is represented as a rectangular bounding box','1.4 mm is reserved for local cover, adhesive, decoration, and clearance above the module','prism path length is a packaging placeholder for folded optics, not an optical prescription','front camera is treated as a display aperture/keep-out conflict'])
    print_section('formulas',['rear_module_volume_cm3 = length_mm * width_mm * thickness_mm / 1000','z_margin_mm = device_thickness_mm - rear_module_thickness_mm - reserved_clearance_mm','lateral_camera_packaging_ratio = prism_path_length_mm / rear_module_length_mm'])
    print_section('outputs',[f'rear_camera_module_volume_cm3: {vol:.1f}',f'prism_path_length_estimate_mm: {a.prism_path_length_mm:.0f}',f'z_height_margin_after_clearance_mm: {z_margin:.1f}',f'lateral_camera_packaging_ratio: {lateral_ratio:.1f}x',f'front_camera_display_conflict_note: aperture or under-display camera reduces active display/design freedom'])
    print_section('warnings',warnings); print('confidence: low because camera modules are vendor-specific optical/mechanical assemblies'); print('basis: first-pass camera bounding-box and folded-path screen'); print('primary blocker: camera z-height and lateral folded-optics volume competing with battery and PCB'); return 0
if __name__=='__main__': raise SystemExit(main())
