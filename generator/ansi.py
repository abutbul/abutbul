"""ANSI/BBS rendering helpers: palette, escaping, FIGlet, small building blocks.

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


def mdesc(s):
    """Escape a string for use inside a GitHub markdown table cell."""
    return (
        str(s)
        .replace("|", "\\|")
        .replace(chr(10), " ")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def truncate(s, cols):
    s = str(s)
    if len(s) <= cols:
        return s
    return s[: cols - 1] + "…"


# --------------------------------------------------------------------------- #
# FIGlet
# --------------------------------------------------------------------------- #
def _load_flf(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    hdr = lines[0]
    if not hdr.startswith("flf2a"):
        raise ValueError("not a figlet font: " + path)
    hardblank = hdr[5]
    nums = [p for p in hdr[6:].split(" ") if p != ""]
    height = int(nums[0])
    maxlen = int(nums[2])
    commentlines = int(nums[4])
    idx = 1 + commentlines
    chars = {}
    for code in range(32, 127):
        block = lines[idx : idx + height]
        idx += height
        block = [ln.ljust(maxlen) for ln in block]
        chars[code] = block
    return height, hardblank, chars


def figlet(font_name, text, shadow="░"):
    """Render text with a vendored FIGlet font.

    ``shadow`` maps the font shadow glyph ("@" in ANSI Shadow) to a nicer
    ANSI shade character; pass None to keep it as-is.
    """
    path = os.path.join(FONT_DIR, font_name)
    height, hardblank, chars = _load_flf(path)
    text = text.upper()
    rows = [""] * height
    for ch in text:
        block = chars.get(ord(ch), chars[32])
        for i in range(height):
            rows[i] += block[i]
    out = []
    for r in rows:
        r = r.replace(hardblank, " ")
        if shadow is not None:
            r = r.replace("@", shadow)
        out.append(r.rstrip())
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return out


def split_runs(row):
    """Split a figlet row into (text, is_shadow) runs for two-tone coloring."""
    runs = []
    for ch in row:
        is_shadow = ch == "░"
        if runs and runs[-1][1] == is_shadow:
            runs[-1][0] += ch
        else:
            runs.append([ch, is_shadow])
    return runs
