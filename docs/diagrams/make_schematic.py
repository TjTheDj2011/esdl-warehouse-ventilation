#!/usr/bin/env python3
"""ESDL Project 1 - circuit schematic (2 sheets).

Hand-laid-out with orthogonal routing and net labels, schematic convention.
Regenerate:  python3 docs/diagrams/make_schematic.py
Output:      docs/05_schematic.pdf
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
from matplotlib.backends.backend_pdf import PdfPages

WIRE = "#12121a"
BLK = "#12121a"
FILL = "#fdfdfd"
NETC = "#8b1a1a"
PWRC = "#1d6b1d"
LW = 1.35
STUB = 7.0
REV, DATE = "A", "2026-09-16"


def page(w=230, h=122):
    fig, ax = plt.subplots(figsize=(16.5, 9.2))
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    ax.set_aspect("equal")
    return fig, ax


def wire(ax, pts, color=WIRE, lw=LW):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ax.plot(xs, ys, color=color, lw=lw, solid_capstyle="round", zorder=2)


def junction(ax, x, y):
    ax.add_patch(Circle((x, y), 1.0, fc=WIRE, ec="none", zorder=4))


def ic(ax, x0, y0, x1, y1, ref, name, left=(), right=(), fs=8.4):
    """left/right: sequence of (pin_name, y). Returns dict name -> stub endpoint."""
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=FILL, ec=BLK,
                           lw=1.7, zorder=3))
    ax.text((x0 + x1) / 2, (y0 + y1) / 2 + 3.0, ref, ha="center", va="center",
            fontsize=9.5, fontweight="bold", zorder=5)
    ax.text((x0 + x1) / 2, (y0 + y1) / 2 - 2.4, name, ha="center", va="center",
            fontsize=8.6, zorder=5, linespacing=1.5)
    ends = {}
    for pn, y in left:
        wire(ax, [(x0 - STUB, y), (x0, y)])
        ax.text(x0 + 2.0, y, pn, ha="left", va="center", fontsize=fs, zorder=5)
        ends[pn] = (x0 - STUB, y)
    for pn, y in right:
        wire(ax, [(x1, y), (x1 + STUB, y)])
        ax.text(x1 - 2.0, y, pn, ha="right", va="center", fontsize=fs, zorder=5)
        ends[pn] = (x1 + STUB, y)
    return ends


def gnd(ax, x, y, down=5.0):
    wire(ax, [(x, y), (x, y - down)])
    yy = y - down
    for i, half in enumerate((4.2, 2.6, 1.2)):
        ax.plot([x - half, x + half], [yy - i * 1.5, yy - i * 1.5],
                color=WIRE, lw=1.5, zorder=3)


def vdd(ax, x, y, label, up=5.0):
    wire(ax, [(x, y), (x, y + up)])
    ax.plot([x - 4.2, x + 4.2], [y + up, y + up], color=PWRC, lw=1.9, zorder=3)
    ax.text(x, y + up + 2.6, label, ha="center", va="bottom", fontsize=8.2,
            color=PWRC, fontweight="bold", zorder=5)


def pwr_tag(ax, x, y, label, direction="left"):
    """Compact power flag - no vertical clearance needed, unlike a Vdd bar."""
    d = -1 if direction == "left" else 1
    tri = [(x, y), (x + d * 4.5, y + 2.6), (x + d * 4.5, y - 2.6)]
    ax.add_patch(Polygon(tri, fc="#e8f5e8", ec=PWRC, lw=1.3, zorder=4))
    ax.text(x + d * 6.0, y, label, ha="right" if d < 0 else "left",
            va="center", fontsize=7.9, color=PWRC, fontweight="bold", zorder=5)


def net(ax, x, y, text, to_right=True, w=40):
    """Off-sheet net label (flag shape)."""
    tip = 4.0
    if to_right:
        pts = [(x, y), (x + w - tip, y), (x + w, y + 3.4), (x + w - tip, y + 6.8),
               (x, y + 6.8)]
        tx = x + 3.0
        ha = "left"
    else:
        pts = [(x + w, y), (x + tip, y), (x, y + 3.4), (x + tip, y + 6.8),
               (x + w, y + 6.8)]
        tx = x + w - 3.0
        ha = "right"
    ax.add_patch(Polygon([(px, py - 3.4) for px, py in pts], fc="#fdf2f2",
                         ec=NETC, lw=1.3, zorder=3))
    ax.text(tx, y, text, ha=ha, va="center", fontsize=8.2, color=NETC,
            fontweight="bold", zorder=5)


def motor(ax, cx, cy, r, ref, name):
    ax.add_patch(Circle((cx, cy), r, fc=FILL, ec=BLK, lw=1.7, zorder=3))
    ax.text(cx, cy, "M", ha="center", va="center", fontsize=13,
            fontweight="bold", zorder=5)
    ax.text(cx + r + 4.5, cy, f"{ref}\n{name}", ha="left", va="center",
            fontsize=8.3, zorder=5, linespacing=1.5)


def cap_v(ax, x, ytop, ybot, ref, val):
    """Vertical capacitor spanning two horizontal wires at ytop and ybot."""
    mid = (ytop + ybot) / 2
    wire(ax, [(x, ytop), (x, mid + 1.5)])
    wire(ax, [(x, ybot), (x, mid - 1.5)])
    ax.plot([x - 4.2, x + 4.2], [mid + 1.5, mid + 1.5], color=WIRE, lw=1.9, zorder=3)
    ax.plot([x - 4.2, x + 4.2], [mid - 1.5, mid - 1.5], color=WIRE, lw=1.9, zorder=3)
    ax.text(x + 6.0, mid, f"{ref}\n{val}", ha="left", va="center", fontsize=8.0,
            zorder=5, linespacing=1.5)
    junction(ax, x, ytop)
    junction(ax, x, ybot)


def battery(ax, x, ytop, ybot, ref, name):
    mid = (ytop + ybot) / 2
    wire(ax, [(x, ytop), (x, mid + 3.0)])
    wire(ax, [(x, ybot), (x, mid - 3.0)])
    for i, (dy, half) in enumerate(((3.0, 5.0), (1.2, 2.4), (-1.2, 5.0), (-3.0, 2.4))):
        ax.plot([x - half, x + half], [mid + dy, mid + dy], color=WIRE,
                lw=1.9, zorder=3)
    ax.text(x - 7.5, mid, f"{ref}\n{name}", ha="right", va="center", fontsize=8.3,
            zorder=5, linespacing=1.5)


def title_block(ax, w, sheet, total, subtitle):
    bw, bh = 86, 24
    x0, y0 = w - bw - 2, 2
    ax.add_patch(Rectangle((x0, y0), bw, bh, fc="white", ec=BLK, lw=1.6, zorder=6))
    ax.plot([x0, x0 + bw], [y0 + bh - 9, y0 + bh - 9], color=BLK, lw=1.2, zorder=7)
    ax.plot([x0, x0 + bw], [y0 + 8, y0 + 8], color=BLK, lw=1.2, zorder=7)
    ax.plot([x0 + 40, x0 + 40], [y0, y0 + 8], color=BLK, lw=1.2, zorder=7)
    ax.plot([x0 + 62, x0 + 62], [y0, y0 + 8], color=BLK, lw=1.2, zorder=7)
    ax.text(x0 + bw / 2, y0 + bh - 4.5, "ESDL PROJECT 1 - WAREHOUSE VENTILATION",
            ha="center", va="center", fontsize=8.6, fontweight="bold", zorder=7)
    ax.text(x0 + bw / 2, y0 + 12.5, subtitle, ha="center", va="center",
            fontsize=8.2, zorder=7)
    ax.text(x0 + 2, y0 + 4, "TJ / Tabitha", ha="left", va="center", fontsize=7.6, zorder=7)
    ax.text(x0 + 42, y0 + 4, DATE, ha="left", va="center", fontsize=7.6, zorder=7)
    ax.text(x0 + 64, y0 + 4, f"REV {REV}   SH {sheet}/{total}", ha="left",
            va="center", fontsize=7.6, zorder=7)


# ------------------------------------------------------------------ sheet 1
def sheet1(pdf):
    W, H = 242, 132
    fig, ax = page(W, H)
    ax.text(4, H - 3, "SHEET 1 - CONTROLLER, SENSORS, DISPLAY", fontsize=12,
            fontweight="bold", va="top")

    esp = ic(ax, 78, 30, 118, 120, "U1", "ESP32-WROOM-32\n3.3 V logic",
             left=[("3V3", 114), ("5V", 107), ("GND", 100),
                   ("GPIO4", 86), ("GPIO16", 79)],
             right=[("GPIO21", 114), ("GPIO22", 107), ("GPIO23", 93),
                    ("GPIO25", 62), ("GPIO26", 56), ("GPIO27", 50),
                    ("GPIO14", 44), ("GPIO13", 38)])

    pwr_tag(ax, esp["3V3"][0], 114, "+3.3 V")
    pwr_tag(ax, esp["5V"][0], 107, "+5 V")
    gnd(ax, esp["GND"][0], 100, down=4.0)

    d1 = ic(ax, 12, 74, 50, 98, "U2", "DHT22 #1\nCHAMBER",
            left=[("VCC", 92), ("GND", 80)], right=[("DATA", 86)])
    d2 = ic(ax, 12, 38, 50, 62, "U3", "DHT22 #2\nAMBIENT",
            left=[("VCC", 56), ("GND", 44)], right=[("DATA", 50)])
    for dd in (d1, d2):
        pwr_tag(ax, dd["VCC"][0], dd["VCC"][1], "+3.3 V")
        gnd(ax, dd["GND"][0], dd["GND"][1], down=4.0)
    wire(ax, [d1["DATA"], esp["GPIO4"]])
    wire(ax, [d2["DATA"], (64, 50), (64, 79), esp["GPIO16"]])

    lv = ic(ax, 140, 96, 174, 122, "U4", "BSS138\nLEVEL SHIFT",
            left=[("LV1", 114), ("LV2", 107), ("LV", 100)],
            right=[("HV1", 114), ("HV2", 107), ("HV", 100)])
    lcd = ic(ax, 194, 88, 230, 122, "U5", "16x2 LCD\nHD44780 + PCF8574",
             left=[("SDA", 114), ("SCL", 107), ("VCC", 100), ("GND", 93)])
    wire(ax, [esp["GPIO21"], lv["LV1"]])
    wire(ax, [esp["GPIO22"], lv["LV2"]])
    wire(ax, [lv["HV1"], lcd["SDA"]])
    wire(ax, [lv["HV2"], lcd["SCL"]])
    wire(ax, [lv["HV"], lcd["VCC"]])
    junction(ax, 186, 100)
    # Net label rather than a flag: no room between the SCL and VCC pins, and
    # naming the net is standard practice anyway.
    ax.text(186, 102.2, "+5 V", ha="center", va="bottom", fontsize=7.9,
            color=PWRC, fontweight="bold", zorder=5)
    pwr_tag(ax, lv["LV"][0], 100, "+3.3 V")
    gnd(ax, lcd["GND"][0], 93, down=4.0)
    ax.text(129, 124, "3.3 V logic side", ha="center", fontsize=7.8, color=PWRC,
            style="italic")
    ax.text(186, 126, "5 V side", ha="center", fontsize=7.8, color="#b8860b",
            style="italic")

    bz = ic(ax, 140, 68, 180, 88, "LS1", "BUZZER MODULE\nonboard NPN",
            left=[("IN", 82), ("VCC", 74)])
    wire(ax, [esp["GPIO23"], (131, 93), (131, 82), bz["IN"]])
    pwr_tag(ax, bz["VCC"][0], 74, "+3.3 V")
    gnd(ax, 160, 68, down=4.0)

    for pn, label in (("GPIO25", "AIN1"), ("GPIO26", "AIN2"),
                      ("GPIO27", "BIN1"), ("GPIO14", "BIN2"),
                      ("GPIO13", "nSLEEP")):
        x, y = esp[pn]
        wire(ax, [(x, y), (x + 10, y)], color=NETC)
        net(ax, x + 10, y, f"{label}   > SH 2", to_right=True, w=44)

    ax.text(4, 10, "All grounds common.  DHT22 data lines are 3.3 V logic and "
                   "connect directly to the MCU.\nThe LCD is the only 5 V device: "
                   "its I2C lines MUST pass through U4.\nThe +5 V net originates at the ESP32 5 V pin (USB-derived).",
            fontsize=8.2, va="bottom", color="#44444e", linespacing=1.7)
    title_block(ax, W, 1, 2, "Controller, Sensors, Display")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ sheet 2
def sheet2(pdf):
    W, H = 242, 132
    fig, ax = page(W, H)
    ax.text(4, H - 3, "SHEET 2 - MOTOR DRIVE AND POWER", fontsize=12,
            fontweight="bold", va="top")

    drv = ic(ax, 80, 34, 126, 110, "U6", "DRV8833\nDUAL H-BRIDGE",
             left=[("AIN1", 102), ("AIN2", 95), ("BIN1", 88), ("BIN2", 81),
                   ("nSLEEP", 74), ("VM", 50), ("GND", 43)],
             right=[("AOUT1", 102), ("AOUT2", 95), ("BOUT1", 81), ("BOUT2", 74)])

    for pn, label in (("AIN1", "AIN1"), ("AIN2", "AIN2"), ("BIN1", "BIN1"),
                      ("BIN2", "BIN2"), ("nSLEEP", "nSLEEP")):
        x, y = drv[pn]
        wire(ax, [(x - 10, y), (x, y)], color=NETC)
        net(ax, x - 54, y, f"SH 1 >   {label}", to_right=False, w=44)

    wire(ax, [drv["AOUT1"], (168, 102)])
    wire(ax, [drv["AOUT2"], (168, 95)])
    cap_v(ax, 150, 102, 95, "C1", "0.1 uF")
    motor(ax, 177, 98.5, 9.0, "M1", "INTAKE FAN\n80mm fan 5V")

    wire(ax, [drv["BOUT1"], (168, 81)])
    wire(ax, [drv["BOUT2"], (168, 74)])
    cap_v(ax, 150, 81, 74, "C2", "0.1 uF")
    motor(ax, 177, 77.5, 9.0, "M2", "EXHAUST FAN\n80mm fan 5V")

    wire(ax, [drv["VM"], (44, 50)])
    battery(ax, 44, 50, 24, "BT1", "4xAA  6 V\nMOTORS ONLY")
    gnd(ax, 44, 24, down=4.0)
    wire(ax, [drv["GND"], (62, 43), (62, 30), (44, 30)])
    junction(ax, 44, 30)

    ax.add_patch(Rectangle((150, 112), 88, 17, fc="#fff4f4", ec="#c0392b",
                           lw=1.5, zorder=6))
    ax.text(194, 124.5, "COMMON GROUND IS MANDATORY", ha="center", fontsize=9.0,
            fontweight="bold", color="#a02020", zorder=7)
    ax.text(194, 117.5,
            "BT1 negative, U6 GND and the ESP32 GND must all tie together,\n"
            "or the H-bridge sees no valid logic level and the motors will not run.",
            ha="center", va="center", fontsize=7.9, color="#a02020",
            zorder=7, linespacing=1.6)

    ax.text(4, 10,
            "C1 and C2 are soldered AT THE MOTOR TERMINALS, not on the breadboard "
            "- brush noise on the I2C bus is the\nmost common failure in this build.  "
            "nSLEEP must be driven HIGH or the bridge stays off.  "
            "Motor supply is separate from logic.",
            fontsize=8.2, va="bottom", color="#44444e", linespacing=1.7)
    title_block(ax, W, 2, 2, "Motor Drive and Power")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.normpath(os.path.join(here, "..", "05_schematic.pdf"))
    with PdfPages(out) as pdf:
        sheet1(pdf)
        sheet2(pdf)
        pdf.infodict()["Title"] = "ESDL Project 1 - Circuit Schematic"
    print("wrote", out)


if __name__ == "__main__":
    main()
