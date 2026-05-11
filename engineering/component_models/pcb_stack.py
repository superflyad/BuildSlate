#!/usr/bin/env python3
"""First-pass PCB stack physics screening model."""
from __future__ import annotations
import argparse
from common import fraction, mm3_to_cm3, positive_float, print_section

def parse_args():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--device-length-mm',type=positive_float,default=180.0); p.add_argument('--device-width-mm',type=positive_float,default=95.0); p.add_argument('--pcb-area-fraction',type=fraction,default=0.35); p.add_argument('--pcb-thickness-mm',type=positive_float,default=0.8); p.add_argument('--component-area-mm2',type=positive_float,default=3500.0); return p.parse_args()

def main():
    a=parse_args(); face=a.device_length_mm*a.device_width_mm; pcb_area=face*a.pcb_area_fraction; util=a.component_area_mm2/pcb_area*100; vol=mm3_to_cm3(pcb_area*a.pcb_thickness_mm); mass_low=vol*1.6; mass_high=vol*2.1
    risk='low'
    if util>75: risk='very high'
    elif util>55: risk='high'
    elif util>35: risk='medium'
    warnings=[]
    if util>55: warnings.append('component occupancy leaves limited room for routing, shields, connectors, and keep-outs')
    if a.pcb_thickness_mm<0.8: warnings.append('thin PCB increases layer, via, warpage, and assembly risk')
    if risk in {'high','very high'}: warnings.append('estimated layer count likely rises because dense memory/SoC/RF routing competes for area')
    if not warnings: warnings.append('no aggressive warning from defaults; board outline and placement still unvalidated')
    print('PCB stack physics model')
    print_section('inputs',[f'device_length_mm: {a.device_length_mm:.0f}',f'device_width_mm: {a.device_width_mm:.0f}',f'pcb_area_fraction: {a.pcb_area_fraction:.2f}',f'pcb_thickness_mm: {a.pcb_thickness_mm:.1f}',f'component_area_mm2: {a.component_area_mm2:.0f}'])
    print_section('assumptions',['available PCB area is a fraction of device face after battery, camera, speaker, and antenna keep-outs','component occupancy excludes routing channels, shields, test pads, board-to-board connectors, and flex tails','FR-4/HDI effective density range is 1.6-2.1 g/cm3','layer-count risk is inferred from utilization, not routed CAD'])
    print_section('formulas',['device_face_area_mm2 = length_mm * width_mm','available_pcb_area_mm2 = device_face_area_mm2 * pcb_area_fraction','utilization_percent = component_area_mm2 / available_pcb_area_mm2 * 100','pcb_volume_cm3 = available_pcb_area_mm2 * pcb_thickness_mm / 1000','pcb_mass_g = pcb_volume_cm3 * density_g_per_cm3'])
    print_section('outputs',[f'available_pcb_area_mm2: {pcb_area:.0f}',f'component_occupancy_mm2: {a.component_area_mm2:.0f}',f'utilization_percent: {util:.0f}',f'estimated_layer_count_risk: {risk}',f'pcb_volume_cm3: {vol:.1f}',f'pcb_mass_g_range: {mass_low:.0f}-{mass_high:.0f}'])
    print_section('warnings',warnings); print('confidence: medium for area arithmetic; low for actual routing feasibility'); print('basis: first-pass HDI PCB area and density screening'); print('primary blocker: dense routing around SoC, memory, storage, RF, cameras, and connectors'); return 0
if __name__=='__main__': raise SystemExit(main())
