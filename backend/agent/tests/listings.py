"""Text versions of all nine fixtures, plus fixtures 10 to 20 from real screenshots.

Written as a pasted listing would read. No seller, store or brand names.
Fixtures 3, 4 and 5 are about what is printed on the product, so their text versions
include a line giving the print on the cells, as a person pasting the listing might
type it. The image path is still how the demo catches fixture 3. Fixtures 10 to 20 follow
the same convention; their screenshots are in fixtures/ (see fixtures/README.md).
"""

LISTING_TEXT: dict[int, str] = {
    1: """\
18650 Rechargeable Battery 12000mAh 3.7V Li-ion High Capacity Flat Top Cell, 4 Pack

- 12000mAh capacity per cell for flashlights and headlamps
- 3.7V lithium-ion, rechargeable

Technical details
Battery cell composition: Lithium Ion
Item package weight: 0.600 Kilograms (600 g)
Package dimensions: 150 x 150 x 150 mm
""",
    2: """\
AA Rechargeable Batteries Ni-MH 700mAh 1.2V, 8 Count

- Ni-MH AA cells, 700mAh each, 1.2V
- For solar garden lights and remote controls
""",
    6: """\
2S LiPo Battery 7.4V 6200mAh Hard Case Pack for 1/10 RC Car

Label on pack: 7.4V 6200mAh 45.88Wh 2S

Specifications
Cells: 2S (2 cells in series)
Dimensions: 139.5 x 47.5 x 26 mm
Weight: 315 g
""",
    7: """\
3S LiPo Battery 11.1V 2200mAh Soft Pack for RC Airplane and Quadcopter

Label on pack: 11.1V 2200mAh 24.42Wh 3S

Specifications
Cells: 3S
Dimensions: 106 x 33 x 23 mm
Weight: 179 g
""",
    8: """\
2S LiPo Battery 7.4V 5200mAh Hard Case for RC Truck and Buggy

Label on pack: 7.4V 5200mAh 38.48Wh 2S

Specifications
Cells: 2S
Dimensions: 25 x 47 x 139 mm
Weight: 307 g
""",
    9: """\
2S LiPo Battery 7.4V 5200mAh Hard Case for RC Car

Label on pack: 7.4V 5200mAh 38.48Wh 2S
""",
    3: """Alkaline Batteries Combo Pack, AA and AAA, 24 Count

- Alkaline AA and AAA batteries for everyday devices

Printed on the cells in the product photo: R6 Heavy Duty (AA cells), R03 Heavy Duty (AAA cells)
""",
    4: """Carbon Zinc Batteries AA and AAA Value Pack

- Carbon zinc AA and AAA cells for clocks and remote controls
- 10-year shelf life
""",
    5: """Heavy Duty Batteries AA and AAA Multipack, Carbon Zinc

- Carbon zinc AA and AAA cells for low-drain devices

Printed on the cells in the product photo: R6 Heavy Duty (AA cells), R03 Heavy Duty (AAA cells)
""",
    # ---- added 2026-11-14 from the screenshots in fixtures/ (see fixtures/README.md)
    10: """\
4 Pack LR03 / AM-4 AAA 1.5V Super Alkaline Batteries - 140 Minutes

About this item
- Battery Type: Super Alkaline; Cadmium 0% ; Mercury 0%
- Ultra High Capacity: Perfect for electronics that drains batteries fast
- 100% Compatible with original manufacturer equipments.
- Capacity: 1.5v (Will NOT affect battery compatibility)
- Discharge time: 140 Minutes

Printed on each cell: 0% MERCURY 0% CADMIUM SUPER ALKALINE AAA LR03/AM-4 1.5V
""",
    11: """\
9V Batteries 4 Pack, 9 Volt Alkaline Battery for Smoke Alarms
6LR61 Square Battery for Guitar Pedals, Audio & Handheld Meters; Leakproof 7-Year Shelf Life, Mercury-Free

About this item
- LONG LASTING POWER - High-performance 9V alkaline batteries designed for reliable, consistent energy in household electronics.
- ADVANCED LEAKPROOF DESIGN - Double-layer internal structure housed within a stainless steel cover.
- VERSATILE COMPATIBILITY - The ideal 9v battery for smoke detector replacement, fire alarms, carbon monoxide detectors, and professional audio gear.
- 7 YEARS SHELF LIFE - Our 9 volt battery 4 pack maintains full power for up to 7 years in storage.

Printed on the retail card: 9V 6LR61 9 VOLTS; ALKALINE BATTERIES; 7 YEAR SHELF LIFE; MERCURY AND CADMIUM FREE; 4 PACK
""",
    12: """\
AAA Batteries (4 Pack), Triple A Alkaline Batteries

About this item
- 4 pack of AAA Alkaline Batteries, Triple A Batteries
- Up to 50% longer lasting in medical devices
- Long lasting batteries for your AAA devices, like toys, games and remotes
- Designed to protect your devices against damaging leaks for up to two years after fully used
- These AAA batteries hold power for up to 12 years in storage

Printed on the retail card: AAA4; 12 YEAR SHELF LIFE; UP TO 50% LONGER LASTING; ALKALINE BATTERIES
""",
    13: """\
AAA Long-Lasting Alkaline Batteries, 8 Count, 1.5 Volt, 10-Year Shelf Life, Leak-Proof

About this item
- IN THE BOX: 8-pack of 1.5 volt AAA alkaline batteries for reliable performance across a wide range of devices
- DEVICE COMPATIBLE: Ideal for game controllers, toys, flashlights, digital cameras, clocks, and more
- DESIGNED TO LAST: 10-year leak-free shelf life; store for emergencies or use right away
- SINGLE USE: These batteries are NOT rechargeable
- Packaging may vary.

Printed on each cell: AAA LR03 AM4 1.5V
""",
    14: """\
Super Heavy Duty 1209 6 Volt Spring Lantern Battery

About this item
- Super Heavy Duty 6V Spring Lantern Battery is perfect for your everyday home and safety devices
- Ideal for use with lanterns, smoke alarms, flashlights and other low drain devices
- Dependable and long-lasting power
- Zero added mercury and cadmium
- Quality seal for trusted power

Printed on the battery: 6V SIZE / FORMAT; SUPER HEAVY DUTY; No. 1209
""",
    15: """\
Super Heavy Duty AAA Battery, 4 Count

Features & Specs
Voltage: 1.5 volts
Reusability: Single Use
Amperage: 1.5 A
Compatible Phone Models: digital camera

Printed on the retail card: AAA4; SUPER HEAVY DUTY; CARBON ZINC BATTERIES / PILES ZINC-CHARBON
""",
    16: """\
3.7V Rechargeable 2000mAh Lipo Battery 1S PH 2.0 Plug 1Pack
1S 1C 3.7V Lithium Polymer Batteries 2000mAh Integrated Protection Circuit for Arduino ESP32 Development Board

About this item
- Battery Specifications: Dimensions: 34*10*50mm/ 1.34*0.39*1.97inch; Battery Weight(Single): 35g; Capacity: 2000mAh; Plug: PH2.0; Discharge Rate: 1C.
- Excellent Performance: A-grade lithium cobalt oxide battery system, featuring higher energy and higher density.
- Safe and reliable to use: Each lipo battery comes equipped with a built-in protection board that prevents overcharging, over-discharging, overcurrent, overheating, and short circuits.
- Application scenarios: suitable for battery replacement of 3.7V electronic products. (NOTE!!! The maximum operating current of this battery is only about 1.5A.)

Printed on the pack: 2000 mAh; 3.7V 7.4Wh
""",
    17: """\
3S 11.1V 1300mAh 45C LiPo Battery Pack with XT60 Plug for FPV racing quads

About this item
- 11.1V 1300mAh Lipo battery Specification: Battery Voltage: 11.1V; Configuration: 3S1P; Capacity: 1300mAh; Discharge: 45C; Plug: XT60 Plug.
- Dimensions: 1300mAh 3S Lipo battery dimensions is: 72*36*23mm/2.83*1.42*0.91inch; Approx Weight: 119g/4.2oz.
- High Performance: 3S 1300mAh Lipo battery with 45C discharge rate offers high power and very long time for your RC Model.

Printed on the pack: 1300 mAh; 45C; 3CELLS; 11.1V; 14.4Wh
""",
    18: """\
3.7V Lipo Battery 3000mAh Rechargeable Lithium Polymer Batteries Pack with Wire JST1.25mm Connector Integrated Protection Circuit for Arduino ESP32 Development Board

About this item
- Battery Specifications: Dimensions: 36*10*65mm/ 1.42*0.39*2.56inch; Battery Weight(Single): 49g; Capacity: 3000mAh; Plug: JST1.25; Discharge Rate: 1C.
- Reliable Performance: Our 3.7 volt rechargeable lithium polymer battery provides reliable performance with long life. Each lipo battery comes equipped with a built-in protection board.
- Storage & Usage: When storing lithium polymer batteries for a long time, please keep the battery in a state of 40%-60%.

Printed on the pack: LP103665; 3000mAh; 3.7V; 11.1Wh; Rechargeable Lipo Battery
""",
    19: """\
4PCS 3.7V Lipo Battery 1000mAh Rechargeable Lithium Polymer Batteries Pack with JST1.25mm Connector Integrated Protection Circuit for Arduino ESP32 Development Board

About this item
- Battery Specifications: Dimensions: 30*8*42mm/ 1.18*0.31*1.65inch; Battery Weight(Single): 18g; Capacity: 1000mAh; Plug: JST1.25; Discharge Rate: 1C.
- Reliable Performance: Our 3.7 volt rechargeable lithium polymer battery provides reliable performance with long life.
- Application: perfect for ESP32 projects or a small Internet of Things (IoT) project.

Printed on each pack: LP803040; 1000mAh; 3.7V; 3.7Wh; Rechargeable Lipo Battery
""",
    20: """\
3.7V Lipo Battery 1100mAh 603449 Rechargeable JST 2.0mm, 1-Pack

About this item
- Basic Info: Voltage: 3.7V; Typical capacity: 1100mAh, Min capacity: 1000mAh; Weight: approximate 22g; Size: 34.5 x 51 x 6.3mm (WxLxH). Connector: pin spacing 2mm, plug width 5.8mm.
- Confirm 4 Factors Before Purchase: 1. Battery size; 2. Connector model; 3. Connector size; 4. Polarity.
- Reliable Performance: Leak-proof, cost-effective, 800+ cycles. Protection: overcharge, over-discharge, overcurrent, short circuit.
- Certifications: UL 1642 listed and UL 62133-2 (IEC 62133-2) certified. UN38.3 compliant for safe transport.

Printed on the pack: Rechargeable Li-ion Polymer Battery; LP603449; 3.7V 1100mAh 4.1Wh; (1ICP7/35/50)
""",
}
