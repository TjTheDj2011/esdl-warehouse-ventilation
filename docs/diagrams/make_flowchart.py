#!/usr/bin/env python3
"""Generate the ESDL Project 1 engineering diagram set as a single PDF.

Regenerate after any design change:
    python3 docs/diagrams/make_flowchart.py
Output: docs/04_engineering_diagrams.pdf
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, FancyArrowPatch, Rectangle
from matplotlib.backends.backend_pdf import PdfPages

# ---- palette ---------------------------------------------------------------
SENSOR = "#cfe3f7"
MCU    = "#e8e8ea"
DRIVER = "#fde2c4"
ALARM  = "#f8cfcf"
STATE  = "#d6efd6"
DECIDE = "#fdf3c8"
POWER  = "#ded5f0"
EDGE   = "#3c3c46"
TXT    = "#1c1c22"

FIGSIZE = (11.0, 8.5)


def new_page(title, subtitle=""):
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    ax.text(50, 96.5, title, ha="center", va="center",
            fontsize=17, fontweight="bold", color=TXT)
    if subtitle:
        ax.text(50, 92.4, subtitle, ha="center", va="center",
                fontsize=9.5, color="#55555f")
    return fig, ax


def box(ax, cx, cy, w, h, text, fc=MCU, fs=8.5, bold=False, ec=EDGE):
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                                boxstyle="round,pad=0.35,rounding_size=0.8",
                                fc=fc, ec=ec, lw=1.3, zorder=2))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, color=TXT,
            fontweight="bold" if bold else "normal", zorder=3, linespacing=1.45)


def diamond(ax, cx, cy, w, h, text, fs=8.0):
    ax.add_patch(Polygon([(cx, cy + h / 2), (cx + w / 2, cy),
                          (cx, cy - h / 2), (cx - w / 2, cy)],
                         fc=DECIDE, ec=EDGE, lw=1.3, zorder=2))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, color=TXT,
            zorder=3, linespacing=1.4)


def arrow(ax, p1, p2, label="", fs=7.5, style="-|>", color=EDGE,
          lx=0, ly=1.6, ls="-", rad=0.0):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=13,
                                 lw=1.2, color=color, zorder=1,
                                 linestyle=ls,
                                 connectionstyle=f"arc3,rad={rad}"))
    if label:
        mx, my = (p1[0] + p2[0]) / 2 + lx, (p1[1] + p2[1]) / 2 + ly
        ax.text(mx, my, label, ha="center", va="center", fontsize=fs,
                color="#33333c",
                bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.2), zorder=4)


def footer(ax, text):
    ax.text(50, 2.2, text, ha="center", va="center", fontsize=7.4,
            color="#6a6a74", style="italic")


# ============================================================ page 1
def page_block_diagram(pdf):
    fig, ax = new_page(
        "System Block Diagram",
        "ESDL Project 1 \u2014 Automated Warehouse Ventilation Controller | "
        "ESP32-WROOM-32 | 3x SSD1306 OLED, 3.3 V native throughout")

    box(ax, 44, 62, 26, 17,
        "ESP32-WROOM-32\n\n3.3 V logic\nmillis() cooperative scheduler\nno delay() in loop()",
        fc=MCU, fs=9, bold=False)

    # sensors
    box(ax, 11, 72, 19, 9, "DS18B20  #1\nchamber / inside", fc=SENSOR)
    box(ax, 11, 56, 19, 9, "DS18B20  #2\nambient / outside", fc=SENSOR)
    arrow(ax, (20.5, 72), (31, 66), "GPIO 4   1-wire + 4.7k", ly=1.8)
    arrow(ax, (20.5, 56), (31, 59), "GPIO 16  1-wire + 4.7k", ly=-2.0)

    # three OLED panels on two I2C buses - no level shifter anywhere
    box(ax, 76, 87, 15, 6, "OLED  IN\n0x3C", fc=DRIVER, fs=7.6)
    box(ax, 76, 79.5, 15, 6, "OLED  OUT\n0x3D", fc=DRIVER, fs=7.6)
    box(ax, 76, 72, 15, 6, "OLED  STATE\n0x3C", fc=DRIVER, fs=7.6)
    arrow(ax, (57, 70), (68.5, 85))
    arrow(ax, (57, 67), (68.5, 72))
    ax.text(63.5, 80.5, "GPIO 21/22\nI2C bus 0", ha="center", va="center",
            fontsize=7.4, color="#33333c", linespacing=1.5,
            bbox=dict(fc="white", ec="none", alpha=0.9, pad=1.0))
    ax.text(62.5, 73.5, "GPIO 17/18\nI2C bus 1", ha="center", va="center",
            fontsize=7.4, color="#33333c", linespacing=1.5,
            bbox=dict(fc="white", ec="none", alpha=0.9, pad=1.0))

    # motor driver + fans
    box(ax, 74, 60, 17, 12, "DRV8833\ndual H-bridge\n3.3 V logic", fc=DRIVER)
    arrow(ax, (57, 62), (65.5, 61), "GPIO 25/26  intake\nGPIO 27/14  exhaust\nGPIO 13  nSLEEP",
          ly=3.4)
    box(ax, 90, 66, 15, 7.5, "Intake fan\n80mm 5V", fc=DRIVER)
    box(ax, 90, 54, 15, 7.5, "Exhaust fan\n80mm 5V", fc=DRIVER)
    arrow(ax, (82.5, 62), (83.2, 65))
    arrow(ax, (82.5, 58), (83.2, 55))

    # buzzer
    box(ax, 74, 44, 17, 7.5, "Buzzer module\n(onboard NPN)", fc=ALARM)
    arrow(ax, (55, 55), (65.5, 45), "GPIO 23", ly=-2.4, lx=3)

    # power
    box(ax, 22, 26, 24, 9, "USB 5 V\nlogic + programming", fc=POWER)
    box(ax, 62, 26, 26, 9, "5 V 2 A supply\nFANS ONLY", fc=POWER, bold=True)
    arrow(ax, (22, 30.5), (38, 53.5))
    arrow(ax, (66, 30.5), (72, 54))
    ax.add_patch(Rectangle((14, 12), 72, 7.5, fc="#fff3f3", ec="#c0392b",
                           lw=1.4, zorder=2))
    ax.text(50, 15.7,
            "COMMON GROUND REQUIRED  —  supply negative ties to ESP32 GND, or the "
            "H-bridge sees no valid logic level",
            ha="center", va="center", fontsize=8.6, color="#a02020",
            fontweight="bold", zorder=3)

    ax.text(50, 36.5,
            "Fan power is never drawn from USB: both fans start together and their "
            "inrush would exceed a USB port.\n"
            "NO LEVEL SHIFTER ANYWHERE — every peripheral is 3.3 V native, which is "
            "why the OLED panels were chosen over a 5 V LCD.",
            ha="center", va="center", fontsize=8, color="#55555f", linespacing=1.6)

    footer(ax, "Pin assignments are authoritative in hardware/01_pinout.md")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


# ============================================================ page 2
def page_control_flow(pdf):
    fig, ax = new_page(
        "Control Logic Flowchart",
        "One pass per control tick (2.5 s). Governing rule: move air only when the "
        "air pulled in is cooler than the air pushed out.")

    xd, xs = 41, 82          # decision column, state column
    box(ax, xd, 87, 30, 7, "CONTROL TICK   (every 2.5 s)", fc="#ffffff", bold=True, fs=9)
    box(ax, xd, 77.5, 30, 7, "Read T_in and T_out  (DS18B20 x2)", fc=SENSOR, fs=8.5)
    arrow(ax, (xd, 83.5), (xd, 81))

    ys = [67, 54, 41, 28]
    diamond(ax, xd, ys[0], 30, 11, "Both readings valid?\n(-127 C = no probe)")
    diamond(ax, xd, ys[1], 30, 11, "T_in above 80.0 F ?\n(releases at 77.0 F)")
    diamond(ax, xd, ys[2], 30, 11, "Outside 3.0 F HOTTER\nthan inside ?")
    diamond(ax, xd, ys[3], 30, 11, "Outside 2.0 F COOLER\nthan inside ?")
    arrow(ax, (xd, 74), (xd, 72.5))
    for a, b in zip(ys, ys[1:]):
        arrow(ax, (xd, a - 5.5), (xd, b + 5.5), "yes" if a == ys[0] else "no",
              lx=2.6, ly=0)

    box(ax, xs, ys[0], 27, 9.5,
        "FAULT\nintake off · exhaust ON\nbuzzer 4 Hz pattern", fc=ALARM, fs=8, bold=True)
    box(ax, xs, ys[1], 27, 9.5,
        "STANDBY\nboth fans stopped\nbuzzer off", fc=STATE, fs=8, bold=True)
    box(ax, xs, ys[2], 27, 9.5,
        "SEALED\nboth fans stopped\nbuzzer steady", fc=STATE, fs=8, bold=True)
    box(ax, xs, ys[3], 27, 9.5,
        "CROSS_VENT\nintake ON · exhaust ON\nbuzzer off", fc=STATE, fs=8, bold=True)
    box(ax, xs, 15, 27, 9.5,
        "EXHAUST_ONLY\nintake off · exhaust ON\nbuzzer steady", fc=STATE, fs=8, bold=True)

    arrow(ax, (xd + 15, ys[0]), (xs - 13.5, ys[0]), "no,  3 in a row", ly=1.9)
    arrow(ax, (xd + 15, ys[1]), (xs - 13.5, ys[1]), "no", ly=1.9)
    arrow(ax, (xd + 15, ys[2]), (xs - 13.5, ys[2]), "yes", ly=1.9)
    arrow(ax, (xd + 15, ys[3]), (xs - 13.5, ys[3]), "yes", ly=1.9)
    arrow(ax, (xd, ys[3] - 5.5), (xd, 15), "no", lx=2.6, ly=0)
    arrow(ax, (xd + 15, 15), (xs - 13.5, 15))

    ax.add_patch(Rectangle((8, 3.8), 84, 6.6, fc="#f4f7fb", ec="#7a8899",
                           lw=1.1, zorder=2))
    ax.text(50, 7.1,
            "Every transition is additionally gated by a 10 s MINIMUM DWELL.   "
            "FAULT preempts dwell — it is a safety event.\n"
            "SEALED cannot deadlock: internal heat raises T_in until it passes "
            "T_out, which releases the seal and resumes ventilation.",
            ha="center", va="center", fontsize=8.2, color="#33333c",
            linespacing=1.6, zorder=3)
    footer(ax, "Asserted by test/test_control_host.cpp — 48 checks, sections [13]-[17]")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


# ============================================================ page 3
def page_bands(pdf):
    fig, ax = new_page(
        "Decision Bands and Hysteresis",
        "Why the controller does not chatter: every boundary engages and releases "
        "at different values.")

    # --- chamber temperature axis
    ax.text(50, 84, "Chamber temperature  T_in", ha="center", fontsize=11,
            fontweight="bold", color=TXT)
    y = 72
    ax.add_patch(Rectangle((10, y), 33, 7, fc=STATE, ec=EDGE, lw=1.2))
    ax.add_patch(Rectangle((43, y), 17, 7, fc=DECIDE, ec=EDGE, lw=1.2))
    ax.add_patch(Rectangle((60, y), 30, 7, fc=DRIVER, ec=EDGE, lw=1.2))
    ax.text(26.5, y + 3.5, "STANDBY\nfans idle", ha="center", va="center", fontsize=8.5)
    ax.text(51.5, y + 3.5, "LATCHED\nholds previous", ha="center", va="center", fontsize=8.5)
    ax.text(75, y + 3.5, "ACTIVE\nventilation states", ha="center", va="center", fontsize=8.5)
    for x, lab in ((43, "77.0 F\nrelease"), (60, "80.0 F\nengage")):
        ax.plot([x, x], [y - 3, y + 7], color="#c0392b", lw=1.6, ls="--")
        ax.text(x, y - 6, lab, ha="center", va="center", fontsize=8,
                color="#a02020", fontweight="bold")
    ax.text(50, y - 11.5,
            "3 F of hysteresis. A bare threshold would chatter the fans on sensor noise.",
            ha="center", fontsize=8.2, color="#55555f")

    # --- differential axis
    ax.text(50, 50, "Temperature difference   D  =  T_in - T_out",
            ha="center", fontsize=11, fontweight="bold", color=TXT)
    y2 = 38
    ax.add_patch(Rectangle((10, y2), 24, 7, fc=STATE, ec=EDGE, lw=1.2))
    ax.add_patch(Rectangle((34, y2), 33, 7, fc=DRIVER, ec=EDGE, lw=1.2))
    ax.add_patch(Rectangle((67, y2), 23, 7, fc=STATE, ec=EDGE, lw=1.2))
    ax.text(22, y2 + 3.5, "SEALED\nno exchange", ha="center", va="center", fontsize=8.5)
    ax.text(50.5, y2 + 3.5, "EXHAUST_ONLY\nboth fans blow out", ha="center",
            va="center", fontsize=8.5)
    ax.text(78.5, y2 + 3.5, "CROSS_VENT\ndirected jet", ha="center", va="center", fontsize=8.5)
    ax.text(10, y2 + 10.5, "outside HOTTER", ha="left", fontsize=8.5,
            color="#a02020", fontweight="bold")
    ax.text(90, y2 + 10.5, "outside COOLER", ha="right", fontsize=8.5,
            color="#1d6b1d", fontweight="bold")
    for x, lab in ((34, "-3.0 F seal\n-1.5 F release"), (67, "+2.0 F open\n+1.0 F release")):
        ax.plot([x, x], [y2 - 3, y2 + 7], color="#c0392b", lw=1.6, ls="--")
        ax.text(x, y2 - 6.5, lab, ha="center", va="center", fontsize=8,
                color="#a02020", fontweight="bold")

    ax.add_patch(Rectangle((8, 8), 84, 16, fc="#f4f7fb", ec="#7a8899", lw=1.1))
    ax.text(50, 20.4, "Why these numbers", ha="center", fontsize=9.5,
            fontweight="bold", color=TXT)
    ax.text(50, 14.0,
            "Each DS18B20 is accurate to +/-0.5 C, so the difference D carries about "
            "+/-1.0 C (+/-1.8 F) of uncertainty.\n"
            "Both differential thresholds sit outside that band, so the controller "
            "never acts on sensor noise — only on a real difference.\n"
            "The seal threshold of 3.0 F is reasoned, NOT yet measured. Determine it "
            "on the bench and update this figure.",
            ha="center", va="center", fontsize=8.2, color="#33333c", linespacing=1.7)
    footer(ax, "Thresholds defined in firmware/src/control.cpp :: default_vent_config()")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


# ============================================================ page 4
def page_airflow(pdf):
    fig, ax = new_page(
        "Enclosure Airflow by State",
        "Transparent box, diagonal wind tunnel. Intake LOW on one wall, exhaust "
        "HIGH on the opposite wall - working with buoyancy, not against it.")

    def chamber(x0, y0, w, h, title, sub, intake, exhaust, flow, note):
        ax.add_patch(Rectangle((x0, y0), w, h, fc="#f7fbff", ec=EDGE, lw=1.8))
        ax.text(x0 + w / 2, y0 + h + 6.2, title, ha="center", fontsize=10.5,
                fontweight="bold", color=TXT)
        ax.text(x0 + w / 2, y0 + h + 2.6, sub, ha="center", fontsize=7.8,
                color="#55555f")
        ax.add_patch(Rectangle((x0 + w - 5.5, y0 + h - 5), 5.5, 5,
                               fc=DRIVER, ec=EDGE, lw=1.1))
        ax.add_patch(Rectangle((x0, y0 + 2), 5.5, 5, fc=DRIVER, ec=EDGE, lw=1.1))
        ax.text(x0 + w - 2.7, y0 + h - 2.5, "EX", ha="center", va="center", fontsize=6.5)
        ax.text(x0 + 2.7, y0 + 4.5, "IN", ha="center", va="center", fontsize=6.5)
        for (p1, p2) in flow:
            ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>",
                                         mutation_scale=11, lw=1.9,
                                         color="#1f6fb2",
                                         connectionstyle="arc3,rad=0.15"))
        ax.text(x0 + w / 2, y0 - 3.4,
                f"intake {intake}   \u00b7   exhaust {exhaust}", ha="center",
                fontsize=8.2, fontweight="bold", color=TXT)
        ax.text(x0 + w / 2, y0 - 7.6, note, ha="center", fontsize=7.4,
                color="#55555f", linespacing=1.5, va="top")

    TOP_Y, BOT_Y, H = 61, 19, 21

    chamber(8, TOP_Y, 34, H, "CROSS_VENT", "outside is at least 2 F cooler",
            "ON", "ON",
            [((13, TOP_Y + 4), (36, TOP_Y + H - 4))],
            "Low in, high out - works with buoyancy.\nDirected diagonal sweep.")

    chamber(58, TOP_Y, 34, H, "EXHAUST_ONLY", "inside and outside within ~3 F",
            "OFF", "ON",
            [((61, TOP_Y + 4), (72, TOP_Y + 10)),
             ((72, TOP_Y + 12), (88, TOP_Y + H - 4))],
            "Exhaust alone. Makeup air is drawn IN\nthrough the idle intake fan, low down.")

    chamber(8, BOT_Y, 34, H, "SEALED", "outside is at least 3 F HOTTER",
            "OFF", "OFF", [],
            "No forced exchange - moving air would\nimport heat. Idle fans leak slowly.")

    chamber(58, BOT_Y, 34, H, "STANDBY", "chamber below 77 F",
            "OFF", "OFF", [],
            "Nothing to do. Chamber is already\nbelow setpoint.")

    ax.add_patch(Rectangle((10, 0.4), 80, 5.0, fc="#f4f7fb", ec="#7a8899", lw=1.0))
    ax.text(50, 2.9,
            "FAULT commands the same airflow as EXHAUST_ONLY with a distinct 4 Hz "
            "buzzer pattern \u2014 bounded near ambient beats an unbounded heat soak.",
            ha="center", va="center", fontsize=7.8, color="#33333c")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.normpath(os.path.join(here, "..", "04_engineering_diagrams.pdf"))
    with PdfPages(out) as pdf:
        page_block_diagram(pdf)
        page_control_flow(pdf)
        page_bands(pdf)
        page_airflow(pdf)
        d = pdf.infodict()
        d["Title"] = "ESDL Project 1 - Engineering Diagrams"
        d["Subject"] = "Automated Warehouse Ventilation System"
    print("wrote", out)


if __name__ == "__main__":
    main()
