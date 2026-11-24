# 1 TB UFS candidate screen

The provisional PCB and assembly now model the published package outline for KIOXIA `THGJFRT3E88BATW`, a 1 TB UFS 4.1, 153-ball part. The [manufacturer product brief](https://apac.kioxia.com/content/dam/kioxia/shared/business/memory/mlc-nand/asset/productbrief/KIOXIA_UFS_Product_Brief.pdf) specifies 9 × 13 × 0.85 mm, VCC 2.4–2.7 V, and VCCQ 1.14–1.26 V. VCCQ2 is not required. KIOXIA says the host SoC and supply must be evaluated together. The nominal 1 TB density is not a promise of 1 TB formatted user capacity.

Run `python -m buildslate.storage_fit` to compare that source record with the board rectangle, assembly height, board boundary, adjacent planning blocks, and power tree. The current outline has 0.5 mm nominal clearance to both the component-side boundary and a memory planning site. The two supply rails are undefined. The [public hardware viewer](https://superflyad.github.io/BuildSlate/?tab=hardware) publishes the same findings.

This is a candidate screen only. The build requires a controlled supplier pin map and land pattern, confirmed host interface and boot support, selected regulators and power sequence, PCB routing and SI/PI review, procurement evidence, and measured tests on an assembled unit. No storage part is released in the BOM.
