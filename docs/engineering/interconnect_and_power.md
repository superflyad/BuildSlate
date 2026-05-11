# Interconnect and Power Delivery Screening

BuildSlate's first-pass device models now include interconnect and power delivery constraints. These models do not describe exact PCB traces, package pin maps, motherboard fabrication rules, or real runtime performance. They are conservative screening tools that expose when an apparently plausible AI-device concept is likely to be limited by data movement, routing, current delivery, or transient power integrity before detailed CAD, SI/PI simulation, supplier datasheets, and lab validation exist.

## Data Movement Can Limit AI Devices

Local AI devices are constrained by data movement, not just compute throughput. A TOPS number can be misleading when the memory subsystem cannot feed model weights, activations, runtime buffers, and cache traffic at the rate needed by the workload. The `memory_bandwidth.py` model therefore treats memory bandwidth as a first-order feasibility gate and explicitly states that it is not a real inference-performance predictor.

Memory bandwidth often limits inference throughput because each generated token can require substantial model and cache traffic. The first-order model uses a conservative weight-streaming estimate, adds overhead for active model footprint, and flags high utilization. It does not model KV cache behavior, scheduling, NPU efficiency, memory latency, runtime software, batching, sparsity, or kernel implementation quality.

## Short Routing Paths Matter

High-bandwidth memory systems prefer short routing between the compute package and memory packages. Longer paths increase loss, skew, crosstalk exposure, via usage, length-matching difficulty, and floorplanning pressure. The `package_interconnect.py` model converts bandwidth, package count, and package spacing into a short-path pressure score so early concepts do not hide package-adjacency constraints.

Short paths are not enough by themselves. The package count also matters because each additional memory package increases escape routing, keepouts, channel matching, decoupling, and local congestion. Routing complexity can grow rapidly even when the total board area seems adequate.

## PCB Layer Count Matters

PCB area is only one part of routing feasibility. High-speed links need impedance-controlled paths, reference planes, spacing, via strategies, and length matching. A thin device with limited board area may need more layers to route memory, storage, RF, cameras, display, charging, and debug interfaces without unacceptable signal-integrity risk.

The `routing_density.py` model uses board area, SoC area, memory package count, high-speed link count, and layer count to estimate routing pressure. It is a proxy, not a board-fabrication plan. Its warnings indicate where layer-count escalation, memory package crowding, or high-speed density may become primary blockers.

## Power Delivery Is Difficult in Thin Devices

Power delivery becomes difficult in thin devices because high compute power at low voltage creates high current. Those currents must pass through batteries, PMICs, VRMs, package interconnect, board copper, connectors, and protection circuits while also fitting into limited z-height and thermal volume.

The `power_delivery.py` model estimates sustained system power, battery-side current, charging current, and combined charge/load stress. It flags battery-side current above 10 A, sustained internal dissipation above 30 W, and overlap risk when fast charging and sustained AI workloads occur at the same time.

## Transient Current Spikes Matter

Average power is not the only power-integrity problem. AI workloads can create fast load steps as compute blocks, memory interfaces, and accelerators switch state. Transient current spikes can cause voltage droop before regulators and decoupling capacitors recover.

The `power_integrity.py` model estimates peak current, transient current, and voltage droop from a simple effective PDN resistance. It flags droop above 5%, high transient multipliers, and thin-device capacitor/VRM constraint risk. Real power integrity depends on impedance across frequency, control-loop response, package parasitics, capacitor placement, and board layout.

## Coupled Thermal, Routing, and PDN Tradeoffs

Thermal, routing, and PDN design interact strongly. More copper and more layers can help power and signal integrity but may increase cost, thickness, stiffness, and local heat spreading. More memory packages can improve capacity or bandwidth but add routing congestion and power. Higher charging power improves user experience but competes with sustained AI loads for thermal and current budget.

These models intentionally remain first-order and conservative. They are intended to identify blockers early, make assumptions explicit, and guide later detailed analysis rather than claim a finished design.
