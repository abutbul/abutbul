"""ANSI/BBS rendering helpers: palette, escaping and FIGlet lettering.

Stdlib only. Kept deterministic so GitHub Actions can regenerate without network.
"""

import os

# IBM PC 16-color ANSI palette (the classic ACiD/ICE BBS look).
PALETTE = {
    "black":    "#000000",
    "blue":     "#0000aa",
    "green":    "#00aa00",
    "cyan":     "#00aaaa",
    "red":      "#aa0000",
    "magenta":  "#aa00aa",
    "brown":    "#aa5500",
    "lgray":    "#aaaaaa",
    "dgray":    "#555555",
    "bblue":    "#5555ff",
    "bgreen":   "#55ff55",
    "bcyan":    "#55ffff",
    "bred":     "#ff5555",
    "bmagenta": "#ff55ff",
    "yellow":   "#ffff55",
    "white":    "#ffffff",
}

FONT_FAMILY = "Consolas,'Liberation Mono','DejaVu Sans Mono',Menlo,monospace"

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")


def xesc(s):
    """XML-escape a string for use in text/attributes."""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace(chr(34), "&quot;")
        .replace(chr(39), "&apos;")
    )


# --------------------------------------------------------------------------- #
# FIGlet
# --------------------------------------------------------------------------- #
def _load_flf(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    header = lines[0].split(" ")
    if not header[0].startswith("flf2a"):
        raise ValueError("not a figlet font: " + path)
    hardblank = header[0][5]
    height = int(header[1])
    idx = 1 + int(header[5])
    chars = {}
    for code in range(32, 127):
        block = lines[idx: idx + height]
        idx += height
        # Every row ends with one or two copies of an end-mark character.
        rows = [ln.rstrip(ln[-1]) if ln else ln for ln in block]
        width = max(len(r) for r in rows)
        chars[code] = [r.ljust(width).replace(hardblank, " ") for r in rows]
    return height, chars


def figlet(font_name, text):
    """Render ``text`` in upper case with a vendored FIGlet font."""
    height, chars = _load_flf(os.path.join(FONT_DIR, font_name))
    rows = [""] * height
    for ch in text.upper():
        block = chars.get(ord(ch), chars[32])
        for i in range(height):
            rows[i] += block[i]
    rows = [r.rstrip() for r in rows]
    while rows and not rows[0].strip():
        rows.pop(0)
    while rows and not rows[-1].strip():
        rows.pop()
    return rows
