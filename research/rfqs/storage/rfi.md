# Embedded Storage RFI

Status: **Prepared, not sent**  
Targets: **Samsung Semiconductor, KIOXIA, Micron**

## Purpose

Establish a supplyable 1 TB embedded-storage package and a supported architecture for the locked 2 TB fallback. The 4 TB target remains aspirational until a supplier-backed path exists.

## Architecture context

- Preferred product unit: 1 TB UFS 5.0/4.1 or equivalent embedded package.
- Locked fallback product capacity: 2 TB.
- Alternatives: multiple supported UFS devices, UFS plus compact NVMe, or compact NVMe when host support and integration evidence exist.
- Public candidate references: Samsung 1 TB UFS 5.0/4.1, KIOXIA 1 TB UFS 4.1, Micron 1 TB 2230 NVMe.

## Required engineering data

- Orderable part, capacity/user capacity, package outline/tolerances, ball map or connector, mass, and keepouts.
- Interface/version, lanes, host requirements, boot support, firmware/update model, security, encryption, and health telemetry.
- Sequential/random read/write performance with queue depth, data pattern, temperature, and sustained-duration conditions.
- Active, idle, sleep, startup, and worst-case power/current; rail requirements and transients.
- Thermal limits, throttling curves, junction/case measurement guidance, endurance, retention, and workload assumptions.
- Multi-device host support and reference architecture for reaching 2 TB; identify boot, RAID/aggregation, software, routing, and power implications.
- Qualification, sample/production status, lifecycle, PCN/EOL policy, MOQ, lead time, pricing basis, and geographic restrictions.

## Decision thresholds

- Marketing throughput without power, temperature, duration, and throttling conditions is insufficient.
- A 2 TB proposal must state the supported host topology; multiplying package capacity is not proof.
- A 4 TB proposal must be orderable or clearly labeled roadmap-only.
- UFS and NVMe proposals must include the extra controller, connector, board-area, and thermal consequences where applicable.

This request is exploratory and does not constitute a purchase commitment or component selection.
