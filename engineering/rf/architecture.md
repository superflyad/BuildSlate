# Slate Pocket v1R RF and Wireless Architecture

Status: provisional pre-module architecture; no antenna, radio, or wireless-power component is selected.

## Architecture decision

EVT0 uses a modular Wi-Fi/Bluetooth development radio with cabled or supplier reference antennas where practical. It reserves four perimeter antenna zones in the intended enclosure but does not claim integrated-antenna performance. UWB remains a reserved option. Optional 5G cellular is deferred until target countries, operators, bands, antenna count, module strategy, and certification budget are approved.

Wireless charging is removed from EVT0. The current 58 x 58 x 0.8 mm planning stack drives the battery zone to 9.84 mm, 0.34 mm over the 9.5 mm device envelope. The Wireless Power Consortium publicly identifies Qi2 25W, while the Slate target is 50 W; this package has no primary evidence for a standards-based 50 W receiver or certification route. The rear coil zone remains reserved for future study, but it cannot consume EVT0 z-height or be presented as supported.

## Target radio inventory

| Function | Product intent | EVT0 posture | Missing release evidence |
| --- | --- | --- | --- |
| Wi-Fi | Wi-Fi 7 target | Modular development radio | Module, bands/channels by market, antennas, coexistence, power, drivers, certification reuse |
| Bluetooth | Bluetooth 6 target | Shared development module where supported | Qualified feature set, profiles, antenna path, interoperability, listing |
| UWB | UWB 2.0 intent | Reserved, disabled unless a qualified module is selected | Use cases, channels by market, antenna, ranging accuracy, coexistence, certification |
| Cellular | Optional 5G | Deferred from EVT0 | Markets, operators, bands, modem/module, SIM/eSIM, antennas, SAR, PTCRB/carrier scope |
| Wireless power | 50 W target | Removed from EVT0 | Selected standard/profile, receiver, coil/ferrite/shield, FOD, thermal map, certification |

Exact bands are intentionally unset. They must follow selected modules, target markets, and current regulatory/lab review; a generic global band list would create false antenna and certification assumptions.

## Antenna and chassis topology

The keepout map reserves four edge zones to prevent the aluminum heat frame, battery, board copper, shields, graphite/copper spreaders, cameras, speakers, and user grip from consuming all antenna volume. The zones are planning reservations, not tuned antenna volumes. Nonmetal windows are required at the selected antenna sites, with continuity breaks and grounding controlled by the antenna/chassis design rather than added late.

The provisional priorities are:

1. Preserve two spatially separated Wi-Fi/Bluetooth antenna opportunities.
2. Preserve an independent UWB opportunity if the use case survives requirements review.
3. Do not reserve cellular antenna count or volume until the market/band matrix exists.
4. Route thermal spreaders around released RF keepouts; do not bridge them with conductive graphite, copper, coatings, fasteners, or gaskets without simulation and test.
5. Treat hand/grip, display, USB cable, charger, and mechanical configuration as antenna boundary conditions.

## Grounding and isolation intent

- Establish one reviewed chassis/PCB RF grounding strategy with controlled return paths and designated bonding points.
- Keep switch-mode power, charger, high-speed clocks, display links, memory, and storage noise away from feeds and matching networks.
- Reserve accessible matching, tuning, conducted-test, and debug points without making them production leakage paths.
- Validate radio-kill behavior at hardware, firmware, user-indicator, suspend/resume, fault, and update boundaries.
- No final antenna matching, ground clearance, feed impedance, or isolation number is claimed before the selected module and antenna design exist.

## Wireless-power coexistence

If wireless charging returns after EVT0, it must independently close:

- the 0.34 mm nominal z-height deficit plus tolerances, swelling, adhesives, and rear-cover variation;
- coil/ferrite/shield geometry, alignment system, foreign-object detection, authentication, and receiver losses;
- desense and emissions interactions with Wi-Fi, Bluetooth, UWB, optional cellular, NFC if added, cameras, storage, and sensor buses;
- rear-skin, battery, and charger temperatures across misalignment and object cases;
- applicable Wireless Power Consortium certification and all separate product-safety/regulatory obligations.

## Current compliance anchors

- United States: FCC equipment authorization and RF-exposure evaluation for the final portable-device configuration; modular approval does not eliminate final-configuration responsibilities. See [FCC equipment authorization/RF exposure order](https://docs.fcc.gov/public/attachments/FCC-19-126A1_Rcd.pdf).
- European Union: Radio Equipment Directive 2014/53/EU, with the applicable harmonized standards and cybersecurity/common-charger obligations determined by the compliance owner at project time. See [EUR-Lex Directive 2014/53/EU](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32014L0053).
- Cellular, if retained: PTCRB plus any operator-specific testing identified for target markets. See [PTCRB certification process](https://www.ptcrb.com/get-certified/).
- Wireless power, if retained: current WPC specification, authorized-lab compliance/interoperability testing, registration, and logo rules. WPC publicly lists Qi2 25W and requires certification for logo use. See [WPC Qi overview](https://www.wirelesspowerconsortium.com/standards/qi-wireless-charging/) and [WPC certification](https://www.wirelesspowerconsortium.com/knowledge-base/testing-and-certification/).

Exact standard editions, limits, test reductions, and market filings must be confirmed with accredited labs and regulatory counsel after the SKU/market matrix is frozen.

This architecture does not prove RF performance, coexistence, SAR/RF-exposure compliance, EMC compliance, wireless-power safety, certification, or production readiness.
