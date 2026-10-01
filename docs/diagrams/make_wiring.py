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
from math import cos, sin, radians
from matplotlib.patches import (FancyBboxPatch, Rectangle, Circle, Polygon,
                                Arc, Wedge)
from matplotlib.backends.backend_pdf import PdfPages

# wire colour code
C5V, C33, CGND = "#d92b2b", "#e8862a", "#17171d"
CSDA, CSCL = "#d4af1a", "#2e9e4f"
CDATA, CCTRL, CMOT = "#2b7fd9", "#8e44ad", "#6d7b84"
CVM = "#b02020"
PWRC = "#1d6b1d"

PCB_ESP, PCB_SENS, PCB_DRV = "#22503a", "#1c4f80", "#8f2020"
PCB_BUZ, PCB_OLED = "#1f1f24", "#14324f"
GOLD, TXT = "#d8b24a", "#17171d"
DATE, REV = "2026-09-30", "B"


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


def hop(ax, x, y, hcol, vcol, r=1.9, lw=2.6):
    """A horizontal wire bridging OVER a vertical one at (x, y): they are NOT
    connected. Clearer than relying on the absence of a junction dot."""
    ax.plot([x - r, x + r], [y, y], color="white", lw=lw + 3.0, zorder=7,
             solid_capstyle="butt")
    ax.plot([x, x], [y - r - 0.8, y + r + 0.8], color=vcol, lw=lw, zorder=8,
            solid_capstyle="butt")
    ax.add_patch(Arc((x, y), 2 * r, 2 * r, theta1=0, theta2=180, color=hcol,
                     lw=lw, zorder=9))


def oled(ax, x0, y0, role, sub):
    """SSD1306 panel with a lit screen showing the role the firmware gives it.
    I2C pads drawn on the left, power on the right: grouped for clarity, the
    real module has all four on one header (GND VCC SCL SDA)."""
    x1, y1 = x0 + 46, y0 + 30
    board(ax, x0, y0, x1, y1, PCB_OLED, "")
    ax.add_patch(Rectangle((x0 + 12, y0 + 9), 22, 15, fc="#061524",
                           ec="#3b5b7a", lw=1.0, zorder=4))
    ax.text(x0 + 23, y0 + 16.5, role, ha="center", va="center", fontsize=8.6,
            fontweight="bold", color="#9fe3ff", family="monospace", zorder=5)
    ax.text(x0 + 23, y0 + 4.4, sub, ha="center", va="center", fontsize=6.8,
            color="white", zorder=5)
    left = pads(ax, ["SDA", "SCL"], x0 - 2, y1 - 7, 6.0, x0 + 3, "left")
    right = pads(ax, ["VCC", "GND"], x1 + 2, y1 - 7, 6.0, x1 - 3, "right")
    return left, right


def fan80(ax, cx, cy, s, ref, name, where):
    """80 mm brushless fan seen face-on: frame, blades, hub, corner screws."""
    h = s / 2
    ax.add_patch(FancyBboxPatch((cx - h, cy - h), s, s,
                                boxstyle="round,pad=0.2,rounding_size=2.2",
                                fc="#2c2f36", ec="#0d0d12", lw=1.4, zorder=3))
    ax.add_patch(Circle((cx, cy), h * 0.86, fc="#4a4e57", ec="#15171c",
                        lw=1.0, zorder=4))
    for k in range(7):
        a = k * 360 / 7
        ax.add_patch(Wedge((cx, cy), h * 0.80, a, a + 32, fc="#8c919b",
                           ec="#2a2d33", lw=0.6, zorder=5))
    ax.add_patch(Circle((cx, cy), h * 0.30, fc="#202227", ec="#15171c",
                        lw=1.0, zorder=6))
    for dx, dy in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        ax.add_patch(Circle((cx + dx * h * 0.78, cy + dy * h * 0.78), 0.9,
                            fc="#9a9ea6", ec="none", zorder=6))
    ax.text(cx + h + 4, cy + 4.5, f"{ref}  {name}", ha="left", va="center",
            fontsize=8.2, fontweight="bold")
    ax.text(cx + h + 4, cy - 1.0, "80 mm, 5 V, brushless", ha="left",
            va="center", fontsize=7.4, color="#44444e")
    ax.text(cx + h + 4, cy - 5.6, where, ha="left", va="center", fontsize=7.4,
            color="#44444e")


NOTE_HOP = ("A wire that HOPS over another is NOT connected to it; a solid dot "
            "marks a real junction.\nPin headers are grouped for clarity - match "
            "pins by their printed LABEL, not by physical position.")


# =================================================================== sheet 1
def sheet1(pdf):
    W, H = 312, 166
    fig, ax = page(W, H)
    ax.text(4, H - 3, "SHEET 1 - SENSORS, DISPLAYS AND ALARM", fontsize=12.5,
            fontweight="bold", va="top")

    lp, rp = esp32(ax, 118, 56, 162, 152,
                   left=[("D4", 124), ("RX2", 87), ("3V3", 78), ("GND", 70)],
                   right=[("D21", 124), ("D22", 119), ("TX2", 114),
                          ("D18", 108), ("D23", 98)])
    ax.text(140, 52, "ESP32 DEV BOARD", ha="center", fontsize=8.4,
            fontweight="bold", color="#33333c")
    ax.text(140, 48, "RX2 = GPIO 16    TX2 = GPIO 17", ha="center",
            fontsize=7.0, color="#a02020")

    rails(ax, 26, 309, 50, 43, 36, show5=False)

    # Temperature probes. Each breakout carries its own 4.7k pull-up on DQ.
    board(ax, 10, 108, 62, 140, PCB_SENS, "DS18B20  #1", "CHAMBER / INSIDE", ty=133)
    s1 = pads(ax, ["DQ", "VCC", "GND"], 64, 124, 6.0, 57, "right")
    board(ax, 10, 70, 62, 102, PCB_SENS, "DS18B20  #2", "AMBIENT / OUTSIDE", ty=95)
    s2 = pads(ax, ["DQ", "VCC", "GND"], 64, 87, 6.0, 57, "right")

    w(ax, [s1["DQ"], lp["D4"]], CDATA)
    w(ax, [s1["VCC"], (104, 118), (104, 43)], C33); dot(ax, 104, 43, C33)
    w(ax, [s1["GND"], (100, 112), (100, 36)], CGND); dot(ax, 100, 36, CGND)
    w(ax, [s2["VCC"], (84, 81), (84, 43)], C33); dot(ax, 84, 43, C33)
    w(ax, [s2["GND"], (80, 75), (80, 36)], CGND); dot(ax, 80, 36, CGND)
    w(ax, [s2["DQ"], lp["RX2"]], CDATA)
    hop(ax, 100, 87, CDATA, CGND)
    hop(ax, 104, 87, CDATA, C33)

    # The dev board SOURCES the 3.3 V rail; USB-C powers the board itself.
    w(ax, [lp["3V3"], (108, 78), (108, 43)], C33); dot(ax, 108, 43, C33)
    w(ax, [lp["GND"], (112, 70), (112, 36)], CGND); dot(ax, 112, 36, CGND)
    arrowhead(ax, 108, 58, C33)

    # Three panels. Roles are handed out by the firmware in probe order.
    pA, qA = oled(ax, 246, 122, "IN", "bus 0  ·  0x3C")
    pB, qB = oled(ax, 246, 86, "OUT", "bus 1  ·  0x3C")
    pC, qC = oled(ax, 246, 50, "STATE", "bus 1  ·  0x3D")

    # I2C bus 0 -> IN panel
    w(ax, [rp["D21"], (214, 124), (214, 145), pA["SDA"]], CSDA)
    w(ax, [rp["D22"], (220, 119), (220, 139), pA["SCL"]], CSCL)
    # I2C bus 1 -> OUT and STATE panels, shared trunk
    w(ax, [rp["TX2"], (236, 114), (236, 73), pC["SDA"]], CSDA)
    w(ax, [(236, 109), pB["SDA"]], CSDA); dot(ax, 236, 109, CSDA)
    w(ax, [rp["D18"], (230, 108), (230, 67), pC["SCL"]], CSCL)
    w(ax, [(230, 103), pB["SCL"]], CSCL); dot(ax, 230, 103, CSCL)
    hop(ax, 236, 103, CSCL, CSDA)

    # Panel power on the right, nested so no two power wires cross.
    for (pv, pg, xv, xg) in ((qA, qA, 307, 305), (qB, qB, 303, 301),
                             (qC, qC, 299, 297)):
        w(ax, [pv["VCC"], (xv, pv["VCC"][1]), (xv, 43)], C33); dot(ax, xv, 43, C33)
        w(ax, [pg["GND"], (xg, pg["GND"][1]), (xg, 36)], CGND); dot(ax, xg, 36, CGND)

    # Buzzer module (active LOW)
    board(ax, 182, 47, 214, 83, PCB_BUZ, "BUZZER", "active LOW", ty=54)
    ax.add_patch(Circle((206, 73), 4.0, fc="#4a4a52", ec="#1a1a20", lw=1.0, zorder=4))
    bz = pads(ax, ["I/O", "VCC", "GND"], 180, 77, 6.0, 185, "left")
    w(ax, [rp["D23"], (176, 98), (176, 77), bz["I/O"]], CCTRL)
    w(ax, [bz["VCC"], (166, 71), (166, 43)], C33); dot(ax, 166, 43, C33)
    w(ax, [bz["GND"], (172, 65), (172, 36)], CGND); dot(ax, 172, 36, CGND)

    ax.text(8, 30, "WIRE COLOURS", fontsize=8.0, fontweight="bold", va="center")
    hlegend(ax, 56, 30, [(C33, "+3.3 V"), (CGND, "GND"), (CSDA, "I2C SDA"),
                         (CSCL, "I2C SCL"), (CDATA, "1-wire data"),
                         (CCTRL, "buzzer")], wid=26.0)
    ax.text(8, 25.5, NOTE_HOP, fontsize=7.3, va="top", color="#44444e",
            linespacing=1.7)
    ax.add_patch(Rectangle((8, 2), 206, 11, fc="#eef7ee", ec=PWRC, lw=1.4, zorder=8))
    ax.text(111, 10.0, "3V3 is an OUTPUT of the dev board",
            ha="center", fontsize=8.4, fontweight="bold", color=PWRC, zorder=9)
    ax.text(111, 5.0,
            "USB-C powers the ESP32; its regulator feeds every part on this sheet. "
            "Never connect an external supply to 3V3.",
            ha="center", va="center", fontsize=7.2, color="#2d5a2d", zorder=9)
    title_block(ax, W, 1, 3, "Sensors, Displays and Alarm")
    pdf.savefig(fig, bbox_inches="tight"); plt.close(fig)


# =================================================================== sheet 2
def sheet2(pdf):
    W, H = 312, 166
    fig, ax = page(W, H)
    ax.text(4, H - 3, "SHEET 2 - FAN DRIVE AND POWER", fontsize=12.5,
            fontweight="bold", va="top")

    lp, rp = esp32(ax, 74, 62, 118, 146, left=[],
                   right=[("D25", 118), ("D26", 112), ("D27", 106),
                          ("D14", 100), ("D13", 94), ("D19", 88), ("GND", 70)])
    ax.text(96, 58, "ESP32 DEV BOARD", ha="center", fontsize=8.4,
            fontweight="bold", color="#33333c")

    # DRV8833 module, pads named exactly as printed on its underside.
    board(ax, 176, 66, 222, 142, PCB_DRV, "DRV8833", "MODULE", ty=113)
    dl = pads(ax, ["IN1", "IN2", "IN3", "IN4", "EEP", "ULT"], 174, 134, 7.0,
              181, "left")
    dp = pads(ax, ["GND", "VCC"], 174, 80, 6.0, 181, "left")
    do = {}
    for n, y in (("OUT1", 128), ("OUT2", 120), ("OUT3", 100), ("OUT4", 92)):
        do.update(pads(ax, [n], 224, y, 0, 217, "right"))

    # Each wire rises to its pad. The TOP wire turns first (leftmost), so no
    # horizontal run ever passes through another wire's vertical.
    for src, dst, vx in ((rp["D25"], dl["IN1"], 148), (rp["D26"], dl["IN2"], 152),
                         (rp["D27"], dl["IN3"], 156), (rp["D14"], dl["IN4"], 160),
                         (rp["D13"], dl["EEP"], 164), (rp["D19"], dl["ULT"], 168)):
        w(ax, [src, (vx, src[1]), (vx, dst[1]), dst], CCTRL, lw=2.2)
    ax.text(121, 83.5, "D19 reads ULT (fault)", fontsize=6.9, color="#5b2c6f")

    # Fans: red lead to the odd OUT, black lead to the even OUT.
    fan80(ax, 268, 124, 24, "M1", "INTAKE FAN", "mount LOW, one wall")
    fan80(ax, 268, 96, 24, "M2", "EXHAUST FAN", "mount HIGH, opposite wall")
    for o, y, lab in (("OUT1", 128, "red +"), ("OUT2", 120, "black −"),
                      ("OUT3", 100, "red +"), ("OUT4", 92, "black −")):
        w(ax, [do[o], (256, y)], CMOT)
        ax.text(244, y + 2.2, lab, ha="center", fontsize=6.8, color="#44444e")

    # Fan supply: + to VCC, - to the common ground node.
    board(ax, 110, 26, 170, 48, "#4a4a52", "5 V  2 A  SUPPLY", "FANS ONLY", ty=37)
    w(ax, [(156, 48), (156, 54), (172, 54), (172, 74), dp["VCC"]], CVM, lw=2.8)
    ax.text(170, 62, "+5 V", fontsize=7.8, color=CVM, fontweight="bold", ha="right")
    w(ax, [dp["GND"], (140, 80), (140, 60), (124, 60), (124, 48)], CGND, lw=2.8)
    w(ax, [rp["GND"], (140, 70)], CGND, lw=2.8)
    dot(ax, 140, 70, CGND)
    ax.text(124, 44.5, "−", fontsize=10, fontweight="bold", color="white",
            ha="center", va="center", zorder=7)
    ax.text(156, 44.5, "+", fontsize=10, fontweight="bold", color="white",
            ha="center", va="center", zorder=7)

    ax.add_patch(Rectangle((6, 96), 62, 32, fc="#fff4f4", ec="#c0392b",
                           lw=1.6, zorder=8))
    ax.text(37, 123, "COMMON GROUND", ha="center", va="top", fontsize=8.8,
            fontweight="bold", color="#a02020", zorder=9)
    ax.text(37, 115,
            "Supply negative, module GND and\n"
            "ESP32 GND must ALL tie together,\n"
            "or the module never sees a\nvalid logic level.",
            ha="center", va="top", fontsize=7.3, color="#a02020", zorder=9,
            linespacing=1.6)

    ax.add_patch(Rectangle((222, 30), 88, 34, fc="#f6f8fa", ec="#7a8899",
                           lw=1.2, zorder=8))
    ax.text(266, 59.5, "MODULE PINOUT", ha="center", fontsize=8.2,
            fontweight="bold", zorder=9)
    ax.text(225, 54.5, "Labels are printed on the UNDERSIDE.", fontsize=6.9,
            color="#55555f", zorder=9)
    ax.text(225, 48.5, "Header 1:  IN4  IN3  GND  VCC  IN2  IN1", fontsize=7.2,
            family="monospace", zorder=9)
    ax.text(225, 43.0, "Header 2:  EEP  OUT1 OUT2 OUT3 OUT4 ULT", fontsize=7.2,
            family="monospace", zorder=9)
    ax.text(225, 36.5, "J1 (en/sleep) stays OPEN: D13 drives EEP.",
            fontsize=6.9, color="#a02020", zorder=9)

    hlegend(ax, 8, 22, [(CCTRL, "control"), (CVM, "+5 V fans"), (CGND, "GND"),
                        (CMOT, "fan leads")], wid=30.0, header="WIRE COLOURS")
    ax.text(8, 15, NOTE_HOP, fontsize=7.2, va="top", color="#44444e",
            linespacing=1.7)
    ax.text(8, 4.5, "Fan power never passes through the ESP32, which runs from "
                    "USB-C.  Brushless fans: no suppression capacitors.",
            fontsize=7.4, va="center", color="#a02020")
    title_block(ax, W, 2, 3, "Fan Drive and Power")
    pdf.savefig(fig, bbox_inches="tight"); plt.close(fig)


# =================================================================== sheet 3
ROWS = [
    ("DS18B20 #1 (inside)", "DQ", "ESP32  D4  (GPIO 4)", "blue", "module has the 4.7k pull-up"),
    ("", "VCC  /  GND", "+3.3 V rail  /  GND rail", "orange / black", ""),
    ("DS18B20 #2 (outside)", "DQ", "ESP32  RX2  (GPIO 16)", "blue", "printed RX2, not 16"),
    ("", "VCC  /  GND", "+3.3 V rail  /  GND rail", "orange / black", "keep clear of exhaust plume"),
    ("OLED IN  (bus 0, 0x3C)", "SDA  /  SCL", "ESP32  D21  /  D22", "yellow / green", ""),
    ("", "VCC  /  GND", "+3.3 V rail  /  GND rail", "orange / black", "3.3 V only - no shifter"),
    ("OLED OUT  (bus 1, 0x3C)", "SDA  /  SCL", "ESP32  TX2  /  D18", "yellow / green", "printed TX2 = GPIO 17"),
    ("", "VCC  /  GND", "+3.3 V rail  /  GND rail", "orange / black", ""),
    ("OLED STATE  (bus 1, 0x3D)", "SDA  /  SCL", "same bus 1 rows as OUT", "yellow / green", "address pad moved to 0x3D"),
    ("", "VCC  /  GND", "+3.3 V rail  /  GND rail", "orange / black", ""),
    ("Buzzer module", "I/O", "ESP32  D23  (GPIO 23)", "purple", "active LOW: sounds when pulled low"),
    ("", "VCC  /  GND", "+3.3 V rail  /  GND rail", "orange / black", ""),
    ("DRV8833 module", "IN1  /  IN2", "ESP32  D25  /  D26", "purple", "intake fan"),
    ("", "IN3  /  IN4", "ESP32  D27  /  D14", "purple", "exhaust fan"),
    ("", "EEP", "ESP32  D13  (GPIO 13)", "purple", "HIGH enables; leave J1 open"),
    ("", "ULT", "ESP32  D19  (GPIO 19)", "purple", "fault output, open drain"),
    ("", "VCC", "5 V fan supply  +", "red", "NEVER from the ESP32"),
    ("", "GND", "supply  −  AND  ESP32 GND", "black", "COMMON GROUND - mandatory"),
    ("", "OUT1  /  OUT2", "intake fan  red  /  black", "grey", "fan runs one direction only"),
    ("", "OUT3  /  OUT4", "exhaust fan  red  /  black", "grey", "fan runs one direction only"),
    ("Power", "ESP32 USB-C", "computer USB port", "-", "powers the logic"),
    ("", "ESP32 3V3", "+3.3 V rail", "orange", "an OUTPUT - sources the rail"),
    ("", "ESP32 GND", "GND rail", "black", ""),
    ("Leave unwired", "GPIO 33", "nothing", "-", "bench-test reference pin"),
]


def sheet3(pdf):
    W, H = 312, 166
    fig, ax = page(W, H)
    ax.text(4, H - 4, "SHEET 3 - CONNECTION TABLE", fontsize=12.5,
            fontweight="bold", va="top")
    ax.text(4, H - 11, "Tick each row as you wire it. Build one component at a "
                       "time and verify it with the serial console before the next.",
            fontsize=8.4, va="top", color="#55555f")

    cols = [8, 30, 92, 142, 202, 236]
    hdr = ["", "COMPONENT", "PIN (as printed)", "CONNECTS TO", "WIRE", "NOTE"]
    ytop, dy = 144, 4.72
    ax.add_patch(Rectangle((6, ytop - 1.8), 304, 6.4, fc="#e9edf2", ec="#7a8899",
                           lw=1.0, zorder=3))
    for cx, hname in zip(cols, hdr):
        ax.text(cx, ytop + 1.4, hname, fontsize=8.0, fontweight="bold",
                va="center", zorder=5)
    y = ytop - 5.2
    for i, (comp, p, to, col, note) in enumerate(ROWS):
        if comp and i:
            ax.plot([6, 310], [y + dy / 2, y + dy / 2], color="#c9d1d9", lw=0.8,
                    zorder=3)
        ax.add_patch(Rectangle((cols[0], y - 1.3), 2.6, 2.6, fc="white",
                               ec="#55555f", lw=0.9, zorder=4))
        if comp:
            ax.text(cols[1], y, comp, fontsize=7.6, va="center",
                    fontweight="bold", zorder=5)
        ax.text(cols[2], y, p, fontsize=7.6, va="center", zorder=5)
        ax.text(cols[3], y, to, fontsize=7.6, va="center", zorder=5)
        ax.text(cols[4], y, col, fontsize=7.4, va="center", zorder=5,
                color="#33333c")
        hot = any(k in note for k in ("mandatory", "NEVER", "printed"))
        ax.text(cols[5], y, note, fontsize=7.2, va="center", zorder=5,
                color="#a02020" if hot else "#55555f")
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
