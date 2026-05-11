#!/usr/bin/env python3
"""First-pass antenna/RF packaging physics screening model."""
from __future__ import annotations
import argparse
from common import percent, positive_float, print_section

def parse_args():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--device-perimeter-mm',type=positive_float,default=550.0); p.add_argument('--antenna-keepout-width-mm',type=positive_float,default=5.0); p.add_argument('--rf-window-area-mm2',type=positive_float,default=1200.0); p.add_argument('--metal-percent',type=percent,default=65.0); p.add_argument('--rf-friendly-percent',type=percent,default=25.0); return p.parse_args()

def main():
    a=parse_args(); keepout_area=a.device_perimeter_mm*a.antenna_keepout_width_mm; keepout_vol=keepout_area*1.2/1000; rf_needed_pct=a.rf_window_area_mm2/keepout_area*100
    warnings=[]
    if a.metal_percent>50: warnings.append('metal frame percentage is high and can detune antennas without breaks, windows, and isolation')
    if a.rf_friendly_percent<30: warnings.append('RF-friendly material share is low for multi-band cellular, Wi-Fi, Bluetooth, GNSS, NFC, and UWB coexistence')
    if a.rf_window_area_mm2>keepout_area*0.5: warnings.append('RF window requirement consumes a large share of the perimeter keep-out area')
    print('Antenna/RF physics model')
    print_section('inputs',[f'device_perimeter_mm: {a.device_perimeter_mm:.0f}',f'antenna_keepout_width_mm: {a.antenna_keepout_width_mm:.0f}',f'rf_window_area_mm2: {a.rf_window_area_mm2:.0f}',f'metal_percent: {a.metal_percent:.0f}',f'rf_friendly_percent: {a.rf_friendly_percent:.0f}'])
    print_section('assumptions',['antenna keep-out is approximated as perimeter length times keep-out width','keep-out volume assumes 1.2 mm local clearance depth for nearby metal, PCB, and battery effects','RF-friendly material percentage is a chassis/material allocation placeholder','coexistence is qualitative until antenna tuning and SAR simulation exist'])
    print_section('formulas',['antenna_keepout_area_mm2 = device_perimeter_mm * antenna_keepout_width_mm','rf_window_share_percent = rf_window_area_mm2 / antenna_keepout_area_mm2 * 100','antenna_keepout_volume_cm3 = antenna_keepout_area_mm2 * clearance_depth_mm / 1000','rf_friendly_material_percent = input_percent'])
    print_section('outputs',[f'rf_window_area_requirement_mm2: {a.rf_window_area_mm2:.0f}',f'antenna_keepout_area_mm2: {keepout_area:.0f}',f'rf_window_share_of_keepout_percent: {rf_needed_pct:.0f}',f'rf_friendly_material_percentage: {a.rf_friendly_percent:.0f}',f'antenna_keepout_volume_cm3_estimate: {keepout_vol:.1f}',f'wireless_coexistence_notes: cellular/Wi-Fi/Bluetooth/GNSS/NFC/UWB need separated apertures, filters, and tuning margin'])
    print_section('warnings',warnings); print('confidence: low until RF simulation, antenna vendor review, and SAR testing'); print('basis: first-pass perimeter keep-out and material compatibility screen'); print('primary blocker: achieving RF performance with high metal content and crowded perimeter keep-outs'); return 0
if __name__=='__main__': raise SystemExit(main())
