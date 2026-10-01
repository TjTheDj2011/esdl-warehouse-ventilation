#!/usr/bin/env python3
"""Slide renders of the circuit schematic.

The same drawing as docs/05_schematic.pdf, cropped to the circuit itself - no
title block, sheet heading or footnotes - and rendered at a fixed scale with
no letterboxing. Drawing coordinates therefore map linearly onto image pixels,
which is what lets the slides place highlight boxes over exact regions.

Regenerate:  python3 docs/diagrams/make_slide_figures.py
Output:      docs/slides/schematic-sheet1.png, docs/slides/schematic-sheet2.png
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import matplotlib
matplotlib.use("Agg")
import make_schematic as ms  # noqa: E402

ms.title_block = lambda *a, **k: None   # the slide has its own heading
SCALE = 16.5 / 262                      # inches per drawing unit, as in the PDF
DPI = 200
# (x0, x1, y0, y1) in drawing units: the circuit and nothing else.
CROPS = {1: (1, 258, 23, 129), 2: (26, 252, 20, 131)}


class Capture:
    """Stands in for PdfPages: re-frames the finished sheet and saves a PNG."""

    def __init__(self, sheet, out):
        self.sheet, self.out = sheet, out

    def savefig(self, fig, **_):
        ax = fig.axes[0]
        top = ax.get_ylim()[1]
        for t in list(ax.texts):        # drop sheet heading and footnotes
            y = t.get_position()[1]
            if y < 20 or y > top - 6:
                t.remove()
        x0, x1, y0, y1 = CROPS[self.sheet]
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect("auto")           # figure is sized to the crop: no stretch
        fig.set_size_inches((x1 - x0) * SCALE, (y1 - y0) * SCALE)
        fig.subplots_adjust(0, 0, 1, 1)
        fig.savefig(self.out, dpi=DPI, facecolor="white")


def main():
    out = os.path.normpath(os.path.join(HERE, "..", "slides"))
    os.makedirs(out, exist_ok=True)
    for n, fn in ((1, ms.sheet1), (2, ms.sheet2)):
        path = os.path.join(out, f"schematic-sheet{n}.png")
        fn(Capture(n, path))
        print("wrote", path)


if __name__ == "__main__":
    main()
