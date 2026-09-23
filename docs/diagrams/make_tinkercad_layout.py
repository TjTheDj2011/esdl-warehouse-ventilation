#!/usr/bin/env python3
"""ESDL Project 1 - Tinkercad Circuits canvas render (2 sheets).

Drawn to match what you actually see in Tinkercad: real breadboard, Arduino
Uno, components as objects, curved jumper wires.

Regenerate:  python3 docs/diagrams/make_tinkercad_layout.py
Output:      docs/08_tinkercad_layout.pdf
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import (FancyBboxPatch, Rectangle, Circle, Polygon,
                                FancyArrowPatch, Wedge)
from matplotlib.backends.backend_pdf import PdfPages

BG      = "#f4f4f6"
UNO_T   = "#01979d"
UNO_D   = "#017c81"
BB_BODY = "#eceadf"
BB_HOLE = "#3c3c42"
BLK     = "#1d1d22"
GOLD    = "#c9a227"
SIL     = "#b6bac0"
TXT     = "#1d1d22"

# jumper colours
RED, BLK_W, ORG, BLU, GRN, YEL, PUR, WHT = ("#d62828", "#242429", "#e07b19",
                                            "#2176d2", "#2e9e4f", "#d9b310",
                                            "#8e44ad", "#dfe2e6")
PITCH = 4.2
DATE, REV = "2026-09-16", "A"


def page(w=372, h=222):
    fig, ax = plt.subplots(figsize=(16.8, 9.8))
    ax.set_xlim(0, w); ax.set_ylim(0, h); ax.axis("off"); ax.set_aspect("equal")
    ax.add_patch(Rectangle((0, 0), w, h, fc=BG, ec="none", zorder=0))
    return fig, ax


def shadow(ax, x0, y0, x1, y1, r=2.0):
    ax.add_patch(FancyBboxPatch((x0 + 1.4, y0 - 1.6), x1 - x0, y1 - y0,
                                boxstyle=f"round,pad=0.3,rounding_size={r}",
                                fc="#00000018", ec="none", zorder=1))


def jump(ax, p0, p1, color, arc=0.22, lw=3.0, z=20):
    """Tinkercad-style jumper: thick, rounded, gently curved."""
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-", mutation_scale=1,
                                 connectionstyle=f"arc3,rad={arc}",
                                 lw=lw + 1.2, color="#00000022", zorder=z - 1,
                                 capstyle="round"))
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-", mutation_scale=1,
                                 connectionstyle=f"arc3,rad={arc}",
                                 lw=lw, color=color, zorder=z,
                                 capstyle="round"))


# ------------------------------------------------------------- breadboard
ROWS = {"j": 56, "i": 52, "h": 48, "g": 44, "f": 40,
        "e": 26, "d": 22, "c": 18, "b": 14, "a": 10}
RAILS = {"+t": 68, "-t": 64, "+b": 2, "-b": -2}


def breadboard(ax, x0, y0, ncols=40, label="BREADBOARD"):
    w = 12 + ncols * PITCH
    shadow(ax, x0, y0 - 8, x0 + w, y0 + 74)
    ax.add_patch(FancyBboxPatch((x0, y0 - 8), w, 82,
                                boxstyle="round,pad=0.4,rounding_size=2.0",
                                fc=BB_BODY, ec="#c9c5b6", lw=1.2, zorder=2))
    # centre channel
    ax.add_patch(Rectangle((x0 + 3, y0 + 30), w - 6, 8, fc="#dedad0",
                           ec="#c9c5b6", lw=0.8, zorder=3))
    # rail stripes
    for key, col in (("+t", "#c0392b"), ("-t", "#2e5fa3"),
                     ("+b", "#c0392b"), ("-b", "#2e5fa3")):
        y = y0 + RAILS[key]
        ax.plot([x0 + 5, x0 + w - 5], [y + 2.6, y + 2.6], color=col, lw=1.1,
                zorder=3)
        ax.text(x0 + 2.4, y, "+" if key.startswith("+") else "−",
                ha="center", va="center", fontsize=6.5, color=col,
                fontweight="bold", zorder=4)

    def hx(c):
        return x0 + 8 + c * PITCH

    for c in range(ncols):
        for r in ROWS.values():
            ax.add_patch(Rectangle((hx(c) - 0.75, y0 + r - 0.75), 1.5, 1.5,
                                   fc=BB_HOLE, ec="none", zorder=4))
        if c % 2 == 0:
            for k in RAILS.values():
                ax.add_patch(Rectangle((hx(c) - 0.75, y0 + k - 0.75), 1.5, 1.5,
                                       fc=BB_HOLE, ec="none", zorder=4))
    ax.text(x0 + w / 2, y0 - 12.5, label, ha="center", fontsize=7.0,
            color="#7a7a84")

    def hole(col, row):
        return (hx(col), y0 + (ROWS[row] if row in ROWS else RAILS[row]))
    return hole


# ----------------------------------------------------------- arduino uno
def uno(ax, x0, y0, w=152, h=58):
    shadow(ax, x0, y0, x0 + w, y0 + h, r=3)
    ax.add_patch(FancyBboxPatch((x0, y0), w, h,
                                boxstyle="round,pad=0.4,rounding_size=3",
                                fc=UNO_T, ec=UNO_D, lw=1.4, zorder=3))
    # USB-B and barrel jack on the left edge
    ax.add_patch(Rectangle((x0 - 7, y0 + h - 22), 10, 15, fc=SIL,
                           ec="#8b8f95", lw=1.0, zorder=4))
    ax.add_patch(Rectangle((x0 - 6, y0 + 6), 9, 12, fc="#17171b",
                           ec="#0c0c10", lw=1.0, zorder=4))
    # MCU + reset
    ax.add_patch(Rectangle((x0 + w * 0.42, y0 + 20), 30, 12, fc="#17171b",
                           ec="#0c0c10", lw=0.9, zorder=4))
    ax.add_patch(Circle((x0 + 12, y0 + h - 8), 2.6, fc="#c0392b",
                        ec="#8e2a20", lw=0.8, zorder=4))
    ax.text(x0 + w * 0.60, y0 + 14, "ARDUINO", fontsize=8.6, color="white",
            fontweight="bold", zorder=5, style="italic")
    ax.text(x0 + w * 0.60, y0 + 7, "UNO  R3", fontsize=7.0, color="#bfe9ec",
            zorder=5)

    dig = ["AREF", "GND", "13", "12", "~11", "~10", "~9", "8",
           "7", "~6", "~5", "4", "~3", "2", "TX", "RX"]
    ana = ["IOREF", "RST", "3V3", "5V", "GND", "GND", "VIN",
           "A0", "A1", "A2", "A3", "A4", "A5"]
    D, A = {}, {}
    hy = y0 + h - 4
    ax.add_patch(Rectangle((x0 + 20, hy - 3), len(dig) * 5.6 + 3, 6.4,
                           fc=BLK, ec="#0c0c10", lw=0.8, zorder=4))
    for i, n in enumerate(dig):
        x = x0 + 23 + i * 5.6
        ax.add_patch(Rectangle((x - 1.1, hy - 1.1), 2.2, 2.2, fc=GOLD,
                               ec="none", zorder=5))
        ax.text(x, hy + 5.4, n, ha="center", va="bottom", fontsize=4.6,
                color="white", rotation=90, zorder=6)
        D[n.lstrip("~")] = (x, hy)
    ly = y0 + 4
    ax.add_patch(Rectangle((x0 + 20, ly - 3.2), len(ana) * 5.6 + 3, 6.4,
                           fc=BLK, ec="#0c0c10", lw=0.8, zorder=4))
    for i, n in enumerate(ana):
        x = x0 + 23 + i * 5.6
        ax.add_patch(Rectangle((x - 1.1, ly - 1.1), 2.2, 2.2, fc=GOLD,
                               ec="none", zorder=5))
        ax.text(x, ly - 5.2, n, ha="center", va="top", fontsize=4.6,
                color="white", rotation=90, zorder=6)
        A[n] = (x, ly)
    return D, A


# ------------------------------------------------------------- components
def tmp36(ax, cx, ybase, caption):
    """TO-92 body sitting above three breadboard holes."""
    ax.add_patch(Wedge((cx, ybase + 13), 8.5, 0, 180, fc="#26262c",
                       ec="#0c0c10", lw=1.0, zorder=12))
    ax.add_patch(Rectangle((cx - 8.5, ybase + 8), 17, 5, fc="#26262c",
                           ec="#0c0c10", lw=1.0, zorder=12))
    ax.text(cx, ybase + 14.5, "TMP36", ha="center", va="center", fontsize=5.2,
            color="#d8d8de", zorder=13)
    for dx in (-PITCH, 0, PITCH):
        ax.plot([cx + dx, cx + dx], [ybase + 8, ybase], color="#9aa0a6",
                lw=1.4, zorder=11)
    ax.text(cx, ybase + 36, caption, ha="center", fontsize=6.6,
            fontweight="bold", color=TXT)


def dip16(ax, x0, ycentre, label="L293D"):
    """DIP-16 straddling the breadboard centre channel."""
    w, h = 7 * PITCH + 4, 8
    ax.add_patch(FancyBboxPatch((x0, ycentre - h / 2), w, h,
                                boxstyle="round,pad=0.3,rounding_size=1.0",
                                fc="#232329", ec="#0c0c10", lw=1.1, zorder=12))
    ax.add_patch(Wedge((x0 + 2.0, ycentre), 1.8, 90, 270, fc="#3a3a42",
                       ec="none", zorder=13))
    ax.text(x0 + w / 2, ycentre, label, ha="center", va="center", fontsize=6.4,
            color="#e3e3e8", fontweight="bold", zorder=26)
    top, bot = {}, {}
    for i in range(8):
        x = x0 + 4 + i * PITCH
        ax.plot([x, x], [ycentre + h / 2, ycentre + h / 2 + 3], color=SIL,
                lw=1.5, zorder=11)
        ax.plot([x, x], [ycentre - h / 2, ycentre - h / 2 - 3], color=SIL,
                lw=1.5, zorder=11)
        bot[i + 1] = (x, ycentre - h / 2 - 3)       # pins 1-8
        top[16 - i] = (x, ycentre + h / 2 + 3)      # pins 16-9
    return bot, top


def lcd(ax, x0, y0, w=150, h=46):
    shadow(ax, x0, y0, x0 + w, y0 + h)
    ax.add_patch(FancyBboxPatch((x0, y0), w, h,
                                boxstyle="round,pad=0.4,rounding_size=2",
                                fc="#1f6b52", ec="#14493a", lw=1.3, zorder=3))
    ax.add_patch(Rectangle((x0 + 14, y0 + 13), w - 28, 24, fc="#39b27a",
                           ec="#14493a", lw=1.0, zorder=4))
    ax.text(x0 + w / 2, y0 + 25, "16 x 2  LCD", ha="center", va="center",
            fontsize=8.0, color="#0d3a2c", fontweight="bold", zorder=5)
    names = ["VSS", "VDD", "V0", "RS", "RW", "E", "D0", "D1", "D2", "D3",
             "D4", "D5", "D6", "D7", "A", "K"]
    P = {}
    ax.add_patch(Rectangle((x0 + 8, y0 + 2), 16 * 5.4 + 2, 5.5, fc=BLK,
                           ec="#0c0c10", lw=0.8, zorder=4))
    for i, n in enumerate(names):
        x = x0 + 11 + i * 5.4
        ax.add_patch(Rectangle((x - 1.1, y0 + 3.6 - 1.1), 2.2, 2.2, fc=GOLD,
                               ec="none", zorder=5))
        ax.text(x, y0 + 8.4, n, ha="center", va="bottom", fontsize=4.4,
                color="white", rotation=90, zorder=6)
        P[n] = (x, y0 + 3.6)
    return P


def pot(ax, cx, ybase):
    ax.add_patch(Circle((cx, ybase + 12), 8.5, fc="#2b4a9e", ec="#1b2f66",
                        lw=1.1, zorder=12))
    ax.add_patch(Rectangle((cx - 1.2, ybase + 12), 2.4, 8, fc="#d8d8de",
                           ec="none", zorder=13))
    for dx in (-PITCH, 0, PITCH):
        ax.plot([cx + dx, cx + dx], [ybase + 6, ybase], color="#9aa0a6",
                lw=1.4, zorder=11)
    ax.text(cx, ybase + 36, "10k POT", ha="center", fontsize=6.6,
            fontweight="bold", color=TXT)



def piezo(ax, cx, cy):
    ax.add_patch(Circle((cx, cy), 12, fc="#1d1d22", ec="#0c0c10", lw=1.2, zorder=12))
    ax.add_patch(Circle((cx, cy), 6.5, fc="#b6bac0", ec="none", zorder=13))
    ax.text(cx, cy + 16, "PIEZO", ha="center", fontsize=6.8, fontweight="bold")
    return (cx - 3, cy - 12), (cx + 3, cy - 12)


def resistor_span(ax, pl, pr, text="220"):
    """Axial resistor with legs in two different breadboard columns."""
    cy = pl[1] + 9
    for p in (pl, pr):
        ax.plot([p[0], p[0]], [p[1], cy], color="#9aa0a6", lw=1.4, zorder=11)
    ax.plot([pl[0], pr[0]], [cy, cy], color="#9aa0a6", lw=1.4, zorder=11)
    cx = (pl[0] + pr[0]) / 2
    ax.add_patch(Rectangle((cx - 7, cy - 2.4), 14, 4.8, fc="#d8c39b",
                           ec="#8a7350", lw=0.9, zorder=12))
    for i, c in enumerate(("#8a4b2a", "#c0392b", "#2b2b30")):
        ax.add_patch(Rectangle((cx - 4.5 + i * 3, cy - 2.4), 1.6, 4.8, fc=c,
                               ec="none", zorder=13))
    ax.text(cx, cy + 6, text, ha="center", fontsize=5.6, color="#5a5a64")


def resistor(ax, cx, cy, text="220"):
    ax.add_patch(Rectangle((cx - 7, cy - 2.4), 14, 4.8, fc="#d8c39b",
                           ec="#8a7350", lw=0.9, zorder=12))
    for i, c in enumerate(("#8a4b2a", "#c0392b", "#2b2b30")):
        ax.add_patch(Rectangle((cx - 4.5 + i * 3, cy - 2.4), 1.6, 4.8, fc=c,
                               ec="none", zorder=13))
    ax.text(cx, cy + 5, text, ha="center", fontsize=5.6, color="#5a5a64")


def motor(ax, cx, cy, caption):
    shadow(ax, cx - 13, cy - 11, cx + 13, cy + 11)
    ax.add_patch(FancyBboxPatch((cx - 13, cy - 11), 26, 22,
                                boxstyle="round,pad=0.3,rounding_size=4",
                                fc="#9aa0a6", ec="#5d6268", lw=1.2, zorder=12))
    ax.add_patch(Circle((cx, cy), 6.5, fc="#c3c7cc", ec="#5d6268", lw=0.9, zorder=13))
    ax.add_patch(Rectangle((cx + 13, cy - 1.4), 7, 2.8, fc="#7d8288",
                           ec="#5d6268", lw=0.8, zorder=12))
    ax.text(cx, cy + 15, caption, ha="center", fontsize=6.8, fontweight="bold")
    return (cx - 6, cy - 11), (cx + 6, cy - 11)


def battery9v(ax, x0, y0):
    shadow(ax, x0, y0, x0 + 40, y0 + 26)
    ax.add_patch(FancyBboxPatch((x0, y0), 40, 26,
                                boxstyle="round,pad=0.3,rounding_size=2",
                                fc="#3a3a42", ec="#1d1d22", lw=1.2, zorder=12))
    ax.text(x0 + 20, y0 + 16, "9 V", ha="center", fontsize=9.0, color="white",
            fontweight="bold", zorder=13)
    ax.text(x0 + 20, y0 + 7, "MOTOR SUPPLY", ha="center", fontsize=5.4,
            color="#c3c7cc", zorder=13)
    return (x0 + 12, y0), (x0 + 28, y0)


def callout(ax, x, y, w, lines, title, col="#c0392b"):
    h = 7 + 4.6 * len(lines)
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.4,rounding_size=1.6",
                                fc="white", ec=col, lw=1.3, zorder=30))
    ax.text(x + w / 2, y + h - 4, title, ha="center", va="center", fontsize=7.6,
            fontweight="bold", color=col, zorder=31)
    for i, ln in enumerate(lines):
        ax.text(x + 3, y + h - 10 - i * 4.6, ln, ha="left", va="center",
                fontsize=6.4, color="#33333c", zorder=31)


def title_block(ax, W, sheet, total, subtitle):
    bw, bh = 86, 20
    x0, y0 = W - bw - 3, 3
    ax.add_patch(Rectangle((x0, y0), bw, bh, fc="white", ec=TXT, lw=1.4, zorder=30))
    ax.plot([x0, x0 + bw], [y0 + bh - 8, y0 + bh - 8], color=TXT, lw=1.0, zorder=31)
    ax.plot([x0, x0 + bw], [y0 + 7, y0 + 7], color=TXT, lw=1.0, zorder=31)
    ax.text(x0 + bw / 2, y0 + bh - 4, "ESDL PROJECT 1 - TINKERCAD CIRCUITS",
            ha="center", va="center", fontsize=7.6, fontweight="bold", zorder=31)
    ax.text(x0 + bw / 2, y0 + 10.6, subtitle, ha="center", va="center",
            fontsize=7.4, zorder=31)
    ax.text(x0 + 3, y0 + 3.4, f"TJ / Tabitha    {DATE}    REV {REV}    "
            f"SH {sheet}/{total}", ha="left", va="center", fontsize=6.4, zorder=31)


# ==================================================================== sheet 1
def sheet1(pdf):
    W, H = 372, 222
    fig, ax = page(W, H)
    ax.text(5, H - 4, "TINKERCAD CIRCUITS  -  sensors, display and alarm",
            fontsize=11.8, fontweight="bold", va="top", color=TXT)

    D, A = uno(ax, 18, 14)
    hole = breadboard(ax, 18, 96, ncols=44)
    P = lcd(ax, 232, 150, w=132, h=44)

    tmp36(ax, hole(3, "f")[0], hole(3, "f")[1], "#1 CHAMBER")
    tmp36(ax, hole(9, "f")[0], hole(9, "f")[1], "#2 AMBIENT")
    pot(ax, hole(16, "f")[0], hole(16, "f")[1])

    jump(ax, A["5V"], hole(0, "+t"), RED, arc=-0.32)
    jump(ax, A["GND"], hole(1, "-t"), BLK_W, arc=-0.30)

    jump(ax, hole(2, "j"), hole(2, "+t"), RED, arc=0.0, lw=2.4)
    jump(ax, hole(4, "j"), hole(4, "-t"), BLK_W, arc=0.0, lw=2.4)
    jump(ax, hole(3, "a"), A["A0"], BLU, arc=0.22)
    jump(ax, hole(8, "j"), hole(8, "+t"), RED, arc=0.0, lw=2.4)
    jump(ax, hole(10, "j"), hole(10, "-t"), BLK_W, arc=0.0, lw=2.4)
    jump(ax, hole(9, "a"), A["A1"], BLU, arc=0.26)
    jump(ax, hole(15, "j"), hole(15, "-t"), BLK_W, arc=0.0, lw=2.4)
    jump(ax, hole(17, "j"), hole(17, "+t"), RED, arc=0.0, lw=2.4)
    jump(ax, hole(16, "a"), P["V0"], ORG, arc=-0.18)

    jump(ax, P["VSS"], hole(30, "-t"), BLK_W, arc=0.22)
    jump(ax, P["VDD"], hole(31, "+t"), RED, arc=0.22)
    jump(ax, P["RW"], hole(33, "-t"), BLK_W, arc=0.24)
    jump(ax, P["K"], hole(43, "-t"), BLK_W, arc=-0.18)
    resistor_span(ax, hole(39, "j"), hole(42, "j"))
    jump(ax, P["A"], hole(39, "i"), RED, arc=-0.20, lw=2.4)
    jump(ax, hole(42, "i"), hole(42, "+t"), RED, arc=0.0, lw=2.4)

    for lcd_pin, uno_pin, arc in (("RS", "12", 0.16), ("E", "11", 0.18),
                                  ("D4", "5", 0.20), ("D5", "4", 0.22),
                                  ("D6", "3", 0.24), ("D7", "2", 0.26)):
        jump(ax, P[lcd_pin], D[uno_pin], PUR, arc=arc, lw=2.4)

    pp, pn = piezo(ax, 300, 108)
    jump(ax, pp, D["10"], ORG, arc=0.26)
    jump(ax, pn, hole(43, "+b"), BLK_W, arc=-0.3)

    callout(ax, 232, 46, 134, [
        "LCD data pins cross over:",
        "LCD D4 -> Uno 5,   D5 -> Uno 4,",
        "D6 -> Uno 3,   D7 -> Uno 2.",
        "TMP36 flat face forward:",
        "left +5 V, middle signal, right GND.",
        "No 10k pot on V0 = blank screen."],
        "WIRE IT EXACTLY LIKE THIS")
    title_block(ax, W, 1, 2, "Sensors, Display, Alarm")
    pdf.savefig(fig, bbox_inches="tight"); plt.close(fig)


# ==================================================================== sheet 2
def sheet2(pdf):
    W, H = 372, 222
    fig, ax = page(W, H)
    ax.text(5, H - 4, "TINKERCAD CIRCUITS  -  motor drive",
            fontsize=11.8, fontweight="bold", va="top", color=TXT)

    D, A = uno(ax, 18, 140)
    hole = breadboard(ax, 18, 52, ncols=44)

    ycentre = (hole(0, "e")[1] + hole(0, "f")[1]) / 2
    bot, top = dip16(ax, hole(8, "e")[0] - 4, ycentre)

    m1a, m1b = motor(ax, 300, 128, "M1  INTAKE")
    m2a, m2b = motor(ax, 300, 74, "M2  EXHAUST")
    bp, bn = battery9v(ax, 196, 6)

    jump(ax, A["5V"], hole(0, "+t"), RED, arc=0.30)
    jump(ax, A["GND"], hole(1, "-t"), BLK_W, arc=0.28)

    jump(ax, D["6"], hole(9, "j"), PUR, arc=0.20, lw=2.4)
    jump(ax, D["7"], hole(14, "j"), PUR, arc=0.18, lw=2.4)
    jump(ax, D["8"], hole(19, "j"), PUR, arc=0.16, lw=2.4)
    jump(ax, D["9"], hole(23, "j"), PUR, arc=0.14, lw=2.4)
    jump(ax, hole(19, "a"), hole(14, "a"), PUR, arc=-0.4, lw=2.2)
    jump(ax, hole(23, "a"), hole(9, "a"), PUR, arc=-0.35, lw=2.2)

    jump(ax, hole(8, "j"), hole(8, "+t"), RED, arc=0.0, lw=2.4)
    jump(ax, hole(15, "j"), hole(15, "+t"), RED, arc=0.0, lw=2.4)
    jump(ax, hole(8, "a"), hole(8, "+b"), RED, arc=0.0, lw=2.4)
    for c in (11, 12):
        jump(ax, hole(c, "a"), hole(c, "-b"), BLK_W, arc=0.0, lw=2.4)
        jump(ax, hole(c, "j"), hole(c, "-t"), BLK_W, arc=0.0, lw=2.4)
    jump(ax, hole(2, "+b"), hole(2, "+t"), RED, arc=-0.5, lw=2.2)
    jump(ax, hole(4, "-b"), hole(4, "-t"), BLK_W, arc=-0.5, lw=2.2)

    jump(ax, bp, hole(15, "a"), RED, arc=-0.22)
    jump(ax, bn, hole(26, "-b"), BLK_W, arc=0.18)
    jump(ax, hole(10, "a"), m1a, GRN, arc=-0.26)
    jump(ax, hole(13, "a"), m1b, GRN, arc=-0.32)
    jump(ax, hole(13, "j"), m2a, YEL, arc=0.26)
    jump(ax, hole(10, "j"), m2b, YEL, arc=0.32)

    callout(ax, 6, 6, 152, [
        "L293D pin 1 at the notch, bottom-left. It must",
        "straddle the centre channel.",
        "Uno 6 -> IN1 (pin 2)      Uno 7 -> IN2 (pin 7)",
        "Uno 8 -> IN3 (pin 10)    Uno 9 -> IN4 (pin 15)",
        "EN1,2 / EN3,4 / VCC1 -> +5 V.  VCC2 -> 9 V.",
        "Battery - and Uno GND share the same rail."],
        "MOTOR DRIVE NOTES")
    title_block(ax, W, 2, 2, "Motor Drive")
    pdf.savefig(fig, bbox_inches="tight"); plt.close(fig)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.normpath(os.path.join(here, "..", "08_tinkercad_layout.pdf"))
    with PdfPages(out) as pdf:
        sheet1(pdf); sheet2(pdf)
        pdf.infodict()["Title"] = "ESDL Project 1 - Tinkercad Circuits"
    print("wrote", out)


if __name__ == "__main__":
    main()
