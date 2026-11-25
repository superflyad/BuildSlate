# Compact 128 GB module inquiry

Status: **Prepared, not sent**

Target: congatec conga-HPC/mIQ-X product team

The public [conga-HPC/mIQ-X datasheet](https://www.congatec.com/fileadmin/user_upload/Documents/Datasheets/conga-HPC-mIQ-X.pdf) lists part `053100` at 95 × 70 mm with 64 GB soldered LPDDR5X and a 28–45 W TDP. The reviewed revision says the product was not yet released for mass production. This is a physical reference for the inquiry, not a Slate part selection.

Slate Pocket v1R retains a 128 GB minimum, a 180 × 95 × 9.5 mm body, and a provisional 78 × 55 mm main PCB. The cataloged module exceeds that PCB by 17 × 15 mm in its best planar orientation. A module also needs a connector, carrier, cooling, power, and all phone subsystems. The 28 W sustained compute screen is an unverified target.

Please provide a written response to these decision questions:

1. Is an orderable **128 GB** configuration of this module or a successor available? Give the exact manufacturer part number, memory placement, package and rank topology, qualification status, lifecycle, sample schedule, MOQ, and lead time. If not, state whether a custom 128 GB configuration is technically supported and what evidence and schedule would be needed.
2. Provide the controlled module drawing with maximum height, keepouts, connector geometry, mounting, heat spreader, and minimum carrier dimensions. State whether a complete module-and-carrier assembly can fit inside a 180 × 95 × 9.5 mm enclosure with battery, display, cameras, antennas, and structural clearances.
3. Provide measured sustained and transient module power, memory power, thermal limits, cooling requirements, and throttling under a defined 128 GB resident-memory and local AI workload. Distinguish processor TDP from complete module and system input power.
4. Identify supported boot firmware, Linux/Windows BSP, memory training, camera, display/touch, audio, USB, and recovery interfaces for the exact 128 GB variant. Identify supported cellular modem, SIM/eSIM, antenna, and telephony integration routes, or state that none are supported.
5. Provide the reference carrier design, pin map, signal rules, PMIC and rail sequence, manufacturing test procedure, and rights to use the material in an independently released Slate design. Identify any NDA or distribution restrictions before sending controlled files.

An answer that only raises the controller maximum, or that supplies a 64 GB module, does not satisfy the memory decision. No supplier material or test result should be entered as approved evidence until the [controlled intake workflow](../../../docs/engineering/operator_workflows.md) records its source and review.
