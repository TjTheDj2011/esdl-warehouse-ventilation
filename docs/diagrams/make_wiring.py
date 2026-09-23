#!/usr/bin/env python3
"""ESDL Project 1 - pictorial wiring diagram (3 sheets).

Physical component representation with colour-coded wires and breadboard
power rails. Companion to docs/05_schematic.pdf (logical connectivity).

Regenerate:  python3 docs/diagrams/make_wiring.py
Output:      docs/06_wiring_diagram.pdf
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, Polygon
from matplotlib.backends.backend_pdf import PdfPages

# wire colour code
C5V, C33, CGND = "#d92b2b", "#e8862a", "#17171d"
CSDA, CSCL = "#d4af1a", "#2e9e4f"
CDATA, CCTRL, CMOT = "#2b7fd9", "#8e44ad", "#6d7b84"
CVM = "#b02020"
PWRC = "#1d6b1d"

PCB_ESP, PCB_SENS, PCB_DRV = "#22503a", "#1c4f80", "#8f2020"
PCB_LVL, PCB_BUZ, PCB_LCD = "#3a3a6e", "#1f1f24", "#1d5c4a"
GOLD, TXT = "#d8b24a", "#17171d"
DATE, REV = "2026-09-16", "A"


def page(w=312, h=166):
    fig, ax = plt.subplots(figsize=(16.5, 9.6))
    ax.set_xlim(0, w); ax.set_ylim(0, h); ax.axis("off"); ax.set_aspect("equal")
    return fig, ax


def w(ax, pts, color, lw=2.6, z=6):
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=lw,
            solid_capstyle="round", solid_joinstyle="round", zorder=z)


def arrowhead(ax, x, y, color, down=True, size=2.2):
    """Small filled triangle marking direction of power flow."""
    d = -1 if down else 1
    ax.add_patch(Polygon([(x, y), (x - size, y - d * size * 1.6),
                          (x + size, y - d * size * 1.6)],
                         fc=color, ec="none", zorder=10))


def dot(ax, x, y, color=CGND, r=1.3):
    ax.add_patch(Circle((x, y), r, fc=color, ec="none", zorder=9))


def board(ax, x0, y0, x1, y1, fc, title, sub="", tfs=9.0, tcol="white", ty=None):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0,
                                boxstyle="round,pad=0.4,rounding_size=1.4",
                                fc=fc, ec="#0d0d12", lw=1.4, zorder=3))
    cy = (y0 + y1) / 2 if ty is None else ty
    ax.text((x0 + x1) / 2, cy + (2.6 if sub else 0), title, ha="center",
            va="center", fontsize=tfs, fontweight="bold", color=tcol, zorder=5)
    if sub:
        ax.text((x0 + x1) / 2, cy - 2.8, sub, ha="center", va="center",
                fontsize=7.4, color=tcol, zorder=5, linespacing=1.4)


def pads(ax, names, x, y0, dy, label_x, label_ha, fs=7.2, tcol="white"):
    """Pin header. Labels print INSIDE the board like real silkscreen, which
    keeps the wire-routing corridor outside the board completely clear."""
    out = {}
    for i, n in enumerate(names):
        y = y0 - i * dy
        ax.add_patch(Rectangle((x - 1.5, y - 1.5), 3, 3, fc=GOLD,
                               ec="#7a5f1c", lw=0.7, zorder=5))
        ax.text(label_x, y, n, ha=label_ha, va="center", fontsize=fs,
                color=tcol, zorder=6)
        out[n] = (x, y)
    return out


def rails(ax, x0, x1, y5, y33, ygnd, show5=True):
    if show5:
        w(ax, [(x0, y5), (x1, y5)], C5V, lw=3.0, z=4)
        ax.text(x0 - 2, y5, "+5 V", ha="right", va="center", fontsize=8.2,
                color=C5V, fontweight="bold")
    w(ax, [(x0, y33), (x1, y33)], C33, lw=3.0, z=4)
    w(ax, [(x0, ygnd), (x1, ygnd)], CGND, lw=3.0, z=4)
    ax.text(x0 - 2, y33, "+3.3 V", ha="right", va="center", fontsize=8.2,
            color=C33, fontweight="bold")
    ax.text(x0 - 2, ygnd, "GND", ha="right", va="center", fontsize=8.2,
            color=CGND, fontweight="bold")


def esp32(ax, x0, y0, x1, y1, left, right):
    """Dev board with USB, shield can and two headers."""
    board(ax, x0, y0, x1, y1, PCB_ESP, "", "")
    ax.add_patch(Rectangle((x0 + 12, y1 - 1), 14, 5, fc="#b9bcc2",
                           ec="#6d7076", lw=1.0, zorder=4))
    ax.text(x0 + 19, y1 + 5.5, "USB-C", ha="center", fontsize=7.0, color="#55555f")
    ax.add_patch(Rectangle((x0 + 4, y1 - 24), (x1 - x0) - 8, 20, fc="#c6c9ce",
                           ec="#80838a", lw=1.0, zorder=4))
    ax.text((x0 + x1) / 2, y1 - 14, "ESP32-WROOM-32", ha="center", va="center",
            fontsize=8.0, fontweight="bold", color="#2b2b33", zorder=5)
    lp = pads(ax, [n for n, _ in left], x0 + 3, left[0][1], 0,
              side="right") if False else {}
    lp = {}
    for n, y in left:
        ax.add_patch(Rectangle((x0 + 1.5, y - 1.5), 3, 3, fc=GOLD,
                               ec="#7a5f1c", lw=0.7, zorder=5))
        ax.text(x0 + 6.0, y, n, ha="left", va="center", fontsize=7.2,
                color="white", zorder=6)
        lp[n] = (x0 + 3, y)
    rp = {}
    for n, y in right:
        ax.add_patch(Rectangle((x1 - 4.5, y - 1.5), 3, 3, fc=GOLD,
                               ec="#7a5f1c", lw=0.7, zorder=5))
        ax.text(x1 - 6.0, y, n, ha="right", va="center", fontsize=7.2,
                color="white", zorder=6)
        rp[n] = (x1 - 3, y)
    return lp, rp


def hlegend(ax, x, y, items, wid=25.0, header=None):
    if header:
        ax.text(x, y + 5.0, header, fontsize=8.0, fontweight="bold", va="center")
    for i, (col, lab) in enumerate(items):
        xx = x + i * wid
        w(ax, [(xx, y), (xx + 7, y)], col, lw=2.8, z=9)
        ax.text(xx + 8.5, y, lab, ha="left", va="center", fontsize=7.4, zorder=9)


def legend(ax, x, y, items, title="WIRE COLOUR CODE"):
    ax.add_patch(Rectangle((x, y), 52, 8 + 5.4 * len(items), fc="white",
                           ec="#7a8899", lw=1.2, zorder=8))
    ax.text(x + 26, y + 5.4 * len(items) + 3.6, title, ha="center",
            fontsize=8.0, fontweight="bold", zorder=9)
    for i, (col, lab) in enumerate(items):
        yy = y + 5.4 * (len(items) - 1 - i) + 4.0
        w(ax, [(x + 3, yy), (x + 13, yy)], col, lw=2.8, z=9)
        ax.text(x + 16, yy, lab, ha="left", va="center", fontsize=7.6, zorder=9)


def title_block(ax, W, sheet, total, subtitle):
    bw, bh = 88, 22
    x0, y0 = W - bw - 2, 2
    ax.add_patch(Rectangle((x0, y0), bw, bh, fc="white", ec=TXT, lw=1.6, zorder=10))
    ax.plot([x0, x0 + bw], [y0 + bh - 8.5, y0 + bh - 8.5], color=TXT, lw=1.1, zorder=11)
    ax.plot([x0, x0 + bw], [y0 + 7.5, y0 + 7.5], color=TXT, lw=1.1, zorder=11)
    ax.plot([x0 + 40, x0 + 40], [y0, y0 + 7.5], color=TXT, lw=1.1, zorder=11)
    ax.plot([x0 + 63, x0 + 63], [y0, y0 + 7.5], color=TXT, lw=1.1, zorder=11)
    ax.text(x0 + bw / 2, y0 + bh - 4.2, "ESDL PROJECT 1 - WIRING DIAGRAM",
            ha="center", va="center", fontsize=8.5, fontweight="bold", zorder=11)
    ax.text(x0 + bw / 2, y0 + 11.6, subtitle, ha="center", va="center",
            fontsize=8.0, zorder=11)
    ax.text(x0 + 2, y0 + 3.7, "TJ / Tabitha", ha="left", va="center", fontsize=7.4, zorder=11)
    ax.text(x0 + 42, y0 + 3.7, DATE, ha="left", va="center", fontsize=7.4, zorder=11)
    ax.text(x0 + 65, y0 + 3.7, f"REV {REV}  SH {sheet}/{total}", ha="left",
            va="center", fontsize=7.4, zorder=11)


NOTE_CROSS = ("Wires that cross are NOT connected unless a solid dot is shown.\n"
              "Pin headers are drawn grouped for clarity - match pins by their "
              "silkscreen LABEL, not by physical position.")


# =================================================================== sheet 1
def sheet1(pdf):
    W, H = 312, 166
    fig, ax = page(W, H)
    ax.text(4, H - 3, "SHEET 1 - SENSORS, DISPLAY AND ALARM", fontsize=12.5,
            fontweight="bold", va="top")

    lp, rp = esp32(ax, 118, 64, 162, 152,
                   left=[("GPIO4", 118), ("GPIO16", 110), ("3V3", 82), ("GND", 74)],
                   right=[("GPIO21", 118), ("GPIO22", 110), ("GPIO23", 102),
                          ("5V", 82), ("GND", 74)])
    ax.text(140, 60, "ESP32 DEV BOARD", ha="center", fontsize=8.4,
            fontweight="bold", color="#33333c")

    rails(ax, 26, 300, 50, 43, 36)

    board(ax, 10, 108, 62, 140, PCB_SENS, "DHT22  #1", "CHAMBER / INSIDE", ty=134)
    d1 = pads(ax, ["VCC", "DATA", "GND"], 64, 124, 6.0, 57, "right")
    board(ax, 10, 70, 62, 102, PCB_SENS, "DHT22  #2", "AMBIENT / OUTSIDE", ty=96)
    d2 = pads(ax, ["VCC", "DATA", "GND"], 64, 87, 6.0, 57, "right")

    w(ax, [d1["DATA"], lp["GPIO4"]], CDATA)
    w(ax, [d2["DATA"], (96, 81), (96, 110), lp["GPIO16"]], CDATA)
    w(ax, [d1["VCC"], (108, 124), (108, 43)], C33); dot(ax, 108, 43, C33)
    w(ax, [d1["GND"], (104, 112), (104, 36)], CGND); dot(ax, 104, 36, CGND)
    w(ax, [d2["VCC"], (92, 87), (92, 43)], C33); dot(ax, 92, 43, C33)
    w(ax, [d2["GND"], (88, 75), (88, 36)], CGND); dot(ax, 88, 36, CGND)

    w(ax, [lp["3V3"], (112, 82), (112, 43)], C33); dot(ax, 112, 43, C33)
    w(ax, [lp["GND"], (110, 74), (110, 36)], CGND); dot(ax, 110, 36, CGND)
    w(ax, [rp["5V"], (172, 82), (172, 50)], C5V); dot(ax, 172, 50, C5V)
    w(ax, [rp["GND"], (176, 74), (176, 36)], CGND); dot(ax, 176, 36, CGND)
    # Direction of flow: these pins SOURCE the rails, they are not inputs.
    arrowhead(ax, 112, 56, C33)
    arrowhead(ax, 172, 62, C5V)
    ax.add_patch(Rectangle((8, 2), 210, 13, fc="#eef7ee", ec=PWRC,
                           lw=1.4, zorder=8))
    ax.text(113, 11.6, "3V3 and 5V are OUTPUTS of the dev board",
            ha="center", fontsize=8.4, fontweight="bold", color=PWRC, zorder=9)
    ax.text(113, 6.0,
            "USB feeds the board and its regulator makes 3.3 V - both pins SOURCE "
            "the rails.   NEVER feed an external\nsupply into 3V3: it bypasses the "
            "regulator and destroys the ESP32.",
            ha="center", va="center", fontsize=7.3, color="#2d5a2d", zorder=9,
            linespacing=1.6)

    board(ax, 186, 104, 224, 144, PCB_LVL, "BSS138", "LEVEL SHIFTER", ty=112)
    lvL = pads(ax, ["LV", "LV1", "LV2", "GND"], 184, 138, 6.0, 191, "left")
    lvR = pads(ax, ["HV", "HV1", "HV2", "GND"], 226, 138, 6.0, 219, "right")

    w(ax, [rp["GPIO21"], (180, 118), (180, 132), lvL["LV1"]], CSDA)
    w(ax, [rp["GPIO22"], (178, 110), (178, 126), lvL["LV2"]], CSCL)
    w(ax, [lvL["LV"], (181, 138), (181, 43)], C33); dot(ax, 181, 43, C33)
    w(ax, [lvL["GND"], (183, 120), (183, 36)], CGND); dot(ax, 183, 36, CGND)

    board(ax, 252, 104, 296, 148, PCB_LCD, "16x2 LCD", "HD44780 + PCF8574", ty=116)
    ax.add_patch(Rectangle((266, 128), 26, 16, fc="#2f7f5f", ec="#123",
                           lw=1.0, zorder=4))
    lcd = pads(ax, ["GND", "VCC", "SDA", "SCL"], 250, 140, 6.0, 257, "left")

    w(ax, [lvR["HV1"], (240, 132), (240, 128), lcd["SDA"]], CSDA)
    w(ax, [lvR["HV2"], (236, 126), (236, 122), lcd["SCL"]], CSCL)
    w(ax, [lvR["HV"], (232, 138), (232, 50)], C5V); dot(ax, 232, 50, C5V)
    w(ax, [lvR["GND"], (229, 120), (229, 36)], CGND); dot(ax, 229, 36, CGND)
    w(ax, [lcd["VCC"], (246, 134), (246, 50)], C5V); dot(ax, 246, 50, C5V)
    w(ax, [lcd["GND"], (243, 140), (243, 36)], CGND); dot(ax, 243, 36, CGND)

    board(ax, 186, 64, 220, 98, PCB_BUZ, "BUZZER", "MODULE (NPN)", ty=72)
    ax.add_patch(Circle((210, 88), 4.4, fc="#4a4a52", ec="#1a1a20", lw=1.0, zorder=4))
    bz = pads(ax, ["VCC", "I/O", "GND"], 184, 92, 6.0, 191, "left")
    w(ax, [rp["GPIO23"], (170, 102), (170, 86), bz["I/O"]], CCTRL)
    w(ax, [bz["VCC"], (174, 92), (174, 43)], C33); dot(ax, 174, 43, C33)
    w(ax, [bz["GND"], (179, 80), (179, 36)], CGND); dot(ax, 179, 36, CGND)

    ax.text(8, 32, "WIRE COLOURS", fontsize=8.0, fontweight="bold", va="center")
    hlegend(ax, 56, 32, [(C5V, "+5 V"), (C33, "+3.3 V"), (CGND, "GND"),
                         (CSDA, "I2C SDA"), (CSCL, "I2C SCL"),
                         (CDATA, "DHT22 data"), (CCTRL, "buzzer")], wid=23.0)
    ax.text(8, 28,
            "Wires that cross are NOT connected unless a solid dot is shown.\n"
            "Pin headers are grouped for clarity - match pins by silkscreen "
            "LABEL, not position.\n"
            "The LCD is the only 5 V part: its SDA/SCL MUST pass through the "
            "BSS138.",
            fontsize=7.3, va="top", color="#44444e", linespacing=1.8)
    title_block(ax, W, 1, 3, "Sensors, Display and Alarm")
    pdf.savefig(fig, bbox_inches="tight"); plt.close(fig)


# =================================================================== sheet 2
def sheet2(pdf):
    W, H = 312, 166
    fig, ax = page(W, H)
    ax.text(4, H - 3, "SHEET 2 - MOTOR DRIVE AND POWER", fontsize=12.5,
            fontweight="bold", va="top")

    lp, rp = esp32(ax, 74, 62, 118, 146,
                   left=[],
                   right=[("GPIO25", 128), ("GPIO26", 121), ("GPIO27", 114),
                          ("GPIO14", 107), ("GPIO13", 100), ("GND", 74)])
    ax.text(96, 58, "ESP32 DEV BOARD", ha="center", fontsize=8.4,
            fontweight="bold", color="#33333c")

    board(ax, 176, 86, 222, 140, PCB_DRV, "DRV8833", "DUAL H-BRIDGE")
    dl = pads(ax, ["AIN1", "AIN2", "BIN1", "BIN2", "SLP"], 174, 134, 7.0,
              181, "left")
    dl2 = pads(ax, ["VM", "GND"], 174, 96, 6.0, 181, "left")
    dr = pads(ax, ["AOUT1", "AOUT2", "BOUT1", "BOUT2"], 224, 132, 12.0,
              217, "right")

    for src, dst, vx in ((rp["GPIO25"], dl["AIN1"], 168),
                         (rp["GPIO26"], dl["AIN2"], 164),
                         (rp["GPIO27"], dl["BIN1"], 160),
                         (rp["GPIO14"], dl["BIN2"], 156),
                         (rp["GPIO13"], dl["SLP"], 152)):
        w(ax, [src, (vx, src[1]), (vx, dst[1]), dst], CCTRL, lw=2.2)

    for (o1, o2, cy, ref, name) in ((dr["AOUT1"], dr["AOUT2"], 126, "M1", "INTAKE FAN"),
                                    (dr["BOUT1"], dr["BOUT2"], 102, "M2", "EXHAUST FAN")):
        w(ax, [o1, (240, o1[1]), (240, cy + 5)], CMOT)
        w(ax, [o2, (246, o2[1]), (246, cy - 5)], CMOT)
        w(ax, [(240, cy + 5), (266, cy + 5)], CMOT)
        w(ax, [(246, cy - 5), (266, cy - 5)], CMOT)
        ax.plot([254, 254], [cy + 5, cy + 1.4], color=CMOT, lw=2.0, zorder=6)
        ax.plot([254, 254], [cy - 5, cy - 1.4], color=CMOT, lw=2.0, zorder=6)
        ax.plot([250.4, 257.6], [cy + 1.4, cy + 1.4], color="#2b2b33", lw=2.2, zorder=7)
        ax.plot([250.4, 257.6], [cy - 1.4, cy - 1.4], color="#2b2b33", lw=2.2, zorder=7)
        dot(ax, 254, cy + 5, CMOT); dot(ax, 254, cy - 5, CMOT)
        pass  # brushless fans need no brush-noise suppression capacitor
        ax.add_patch(Circle((276, cy), 8.4, fc="#8c8f96", ec="#3a3d44", lw=1.4, zorder=4))
        ax.add_patch(Rectangle((284, cy - 1.2), 6, 2.4, fc="#6d7078",
                               ec="#3a3d44", lw=0.9, zorder=4))
        ax.add_patch(Polygon([(290, cy), (300, cy + 7), (300, cy - 7)],
                             fc="#c8ccd2", ec="#3a3d44", lw=1.0, zorder=4))
        ax.text(276, cy, "M", ha="center", va="center", fontsize=11,
                fontweight="bold", color="white", zorder=6)
        ax.text(282, cy - 12.5, f"{ref}  {name}", ha="center", fontsize=8.2,
                fontweight="bold")

    board(ax, 110, 28, 170, 50, "#4a4a52", "5 V  2 A  SUPPLY", "FANS ONLY")
    w(ax, [(170, 44), (172, 44), (172, 96), dl2["VM"]], CVM, lw=2.8)
    ax.text(166, 70, "+5 V", fontsize=7.8, color=CVM, fontweight="bold", ha="right")
    w(ax, [(170, 34), (178, 34), (178, 58), (150, 58), (150, 66)], CGND, lw=2.8)
    w(ax, [dl2["GND"], (150, 90), (150, 66)], CGND, lw=2.8)
    w(ax, [rp["GND"], (132, 74), (132, 66), (150, 66)], CGND, lw=2.8)
    dot(ax, 150, 66, CGND)

    ax.add_patch(Rectangle((6, 96), 62, 32, fc="#fff4f4", ec="#c0392b",
                           lw=1.6, zorder=8))
    ax.text(37, 123, "COMMON GROUND", ha="center", va="top", fontsize=8.8,
            fontweight="bold", color="#a02020", zorder=9)
    ax.text(37, 115,
            "Battery negative, DRV8833 GND and\n"
            "ESP32 GND must ALL tie together at\n"
            "one point, or the bridge never sees\na valid logic level.",
            ha="center", va="top", fontsize=7.3, color="#a02020", zorder=9,
            linespacing=1.6)

    hlegend(ax, 8, 26, [(CCTRL, "control signals"), (CVM, "+5 V fans"),
                        (CGND, "GND"), (CMOT, "motor output")], wid=40.0,
            header="WIRE COLOURS")
    ax.text(8, 18, NOTE_CROSS, fontsize=7.6, va="top", color="#44444e",
            linespacing=1.8)
    ax.text(8, 5, "Fan supply NEVER comes from the ESP32 or USB.  Brushless fans need "
                  "no suppression caps - that risk is designed out.",
            fontsize=7.8, va="top", color="#a02020")
    title_block(ax, W, 2, 3, "Motor Drive and Power")
    pdf.savefig(fig, bbox_inches="tight"); plt.close(fig)


# =================================================================== sheet 3
ROWS = [
    ("DHT22 #1 (chamber)", "VCC", "+3.3 V rail", "orange", "module has the pull-up"),
    ("", "DATA", "ESP32  GPIO 4", "blue", "3.3 V logic, direct"),
    ("", "GND", "GND rail", "black", ""),
    ("DHT22 #2 (ambient)", "VCC", "+3.3 V rail", "orange", "keep clear of exhaust plume"),
    ("", "DATA", "ESP32  GPIO 16", "blue", "3.3 V logic, direct"),
    ("", "GND", "GND rail", "black", ""),
    ("BSS138 shifter", "LV", "+3.3 V rail", "orange", "low side reference"),
    ("", "LV1", "ESP32  GPIO 21", "yellow", "SDA, 3.3 V side"),
    ("", "LV2", "ESP32  GPIO 22", "green", "SCL, 3.3 V side"),
    ("", "HV", "+5 V rail", "red", "high side reference"),
    ("", "HV1", "LCD  SDA", "yellow", "5 V side"),
    ("", "HV2", "LCD  SCL", "green", "5 V side"),
    ("", "GND x2", "GND rail", "black", "both GND pins"),
    ("16x2 LCD (PCF8574)", "VCC", "+5 V rail", "red", "5 V for contrast"),
    ("", "GND", "GND rail", "black", ""),
    ("", "SDA / SCL", "BSS138 HV1 / HV2", "yellow / green", "NEVER direct to ESP32"),
    ("Buzzer module", "VCC", "+3.3 V rail", "orange", "module with onboard NPN"),
    ("", "I/O", "ESP32  GPIO 23", "purple", ""),
    ("", "GND", "GND rail", "black", ""),
    ("DRV8833 driver", "AIN1 / AIN2", "ESP32  GPIO 25 / 26", "purple", "intake fan"),
    ("", "BIN1 / BIN2", "ESP32  GPIO 27 / 14", "purple", "exhaust fan"),
    ("", "SLP (nSLEEP)", "ESP32  GPIO 13", "purple", "HIGH enables the bridge"),
    ("", "VM", "5 V fan supply +", "red", "never from the ESP32"),
    ("", "GND", "Battery -  AND  ESP32 GND", "black", "COMMON GROUND - mandatory"),
    ("", "AOUT1 / AOUT2", "M1 intake fan", "grey", "brushless, one direction"),
    ("", "BOUT1 / BOUT2", "M2 exhaust fan", "grey", "brushless, one direction"),
    ("Power", "ESP32 3V3", "+3.3 V rail", "orange", "logic supply"),
    ("", "ESP32 5V", "+5 V rail", "red", "USB-derived, LCD only"),
    ("", "ESP32 GND", "GND rail", "black", ""),
]


def sheet3(pdf):
    W, H = 312, 166
    fig, ax = page(W, H)
    ax.text(4, H - 4, "SHEET 3 - CONNECTION TABLE", fontsize=12.5,
            fontweight="bold", va="top")
    ax.text(4, H - 11, "Tick each row as you wire it. Build one component at a "
                       "time and verify with the serial console before the next.",
            fontsize=8.4, va="top", color="#55555f")

    cols = [8, 30, 84, 142, 188, 228]
    hdr = ["", "COMPONENT", "PIN", "CONNECTS TO", "WIRE", "NOTE"]
    ytop, dy = 146, 4.2
    ax.add_patch(Rectangle((6, ytop - 1.5), 300, 6, fc="#e9edf2", ec="#7a8899",
                           lw=1.0, zorder=3))
    for cx, hname in zip(cols, hdr):
        ax.text(cx, ytop + 1.4, hname, fontsize=8.0, fontweight="bold",
                va="center", zorder=5)
    y = ytop - 4.6
    for i, (comp, p, to, col, note) in enumerate(ROWS):
        if i % 2 == 0:
            ax.add_patch(Rectangle((6, y - 1.9), 300, dy, fc="#f6f8fa",
                                   ec="none", zorder=2))
        ax.add_patch(Rectangle((cols[0], y - 1.3), 2.6, 2.6, fc="white",
                               ec="#55555f", lw=0.9, zorder=4))
        if comp:
            ax.text(cols[1], y, comp, fontsize=7.5, va="center",
                    fontweight="bold", zorder=5)
        ax.text(cols[2], y, p, fontsize=7.5, va="center", zorder=5)
        ax.text(cols[3], y, to, fontsize=7.5, va="center", zorder=5)
        ax.text(cols[4], y, col, fontsize=7.5, va="center", zorder=5,
                color="#33333c")
        ax.text(cols[5], y, note, fontsize=7.2, va="center", zorder=5,
                color="#a02020" if "mandatory" in note or "NEVER" in note else "#55555f")
        y -= dy
    title_block(ax, W, 3, 3, "Connection Table")
    pdf.savefig(fig, bbox_inches="tight"); plt.close(fig)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.normpath(os.path.join(here, "..", "06_wiring_diagram.pdf"))
    with PdfPages(out) as pdf:
        sheet1(pdf); sheet2(pdf); sheet3(pdf)
        pdf.infodict()["Title"] = "ESDL Project 1 - Wiring Diagram"
    print("wrote", out)


if __name__ == "__main__":
    main()
