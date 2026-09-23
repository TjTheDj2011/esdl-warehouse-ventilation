# Physical Build — What To Do, What To Get

Single reference for the hardware side. Electrical pin detail lives in
`01_pinout.md`; control behaviour lives in `../docs/03_control_matrix.md`.

---

# PART A — What to buy

## Already on hand
- [x] ESP32-WROOM-32 (USB-C) — several. **Selected controller.**
- [x] ESP32-S3 N16R8 + IPEX antenna — backup board, different pinout
- [x] Breadboard, jumper wires, assorted resistors
- [x] 2x 130-size brushed DC motor — *superseded. Keep as spares.*
- [x] 1x Corsair LL120 — *not used: 12V, and only one. Keep for the PC.*
- [x] 2x breadboard, butted together so the ESP32 fits (4 rail pairs available)
- [x] **3x Elegoo SSD1306 OLED 128x64, I2C (4-pin)** — the display, on hand
- [x] **2x DS18B20** 1-wire temperature sensors (from the professor) — better than
      the DHT22 they replace: same ±0.5 °C, 12-bit resolution, CRC-checked,
      and no 2-second minimum between reads
- [x] **Active buzzer** (from the professor) — active is what the firmware expects

## In the cart, not yet ordered
- [ ] 2x 80 mm 5 V brushless fan, dual ball bearing (8010 2-pack)
- [ ] 5 V 2 A wall adapter — ships with a screw-terminal adapter, so nothing extra needed

## Must order — electronics

| # | Part | Qty | ~$ | Why this one |
|---|---|---|---|---|
| 1 | **DRV8833 dual motor driver** | 1 | 5–9 | Switches both fans. 3.3 V native logic. Tops out at 10.8 V, so pair it with **5 V fans**; use a TB6612FNG instead if you end up with 12 V fans. |
| ~~6~~ | ~~2x 80 mm brushless PC fan, 5 V~~ | | | **In cart.** 8010 dual ball bearing 2-pack, 20 CFM, 22 dBA, 0.1 A each. |
| ~~7~~ | ~~5 V 2 A supply for the fans~~ | | | **In cart.** Sizing justified by fan inrush, not steady draw — see the power budget in B7. |

## Must source — mechanical

| # | Item | ~$ | Notes |
|---|---|---|---|
| 9 | Clear plastic box | 8–15 | **Polypropylene storage tub beats acrylic** — acrylic cracks when drilled. Big enough that the diagonal is a real distance; roughly shoebox or larger. |
| 10 | M4 screws, nuts, washers (x8) + foam weatherstrip | 5 | Fan mounting. Four screws per fan, foam as a gasket. |
| 11 | Soldering iron + solder | on hand? | Only needed to tin the fan leads after cutting their connectors. Much less critical now that brushed motors are out. |
| 12 | **76 mm hole saw or step bit** | 8–15 | For the fan openings. Plus a 4.5 mm bit for the screw holes. |
| 13 | Heat source — hair dryer | on hand? | Demo stimulus. A heat gun will melt a polypropylene tote. |
| 14 | Masking tape | ~0 | Labelling the four power rails, and for the blocked-intake control experiment |

## Deliberately not buying
L298N (see item 2) · discrete H-bridge parts · anything for WiFi, Bluetooth or SD
logging. The design is a self-contained local controller; the LCD is the
visualisation. Scope stays closed.

---

# PART B — What to build

## B1. Fan ports

Two ports on the **diagonal** - this geometry is core objective #4, not decoration:

- **Intake - LOW on one wall**
- **Exhaust - HIGH on the opposite wall**

Low-in / high-out works with buoyancy instead of against it: cool air enters at
the floor, the exhaust removes the hottest stratified layer off the ceiling.

For a standard **80 mm** computer fan:

| Feature | Size |
|---|---|
| Airflow hole | **76 mm** diameter |
| Screw holes | **71.5 mm** square spacing, 4 x 4.5 mm |

Mark the screw holes from the fan itself rather than measuring - lay it on the
wall and pencil through the corners.

## B2. Makeup air - nothing to drill

Earlier revisions of this design drilled a pattern of makeup holes. **They are no
longer needed.** The idle intake fan is the makeup-air path: in `EXHAUST_ONLY` the
exhaust runs while the intake sits still, and air is drawn in through the stopped
intake fan exactly where we want it, low and on the far wall.

That is safe by construction - see docs/03_control_matrix.md. If outside were
meaningfully hotter, `SEALED` stops both fans rather than letting the exhaust pull
hot air in.

Optional, not required:

- A **one-way flapper** over the intake reduces slow passive exchange during
  `SEALED`. Worth adding only if bench measurements show `SEALED` drifting.
- If the exhaust sounds strained or moves little air, the intake fan may be too
  restrictive as a passive vent. A few extra 20 mm holes low on the intake wall
  would fix it. Measure before drilling.

## B3. Which fans

**2x 80 mm brushless computer fan, 5 V.** Not brushed motors, and this is a
deliberate reversal of the earlier plan:

| | Brushless PC fan | 130 motor + propeller |
|---|---|---|
| Airflow | ~20-25 CFM | roughly 3-5 CFM |
| Noise / vibration | quiet, balanced | buzzes the whole tote |
| Mounting | 4 screws, standard holes | fabricate a sub-plate |
| Brush noise on I2C | **none** | the #1 failure risk in this build |
| Can reverse | no | yes |

Losing reversal costs nothing now that `SEALED` exists, and removing brushes
eliminates the single most likely cause of a mid-demo failure.

**Voltage:** buy **5 V** fans so the existing DRV8833 can drive them - it tops out
at 10.8 V. If you find only 12 V fans, either run them at 5-6 V (slower but still
far better than a toy propeller) or switch the driver to a TB6612FNG, which
handles 13.5 V.

**Wiring is unchanged.** Each fan goes to one DRV8833 channel exactly where the
motor would have. The firmware only ever commands those channels forward, so it
never asks a fan to do something it cannot.

A 2-wire fan has no tachometer - that is fine, nothing in the design reads one.
If yours has a third wire, leave it unconnected.

## B3b. Mounting the fans

This is now a four-screw job per fan, which is most of why the change was worth
making.

1. **Mark from the fan.** Hold it on the wall in position, pencil through the four
   corner holes, and mark the airflow circle.
2. **Cut the airflow hole** (76 mm for an 80 mm fan). A hole saw or step bit in a
   polypropylene tote cuts cleanly; go slowly and back the panel with scrap.
3. **Drill the four corner holes** at 4.5 mm.
4. **Sandwich a foam gasket** between fan and wall - weatherstrip tape works. It
   seals the gap and stops vibration transmitting into the tote.
5. **Bolt through** with M4 screws, washers and nuts. Do not overtighten; the tote
   wall will dish.

**Check airflow direction before final assembly.** Every PC fan has a moulded
arrow on the frame showing flow direction. Confirm it with power anyway - the
intake must blow **in**, the exhaust must blow **out**. Mark each one with a
marker. A fan mounted backwards quietly ruins the cross-ventilation demo and is
easy to miss.

**Strain-relieve the leads** to the plate so the connector is not carrying load.

## B4. Sensor placement

This is where the design is most easily sabotaged.

- **Inside sensor** — mid-chamber, in the airflow path, **shielded from direct
  heat-gun infrared**. A small piece of card or foil between the gun and the
  sensor is enough. Unshielded it reads radiant heat, not air temperature, and
  every number you record is wrong.
- **Outside sensor** — well clear of the **top-right exhaust plume**. If it reads
  our own hot exhaust, the controller sees outside as hotter than inside and
  latches `SEALED` or `EXHAUST_ONLY` forever. That is a positive feedback loop
  that looks exactly like a firmware bug. Mount it on the intake side, or on a
  short standoff away from the box entirely.

## B5. Keep the electronics out of the heat

Breadboard, ESP32, driver and battery pack all live **outside** the box. Only the
inside DHT22 goes in. Run its three wires through a small pass-through hole and
seal around them loosely with tape. Heating your own microcontroller to 100 F+ is
an unforced error.

## B6. LCD mounting

Outside, facing the audience, on top of the box or on a small stand. It exists to
prove state changes live during the presentation, so it has to be readable from
where the class will be standing.

---

# PART C — Assembly order

Do these in order. Each step is verifiable before the next, so a fault has one
suspect instead of five. Console commands and expected output are in
`../docs/02_bringup_guide.md`.

1. **Solder motor leads**, then solder a **0.1 uF ceramic across each motor's
   terminals**, right at the motor case. Do this before mounting — it is awkward
   afterwards. Brush noise corrupting the I2C bus is the most common failure in
   this exact build, and it presents as an *LCD* problem, which sends people
   debugging entirely the wrong subsystem.
2. **Cut ports, drill makeup holes, mount fans.** Confirm airflow direction.
3. **Flash the bare board** with nothing attached. Self test should report 0 I2C
   devices and no sensor readings, then drop to FAULT. That is a pass.
4. **Add the LCD** through the level shifter. Self test should find it at 0x27 or
   0x3F automatically.
5. **Add the inside DHT22**, then the outside one. Watch the `fail` counter in
   `status` for a minute — it should stay at or near zero.
6. **Add the motor driver on its own supply**, common ground. Test each channel
   with `intake on` / `intake rev` / `exhaust on`.
7. **Add the buzzer.** `buzz on`, `buzz pat`.
8. **Prove all five states with `sim`**, no heat needed.
9. **Real heat.** Capture the serial trace — those transitions are the
   measurements the report is built on.

---

# PART D — Before first power-on

Four things that damage parts. Check all four every time you rewire.

1. **DRV8833 orientation.** Reversed VM and GND kills it instantly.
2. **Level shifter present on SDA/SCL**, low side 3.3 V, high side 5 V. The
   ESP32 is not 5 V tolerant — 3.6 V absolute maximum.
3. **Motor power is separate.** Never the 3.3 V rail, never USB through the
   board.
4. **Common ground.** Battery negative to ESP32 GND. Without it the driver has no
   reference and the usual symptom is motors that do nothing or twitch randomly.

---

# PART E — Measurements to capture

The report needs numbers we actually took, not design intent.

- [ ] Serial trace of every state transition under real heat, with timestamps
- [ ] **Seal threshold.** The 3.0 F figure is reasoned, not measured. Hold the
      chamber steady, sweep outside temperature, find where forced exchange stops
      helping.
- [ ] **Intake reversed vs braked** in `EXHAUST_ONLY` — cool-down curves under
      identical heat input, to show the reversal actually increases flush rate
- [ ] **Makeup holes open vs taped over** — same comparison. This is the
      controlled experiment the fixed holes buy you, and it runs between takes
      rather than during the demo.
- [ ] DHT22 read reliability: `ok` / `fail` counts over a long run
- [ ] Confirmation the ambient sensor never reads the exhaust plume
