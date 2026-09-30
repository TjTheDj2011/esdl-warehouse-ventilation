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
REV, DATE = "B", "2026-09-30"


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


# ------------------------------------------------------------------ helpers
def netlbl(ax, x, y, text, side="right", length=6.0):
    """Short wire ending in a net name. Wires carrying the same name connect."""
    d = 1 if side == "right" else -1
    wire(ax, [(x, y), (x + d * length, y)])
    ax.text(x + d * (length + 1.2), y, text, ha="left" if d > 0 else "right",
            va="center", fontsize=8.0, color=NETC, fontweight="bold", zorder=5)


def dc_source(ax, cx, cy, r, ref, name):
    ax.add_patch(Circle((cx, cy), r, fc=FILL, ec=BLK, lw=1.7, zorder=3))
    ax.text(cx, cy + r * 0.45, "+", ha="center", va="center", fontsize=12,
            fontweight="bold", zorder=5)
    ax.text(cx, cy - r * 0.45, "−", ha="center", va="center", fontsize=12,
            fontweight="bold", zorder=5)
    ax.text(cx - r - 3.5, cy, f"{ref}\n{name}", ha="right", va="center",
            fontsize=8.3, zorder=5, linespacing=1.5)


# ------------------------------------------------------------------ sheet 1
def sheet1(pdf):
    W, H = 262, 134
    fig, ax = page(W, H)
    ax.text(4, H - 3, "SHEET 1 - CONTROLLER, SENSORS, DISPLAY", fontsize=12,
            fontweight="bold", va="top")

    esp = ic(ax, 84, 26, 124, 124, "U1", "ESP32-WROOM-32\n3.3 V logic",
             left=[("3V3", 118), ("GND", 111), ("GPIO4", 96), ("GPIO16", 88)],
             right=[("GPIO21", 118), ("GPIO22", 112), ("GPIO17", 104),
                    ("GPIO18", 98), ("GPIO23", 88), ("GPIO25", 66),
                    ("GPIO26", 60), ("GPIO27", 54), ("GPIO14", 48),
                    ("GPIO13", 42), ("GPIO19", 36)])
    pwr_tag(ax, esp["3V3"][0], 118, "+3.3 V")
    gnd(ax, esp["GND"][0], 111, down=4.0)

    # Temperature probes. Each breakout carries its own 4.7k pull-up on DQ.
    s1 = ic(ax, 26, 88, 62, 108, "U2", "DS18B20 #1\nCHAMBER",
            left=[("VCC", 104), ("GND", 92)], right=[("DQ", 98)])
    s2 = ic(ax, 26, 58, 62, 78, "U3", "DS18B20 #2\nAMBIENT",
            left=[("VCC", 74), ("GND", 62)], right=[("DQ", 68)])
    for dd in (s1, s2):
        pwr_tag(ax, dd["VCC"][0], dd["VCC"][1], "+3.3 V")
        gnd(ax, dd["GND"][0], dd["GND"][1], down=4.0)
    wire(ax, [s1["DQ"], (72, 98), (72, 96), esp["GPIO4"]])
    wire(ax, [s2["DQ"], (74, 68), (74, 88), esp["GPIO16"]])

    # Two hardware I2C buses. Named nets connect to the panels on the right.
    netlbl(ax, *esp["GPIO21"], "SDA0")
    netlbl(ax, *esp["GPIO22"], "SCL0")
    netlbl(ax, *esp["GPIO17"], "SDA1")
    netlbl(ax, *esp["GPIO18"], "SCL1")

    bz = ic(ax, 152, 74, 188, 94, "LS1", "BUZZER MODULE\nactive LOW",
            left=[("IN", 88), ("VCC", 80)])
    wire(ax, [esp["GPIO23"], bz["IN"]])
    pwr_tag(ax, bz["VCC"][0], 80, "+3.3 V")
    gnd(ax, 170, 74, down=4.0)

    for pn, label in (("GPIO25", "AIN1"), ("GPIO26", "AIN2"),
                      ("GPIO27", "BIN1"), ("GPIO14", "BIN2"),
                      ("GPIO13", "nSLEEP"), ("GPIO19", "nFAULT")):
        x, y = esp[pn]
        wire(ax, [(x, y), (x + 6, y)], color=NETC)
        net(ax, x + 6, y, f"{label}   > SH 2", to_right=True, w=46)

    # Three SSD1306 panels: one on bus 0, two sharing bus 1 at 0x3C and 0x3D.
    panels = (("U4", "SSD1306 OLED\nbus 0  ·  0x3C", 102, "SDA0", "SCL0"),
              ("U5", "SSD1306 OLED\nbus 1  ·  0x3C", 70, "SDA1", "SCL1"),
              ("U6", "SSD1306 OLED\nbus 1  ·  0x3D", 38, "SDA1", "SCL1"))
    for ref, name, y0, sda, scl in panels:
        u = ic(ax, 214, y0, 254, y0 + 24, ref, name,
               left=[("SDA", y0 + 20), ("SCL", y0 + 14), ("VCC", y0 + 8),
                     ("GND", y0 + 2)])
        netlbl(ax, *u["SDA"], sda, side="left")
        netlbl(ax, *u["SCL"], scl, side="left")
        pwr_tag(ax, u["VCC"][0], u["VCC"][1], "+3.3 V")
        gnd(ax, u["GND"][0], u["GND"][1], down=3.0)

    ax.text(4, 10,
            "All grounds common.  Every device is 3.3 V native, so there is no level "
            "shifter anywhere.  Nets with the same name are connected.\n"
            "Each DS18B20 breakout carries its own 4.7 kΩ pull-up on DQ.  "
            "OLED roles IN / OUT / STATE are assigned by the firmware at boot.\n"
            "The buzzer module sounds when its input is pulled LOW.",
            fontsize=8.2, va="bottom", color="#44444e", linespacing=1.7)
    title_block(ax, W, 1, 2, "Controller, Sensors, Display")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ sheet 2
def sheet2(pdf):
    W, H = 262, 134
    fig, ax = page(W, H)
    ax.text(4, H - 3, "SHEET 2 - FAN DRIVE AND POWER", fontsize=12,
            fontweight="bold", va="top")

    drv = ic(ax, 96, 30, 142, 114, "U7", "DRV8833\nDUAL H-BRIDGE",
             left=[("AIN1", 106), ("AIN2", 99), ("BIN1", 92), ("BIN2", 85),
                   ("nSLEEP", 78), ("nFAULT", 71), ("VM", 50), ("GND", 42)],
             right=[("AOUT1", 106), ("AOUT2", 99), ("BOUT1", 85),
                    ("BOUT2", 78)])

    for pn in ("AIN1", "AIN2", "BIN1", "BIN2", "nSLEEP", "nFAULT"):
        x, y = drv[pn]
        wire(ax, [(x - 10, y), (x, y)], color=NETC)
        net(ax, x - 56, y, f"SH 1 >   {pn}", to_right=False, w=46)

    wire(ax, [drv["AOUT1"], (172, 106)])
    wire(ax, [drv["AOUT2"], (172, 99)])
    ax.text(160, 108.2, "red (+)", ha="center", fontsize=7.6, color="#44444e")
    ax.text(160, 101.2, "black", ha="center", fontsize=7.6, color="#44444e")
    motor(ax, 181, 102.5, 9.0, "M1", "INTAKE FAN\n80 mm brushless, 5 V")

    wire(ax, [drv["BOUT1"], (172, 85)])
    wire(ax, [drv["BOUT2"], (172, 78)])
    ax.text(160, 87.2, "red (+)", ha="center", fontsize=7.6, color="#44444e")
    ax.text(160, 80.2, "black", ha="center", fontsize=7.6, color="#44444e")
    motor(ax, 181, 81.5, 9.0, "M2", "EXHAUST FAN\n80 mm brushless, 5 V")

    # Fan supply. Separate from the ESP32, which runs from USB.
    dc_source(ax, 50, 46, 7.0, "PS1", "5 V 2 A\nwall supply\nFANS ONLY")
    wire(ax, [(50, 53), (50, 58), (84, 58), (84, 50), drv["VM"]])
    wire(ax, [(50, 39), (50, 30)])
    wire(ax, [drv["GND"], (84, 42), (84, 30), (50, 30)])
    junction(ax, 50, 30)
    gnd(ax, 50, 30, down=4.0)
    ax.text(58, 23.5, "to ESP32 GND (sheet 1)", ha="left", fontsize=7.8,
            color="#44444e", style="italic")

    ax.add_patch(Rectangle((160, 112), 88, 17, fc="#fff4f4", ec="#c0392b",
                           lw=1.5, zorder=6))
    ax.text(204, 124.5, "COMMON GROUND IS MANDATORY", ha="center", fontsize=9.0,
            fontweight="bold", color="#a02020", zorder=7)
    ax.text(204, 117.5,
            "PS1 negative, U7 GND and the ESP32 GND must all tie together,\n"
            "or the H-bridge sees no valid logic level and the fans will not run.",
            ha="center", va="center", fontsize=7.9, color="#a02020",
            zorder=7, linespacing=1.6)

    ax.text(4, 10,
            "Fans are brushless and only ever switched one direction, so no "
            "suppression capacitors are fitted.\n"
            "nSLEEP must be driven HIGH or the bridge stays off.  nFAULT is open "
            "drain: GPIO 19 reads it through the internal pull-up.\n"
            "Fan power never passes through the ESP32, which runs from USB.",
            fontsize=8.2, va="bottom", color="#44444e", linespacing=1.7)
    title_block(ax, W, 2, 2, "Fan Drive and Power")
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
