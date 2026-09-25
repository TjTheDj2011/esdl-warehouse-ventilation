# Analytical Theory and Design Calculations

Written for the report's **design procedure** and **data analysis** sections.
The EECE 4101 syllabus requires that *"the design project must include
analytical theories and design calculations"*, and these are they.

Every threshold in the firmware is derived here rather than chosen by feel.
Where a number depends on the enclosure, the symbolic result is given first and
the arithmetic is worked for candidate tote sizes — **substitute the measured
volume once the box is built**.

**Symbols**

| Sym | Meaning | Unit |
|---|---|---|
| V̇ | volumetric airflow | m³/s |
| ṁ | mass flow of air | kg/s |
| V | chamber volume | m³ |
| ρ | air density, 1.204 at 20 °C | kg/m³ |
| c_p | specific heat of air at constant pressure, 1005 | J/(kg·K) |
| Q̇ | rate of heat removal | W |
| Q_s | internal heat source power | W |
| τ | thermal time constant | s |
| T_i, T_o | inside, outside temperature | °C |

---

## 1. Airflow and air exchange rate

Each fan is rated **20 CFM** free-air. Converting:

    V̇ = 20 CFM × 4.7195×10⁻⁴ m³/s per CFM = 9.439×10⁻³ m³/s

In cross-ventilation the two fans act in series on one flow path — intake low
on one wall, exhaust high on the opposite — so the system flow is set by the
path, not by the sum of the two ratings. Taking one fan's rating as the
system flow is the correct first approximation; adding the two would be wrong.

**Air changes per hour:**

    ACH = 3600 · V̇ / V

| Tote | V (m³) | τ = V/V̇ (s) | ACH | at 60 % derate: τ (s) | ACH |
|---|---|---|---|---|---|
| 12 gal | 0.0454 | 4.8 | 748 | 8.0 | 449 |
| 18 gal | 0.0681 | 7.2 | 499 | 12.0 | 299 |
| 27 gal | 0.1022 | 10.8 | 332 | 18.0 | 199 |
| 32 gal | 0.1211 | 12.8 | 281 | 21.4 | 168 |

Free-air ratings are measured with zero static pressure. A fan in a drilled
panel with a foam gasket works against restriction, so the **60 % derate column
is the realistic one** and the free-air column is the optimistic bound. The
measured time constant in §4 will fall between them, and reporting where it
lands is exactly the comparison the data analysis section needs.

## 2. Rate of heat removal

Sensible heat carried out by the exhaust stream:

    ṁ = ρ V̇ = 1.204 × 9.439×10⁻³ = 1.136×10⁻² kg/s

    Q̇ = ṁ c_p (T_i − T_o) = 1.136×10⁻² × 1005 × ΔT

    **Q̇ = 11.4 · ΔT   watts per kelvin of inside-to-outside difference**

So at ΔT = 5 K the system removes roughly **57 W**. This is the number that
makes the design credible: a small internal heat source is comfortably within
range, and the capacity scales linearly with the temperature difference the
controller is trying to eliminate.

It also explains the control law directly. If ΔT < 0 — outside hotter — then Q̇
is negative: running the fans *adds* heat at 11.4 W per kelvin. That is the
`SEALED` state expressed as arithmetic rather than as an argument.

## 3. Why the chamber cannot go below ambient

Energy balance on a well-mixed chamber with an internal source:

    V ρ c_p (dT_i/dt) = ṁ c_p (T_o − T_i) + Q_s

At steady state dT_i/dt = 0:

    **T_i,ss = T_o + Q_s / (ṁ c_p)**

Two consequences, both worth stating plainly in the report:

- With **Q_s = 0**, T_i,ss = T_o exactly. The floor is ambient. There is no
  refrigeration in this system and no arrangement of fans produces one.
- With a source, the chamber settles **Q_s/(ṁ c_p) above ambient** — about
  **1 K per 11.4 W** at full flow. Increasing airflow reduces the elevation but
  can never make it negative.

The defensible claim is therefore not "it cools the warehouse" but "it drives
the chamber to the lowest temperature obtainable by air exchange, and never
takes an action that raises it."

With both fans stopped (`SEALED`), ṁ → 0 and the balance degenerates to
dT_i/dt = Q_s/(V ρ c_p): the chamber heats without bound until wall conduction
balances it. This is why `SEALED` is only correct while outside is hotter, and
why it releases itself as soon as that stops being true.

## 4. Thermal time constant

From the same balance with Q_s = 0, the homogeneous solution is first order:

    T_i(t) = T_o + (T_i,0 − T_o) · e^(−t/τ)

    where  **τ = V ρ c_p / (ṁ c_p) = V / V̇**

The mass and the specific heat cancel: **the time constant is simply the
chamber volume divided by the volumetric flow rate** — one air-change time.
Values are tabulated in §1.

**Measurement procedure.** Heat the chamber, cut the source, let the controller
ventilate, and log T_i against t. Then

    ln( (T_i(t) − T_o) / (T_i,0 − T_o) ) = −t/τ

so plotting the left side against t gives a straight line of slope −1/τ. The
measured τ against the predicted V/V̇ is the central result of the data
analysis section, and the ratio between them *is* the installed flow derate —
one experiment yields both.

## 5. Hysteresis band, derived from sensor tolerance

DS18B20 accuracy is **±0.5 °C** over the range used, i.e. **±0.90 °F**.
Quantisation at 12-bit resolution is 0.0625 °C = 0.11 °F, an order of magnitude
smaller, so tolerance dominates and resolution can be ignored.

**Threshold hysteresis (single sensor).** A bare threshold re-triggers on noise,
so the band must exceed the peak-to-peak uncertainty of one sensor:

    band > 2 × 0.90 °F = 1.80 °F

Chosen: **ON at 80.0 °F, OFF at 77.0 °F → 3.00 °F**, a factor of 1.67 margin.
The measured run engaged at 80.8 °F and released at 76.9 °F, holding through
77.9 °F without chatter, confirming the band is sufficient in practice.

**Differential deadband (two sensors).** The control law compares T_i − T_o, so
both tolerances enter. Worst case they add:

    ±0.5 + ±0.5 = ±1.0 °C = **±1.80 °F**

Treating the errors as independent gives the root-sum-square figure:

    √(0.5² + 0.5²) = 0.707 °C = **±1.27 °F**

The design uses the **worst case**, not the RSS, because the two probes are the
same part from the same batch and their errors may be correlated — in which
case they do not partially cancel. Entering `CROSS_VENT` therefore requires
outside to be **2.0 °F cooler**, just above the ±1.80 °F worst-case
uncertainty, and exit is at **1.0 °F** to give differential hysteresis of its
own.

Without that deadband, two sensors reading the same air could differ by 1.8 °F
and the controller would flap between `CROSS_VENT` and `EXHAUST_ONLY` on
nothing but tolerance.

## 6. Control loop timing

| Quantity | Value | Origin |
|---|---|---|
| DS18B20 conversion, 12-bit | ≤ 750 ms | datasheet |
| Collection delay | 900 ms | conversion + 20 % margin |
| Sensor period | 2500 ms | > conversion + collection, with headroom |
| Minimum state dwell | 10 s | 4 sensor periods — a state cannot change on one reading |
| Fault streak | 3 reads ≈ 7.5 s | tolerates a single glitch, still fast enough to matter |

Both conversions are started together and collected 900 ms later, so the loop
never blocks on a sensor. At a τ of order 10 s, a 2.5 s sampling period gives
roughly four samples per time constant — comfortably faster than the thermal
dynamics it is controlling.

## 7. Power budget

| Load | Current | Rail | Power |
|---|---|---|---|
| 2 × 80 mm fan, steady | 200 mA | 5 V | 1.00 W |
| ESP32-WROOM-32, radio unused | 80 mA | 3.3 V | 0.26 W |
| 3 × SSD1306 OLED | 60 mA | 3.3 V | 0.20 W |
| 2 × DS18B20 | 3 mA | 3.3 V | 0.01 W |
| Buzzer module | 30 mA | 3.3 V | 0.10 W |
| DRV8833 quiescent | 2 mA | 5 V | 0.01 W |
| **Total steady** | | | **≈ 1.6 W** |

**The supply is sized by inrush, not by steady draw.** A brushless fan draws
roughly 3× its rated current for the first tens of milliseconds while the rotor
accelerates:

    I_peak ≈ 3 × 0.200 A = 0.6 A

Both fans start simultaneously on entry to `CROSS_VENT`, so that transient is
the worst case. The **5 V 2 A** supply gives 3.3× headroom on inrush and 10× on
steady draw. A 500 mA supply would meet the steady figure and still brown out
the moment both fans start — which is why motor power is on its own supply and
never on the 3.3 V rail or drawn through USB.

## 8. Assumptions and limitations

Stated so the analysis is not over-read:

1. **Well-mixed chamber.** T_i is treated as uniform. Real stratification is
   why the exhaust is mounted high — the measured τ absorbs the error.
2. **No wall conduction.** Heat exchange through the tote walls is neglected;
   over short runs the air exchange term dominates by orders of magnitude.
3. **Constant air properties.** ρ and c_p are taken at 20 °C. Over a 20 °F
   excursion ρ varies about 4 %, inside the fan-rating uncertainty.
4. **Free-air fan rating.** The dominant uncertainty. §4's measurement resolves
   it, and the derate is a result rather than an assumption.
5. **Dry air, sensible heat only.** Latent heat is excluded — consistent with
   the decision to discard humidity from the control law.

## 9. Measurements still needed

- [ ] **Chamber internal dimensions** → V. Everything in §1 and §4 depends on it.
- [ ] **Cooling curve**, T_i vs t after cutting the heat source → measured τ.
- [ ] **Heat source power** if it can be established → check against §3.
- [ ] **Steady-state ΔT** with the source running → compare with T_o + Q_s/(ṁc_p).
