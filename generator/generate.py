"""Generate the BBS-style README, its SVG screens and a local preview.

Everything is derived from data/profile.json:

  assets/logon.svg            the logon screen (logo, neofetch, stats)
  assets/menu-<key>.svg       one clickable menu bar per menu entry
  assets/screen-*.svg         the screen each menu bar opens
  assets/proj-*.svg           one clickable row per project
  assets/contact-*.svg        one clickable row per contact
  assets/prompt.svg           the command prompt under the menu
  README.md                   the page that wires them together
  preview/index.html          the same markup for a local look

The screens are static: nothing plays on its own. Interaction comes from
what GitHub allows in a README, which is <details> (menu bars that open a
screen, one at a time) and links (project and contact rows).

Usage:  python3 generator/generate.py
Stdlib only.
"""

import json
import os
import re
import sys
import textwrap
import urllib.request

from ansi import PALETTE, FONT_FAMILY, figlet, split_runs, xesc, truncate

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE, "data", "profile.json")
ASSETS = os.path.join(BASE, "assets")
PREVIEW = os.path.join(BASE, "preview")
CACHE_PATH = os.path.join(BASE, "data", ".stats-cache.json")

FONT_SIZE = 13
LINE_H = 20
BASELINE = 14
FW = FONT_SIZE * 0.6
WIDTH = 800
MARGIN_X = 16
COLS = int((WIDTH - 2 * MARGIN_X) / FW)
PAD = 12

# Menu bars sit next to the <details> disclosure triangle, so they are a
# little narrower than the screens to stay on the same line as it.
BAR_WIDTH = "92%"
MENU_GROUP = "bbs"

NL = chr(10)


def fmt(x):
    if isinstance(x, int):
        return str(x)
    s = ("%.1f" % x).rstrip("0").rstrip(".")
    return s if s else "0"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-") or "x"


def wrap(text, first, rest, cols=COLS):
    """Word-wrap ``text`` to the screen width with hanging indentation."""
    return textwrap.wrap(str(text), width=cols, initial_indent=first,
                         subsequent_indent=rest, break_long_words=False) or [first]


def pad_between(left, right, cols=COLS):
    """Spaces that push ``right`` to the last column after ``left``."""
    return " " * max(1, cols - left - right)


# --------------------------------------------------------------------------- #
# SVG screen builder
# --------------------------------------------------------------------------- #
class Screen:
    """A block of terminal rows rendered as one static SVG."""

    def __init__(self, pad_top=PAD, pad_bottom=PAD):
        self.pad_top = pad_top
        self.pad_bottom = pad_bottom
        self.row = 0
        self.under = []
        self.parts = []

    def _y(self):
        return self.pad_top + self.row * LINE_H + BASELINE

    def line(self, segments, x=MARGIN_X, center=False, advance=True):
        anchor = ' text-anchor="middle"' if center else ''
        spans = []
        for seg in segments:
            txt, col = seg[0], seg[1]
            fill = PALETTE.get(col, PALETTE["white"])
            inner = xesc(txt)
            if len(seg) > 2 and seg[2] == "blink":
                inner += ('<animate attributeName="fill-opacity" values="1;1;0;0" '
                          'keyTimes="0;0.5;0.5;1" dur="1.1s" repeatCount="indefinite"/>')
            spans.append('<tspan fill="' + fill + '">' + inner + '</tspan>')
        self.parts.append('<text x="' + fmt(WIDTH / 2 if center else x) + '" y="'
                          + fmt(self._y()) + '"' + anchor + ' xml:space="preserve">'
                          + "".join(spans) + '</text>')
        if advance:
            self.row += 1
        return self

    def text(self, s, color="white", **kw):
        return self.line([(s, color)], **kw)

    def center(self, s, color="white"):
        return self.line([(s, color)], center=True)

    def blank(self, n=1):
        self.row += n
        return self

    def rule(self, color="dgray", ch="─"):
        return self.text(ch * COLS, color=color)

    def title(self, label, hint=""):
        left = "[" + label.upper() + "]"
        segs = [(left, "yellow")]
        if hint:
            segs.append((pad_between(len(left), len(hint)) + hint, "dgray"))
        self.line(segs)
        return self.rule()

    def footer(self, s):
        self.rule()
        return self.text(s, color="dgray")

    def hotkey(self, key):
        """An inverse-video key cap at the start of the current row."""
        y = self.pad_top + self.row * LINE_H - 2
        self.under.append('<rect x="' + fmt(MARGIN_X) + '" y="' + fmt(y) + '" width="'
                          + fmt(FW * 3) + '" height="' + fmt(LINE_H + 2) + '" fill="'
                          + PALETTE["bcyan"] + '"/>')
        return self.line([(" " + key + " ", "black")], advance=False)

    def height(self):
        return self.pad_top + self.row * LINE_H + self.pad_bottom

    def svg(self, frame=False):
        h = self.height()
        out = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<svg xmlns="http://www.w3.org/2000/svg" width="' + str(WIDTH)
               + '" height="' + str(h) + '" viewBox="0 0 ' + str(WIDTH) + ' ' + str(h)
               + '" font-family="' + FONT_FAMILY + '" font-size="' + str(FONT_SIZE) + '">',
               '<style>text,tspan{white-space:pre}</style>',
               '<rect width="' + str(WIDTH) + '" height="' + str(h) + '" fill="#000000"/>']
        if frame:
            out.append('<rect x="0.5" y="0.5" width="' + fmt(WIDTH - 1) + '" height="'
                       + fmt(h - 1) + '" fill="none" stroke="' + PALETTE["dgray"]
                       + '" stroke-width="1"/>')
        out.extend(self.under)
        out.extend(self.parts)
        out.append('</svg>')
        return NL.join(out) + NL


# --------------------------------------------------------------------------- #
# Screens
# --------------------------------------------------------------------------- #
def _monitor_art(handle):
    name = (handle + "-bbs v1.2")[:16].ljust(16)
    who = handle[:9]
    return [
        "   ╔══════════════════╗",
        "   ║ " + name + " ║",
        "   ║ ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄ ║",
        "   ║ " + ("login: " + who).ljust(16) + " ║",
        "   ║ pass : ░░░░░░░░  ║",
        "   ║ $ whoami         ║",
        "   ║ " + ("> " + who).ljust(16) + " ║",
        "   ║ ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀ ║",
        "   ╚══════════════════╝",
        "     ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄",
    ]


def _art_color(ch):
    if ch in "╔═╗╚╝║":
        return "lgray"
    if ch in "▄▀█":
        return "bcyan"
    if ch in "░▒▓":
        return "dgray"
    return "bgreen"


def _colorize_art(rows):
    out = []
    for r in rows:
        segs = []
        for ch in r:
            col = _art_color(ch)
            if segs and segs[-1][1] == col:
                segs[-1][0] += ch
            else:
                segs.append([ch, col])
        out.append(segs)
    return out


def _info_line(key, value, maxlen, val_color="white"):
    dots = "·" * (maxlen - len(key) + 3)
    return [(key, "bcyan"), (":", "dgray"), (" " + dots + " ", "dgray"),
            (value, val_color)]


def menu_keys(data):
    return ",".join(m["key"] for m in data["menu"])


def screen_logon(data, stats):
    handle = data["handle"]
    spaced = " ".join(handle.upper())
    s = Screen(pad_top=PAD + 8)
    s.center("(c) 1992 " + handle.upper() + " SYSTEMS  ·  ANSI/VT100 16-COLOR", "lgray")
    s.blank()
    colors = ["bred", "yellow", "bgreen", "bcyan", "bblue", "bmagenta"]
    for i, row in enumerate(figlet("ANSI Shadow.flf", handle)):
        col = colors[i % len(colors)]
        s.line([(t, "dgray" if shadow else col) for t, shadow in split_runs(row)],
               center=True)
    s.blank()
    s.center("▄▄▄▄  T H E   " + spaced + "   B B S  ▄▄▄▄", "bcyan")
    s.center(data["name"] + "  ·  " + data.get("title", ""), "lgray")
    s.blank()

    connect = "CONNECT 57600 8N1  ·  ANSI detected"
    online = "● ONLINE"
    s.line([(connect, "green"),
            (pad_between(len(connect), len(online)), "black"),
            (online, "bgreen")])
    s.line([("LOGIN   ", "lgray"), (handle, "bcyan")])
    s.line([("PASSWD  ", "lgray"), ("●" * 9, "dgray")])
    s.text("* ACCESS GRANTED *", color="bred")
    s.blank()

    s.center("═" * 30 + " NEOFETCH " + "═" * 30, "yellow")
    s.blank()
    top = s.row
    for segs in _colorize_art(_monitor_art(handle)):
        s.line(segs)
    art_bottom = s.row
    info_x = MARGIN_X + 24 * FW + 24
    nf = data["neofetch"]
    s.row = top
    s.line([(handle, "bcyan"), ("@", "dgray"), (nf.get("host", "bbs"), "bcyan")], x=info_x)
    s.line([("─" * 28, "dgray")], x=info_x)
    keys = [k for k in nf if k != "host"]
    maxlen = max(len(k) for k in keys)
    for k in keys:
        s.line(_info_line(k, nf[k], maxlen), x=info_x)
    if stats:
        s.blank()
        s.line([("GitHub Stats", "bred")], x=info_x)
        s.line([("─" * 28, "dgray")], x=info_x)
        labels = [("repos", "Repos"), ("followers", "Followers"),
                  ("following", "Following"), ("stars", "Stars")]
        smax = max(len(lb) for _, lb in labels)
        for key, label in labels:
            val = stats.get(key)
            s.line(_info_line(label, str(val) if val is not None else "—", smax, "yellow"),
                   x=info_x)
    s.row = max(s.row, art_bottom)
    s.blank()

    s.center("═" * 14 + " MAIN MENU " + "═" * 14, "yellow")
    s.center("pick a key below  ·  click a bar to open it, click again to close", "dgray")
    return s


def screen_bar(item):
    key, label, hint = item["key"], item["label"], item.get("hint", "")
    s = Screen(pad_top=7, pad_bottom=7)
    s.hotkey(key)
    lead = 5
    dots = "·" * max(3, COLS - lead - len(label) - len(hint) - 2)
    s.line([(label, "white"), (" " + dots + " ", "dgray"), (hint, "lgray")],
           x=MARGIN_X + lead * FW)
    return s


def screen_prompt(data):
    s = Screen(pad_top=8, pad_bottom=8)
    s.line([("Command [" + menu_keys(data) + "] > ", "bred"), ("█", "bgreen", "blink")])
    return s


def screen_about(data):
    s = Screen()
    s.title("About")
    for line in data.get("about", []):
        for part in wrap(line, "  ", "  "):
            s.text(part, color="lgray")
    s.blank()
    s.footer("end of screen  ·  pick another key from the menu")
    return s


def screen_work(data):
    s = Screen()
    s.title("Work Experience")
    for w in data.get("work", []):
        role, period = w.get("role", ""), w.get("period", "")
        head = [("▸ ", "bred"), (role, "bcyan")]
        if period:
            head.append((pad_between(2 + len(role), len(period)) + period, "dgray"))
        s.line(head)
        if w.get("org"):
            s.text("   " + w["org"], color="white")
        for bl in w.get("bullets", []):
            for part in wrap(bl, "   - ", "     "):
                s.text(part, color="lgray")
        s.blank()
    s.footer("end of screen  ·  pick another key from the menu")
    return s


def screen_skills(data):
    s = Screen()
    s.title("Skills")
    for group, items in data.get("skills", {}).items():
        s.line([("▸ ", "bred"), (group, "bred"), (":", "dgray"),
                ("  " + " · ".join(items), "white")])
    s.blank()
    s.footer("end of screen  ·  pick another key from the menu")
    return s


def screen_list_head(label, hint):
    s = Screen(pad_bottom=0)
    s.title(label, hint)
    s.blank()
    return s


def screen_list_tail(text):
    s = Screen(pad_top=0)
    s.footer(text)
    return s


def screen_group(label):
    s = Screen(pad_top=0, pad_bottom=0)
    s.line([("── ", "dgray"), (label, "yellow"),
            (" " + "─" * max(3, COLS - len(label) - 4), "dgray")])
    s.blank()
    return s


def _open_tag(left_len):
    tag = "→ open"
    return (pad_between(left_len, len(tag)) + tag, "dgray")


def screen_project(p):
    s = Screen(pad_top=0, pad_bottom=0)
    head = [("▸ ", "bred"), (p["name"], "bcyan"),
            ("  ★ " + str(p.get("stars", 0)), "yellow"),
            ("  " + " · ".join(p.get("tags", [])), "dgray")]
    head.append(_open_tag(sum(len(t) for t, _ in head)))
    s.line(head)
    s.text("   " + truncate(p.get("desc", ""), COLS - 4), color="lgray")
    s.text("   ↳ " + truncate(p.get("url", ""), COLS - 6), color="dgray")
    s.blank()
    return s


def screen_contact(c, maxlen):
    s = Screen(pad_top=0, pad_bottom=0)
    dots = "·" * (maxlen - len(c["label"]) + 3)
    head = [("▸ ", "bred"), (c["label"], "bred"), (":", "dgray"),
            (" " + dots + " ", "dgray"), (c["value"], "bcyan")]
    head.append(_open_tag(sum(len(t) for t, _ in head)))
    s.line(head)
    s.text("   ↳ " + truncate(c.get("url", ""), COLS - 6), color="dgray")
    s.blank()
    return s


def screen_quit(data):
    s = Screen(pad_bottom=0)
    s.title("Quit")
    s.text("  logging off...", color="dgray")
    s.blank()
    s.center("G O O D B Y E  ✦", "bred")
    s.blank()
    s.text("  NO CARRIER", color="lgray")
    s.blank()
    return s


def screen_redial(url):
    s = Screen(pad_top=0, pad_bottom=0)
    head = [("▸ ", "bred"), ("redial", "bcyan"), ("  " + url, "dgray")]
    head.append(_open_tag(sum(len(t) for t, _ in head)))
    s.line(head)
    s.blank()
    return s


# --------------------------------------------------------------------------- #
# GitHub stats
# --------------------------------------------------------------------------- #
def fetch_stats(handle):
    try:
        req = urllib.request.Request(
            "https://api.github.com/users/" + handle,
            headers={"User-Agent": "abutbul-readme", "Accept": "application/vnd.github+json"})
        u = json.load(urllib.request.urlopen(req, timeout=10))
        req2 = urllib.request.Request(
            "https://api.github.com/users/" + handle + "/repos?per_page=100",
            headers={"User-Agent": "abutbul-readme"})
        repos = json.load(urllib.request.urlopen(req2, timeout=10))
        stars = sum(r.get("stargazers_count", 0) for r in repos if not r.get("fork"))
        return {"repos": u.get("public_repos"), "followers": u.get("followers"),
                "following": u.get("following"), "stars": stars}
    except Exception as exc:
        print("stats fetch failed: %s" % exc, file=sys.stderr)
        return None


def load_stats(data):
    stats = fetch_stats(data["github"]) if data.get("stats", {}).get("enable") else None
    if stats is None:
        try:
            with open(CACHE_PATH) as fh:
                stats = json.load(fh)
        except Exception:
            stats = {}
    else:
        try:
            with open(CACHE_PATH, "w") as fh:
                json.dump(stats, fh)
        except Exception:
            pass
    return stats


# --------------------------------------------------------------------------- #
# Page assembly
# --------------------------------------------------------------------------- #
class Page:
    """Collects the SVG files and the README markup that references them."""

    def __init__(self):
        self.files = {}
        self.html = []

    def asset(self, name, screen, frame=False):
        self.files[name] = screen.svg(frame=frame)
        return "assets/" + name

    @staticmethod
    def img(src, alt, width="100%"):
        return ('<img align="top" src="' + src + '" width="' + width + '" alt="'
                + xesc(alt) + '" />')

    # <picture> keeps GitHub from wrapping the image in a link to itself, so a
    # click on a menu bar toggles its <details> instead of opening the file.
    def plain(self, src, alt, width="100%"):
        return '<picture>' + self.img(src, alt, width) + '</picture>'

    def linked(self, src, alt, url):
        return '<a href="' + xesc(url) + '">' + self.img(src, alt) + '</a>'

    def add(self, *lines):
        self.html.extend(lines)

    def menu(self, item, body_lines):
        key = item["key"]
        bar = self.asset("menu-" + slug(key) + ".svg", screen_bar(item), frame=True)
        self.add('<details name="' + MENU_GROUP + '">',
                 '<summary>' + self.plain(bar, "(" + key + ") " + item["label"], BAR_WIDTH)
                 + '</summary>',
                 '<p>')
        self.add(*body_lines)
        self.add('</p>', '</details>', '')


def build_page(data, stats):
    page = Page()
    handle = data["handle"]

    logon = page.asset("logon.svg", screen_logon(data, stats))
    alt = (data["name"] + " — " + data.get("title", "") + ". The " + handle
           + " BBS logon screen. Main menu: "
           + ", ".join("(" + m["key"] + ") " + m["label"] for m in data["menu"]) + ".")
    page.add('<!-- Generated by generator/generate.py from data/profile.json. Do not edit. -->',
             '<p>' + page.plain(logon, alt) + '</p>', '')

    for item in data["menu"]:
        key = item["key"]
        if key == "A":
            src = page.asset("screen-about.svg", screen_about(data))
            body = [page.plain(src, " ".join(data.get("about", [])))]
        elif key == "P":
            projects = data.get("projects", [])
            head = page.asset("screen-projects-head.svg",
                              screen_list_head("Projects", "click a project to open its repo"))
            body = [page.plain(head, "Projects")]
            group = None
            for p in projects:
                if p.get("group") and p["group"] != group:
                    group = p["group"]
                    src = page.asset("group-" + slug(group) + ".svg", screen_group(group))
                    body.append(page.plain(src, group))
                src = page.asset("proj-" + slug(p["name"]) + ".svg", screen_project(p))
                body.append(page.linked(
                    src, p["name"] + " — " + p.get("desc", "") + " (" + str(p.get("stars", 0))
                    + " stars)", p["url"]))
            tail = page.asset("screen-projects-tail.svg", screen_list_tail(
                str(len(projects)) + " project(s) listed  ·  pick another key from the menu"))
            body.append(page.plain(tail, ""))
        elif key == "W":
            src = page.asset("screen-work.svg", screen_work(data))
            alt = "; ".join(
                ", ".join(x for x in [w.get("role", ""), w.get("org", ""), w.get("period", "")] if x)
                for w in data.get("work", []))
            body = [page.plain(src, alt)]
        elif key == "S":
            src = page.asset("screen-skills.svg", screen_skills(data))
            alt = "; ".join(g + ": " + ", ".join(items)
                            for g, items in data.get("skills", {}).items())
            body = [page.plain(src, alt)]
        elif key == "C":
            contacts = data.get("contact", [])
            head = page.asset("screen-contact-head.svg",
                              screen_list_head("Contact", "click a line to open it"))
            body = [page.plain(head, "Contact")]
            maxlen = max([len(c["label"]) for c in contacts] or [0])
            for c in contacts:
                src = page.asset("contact-" + slug(c["label"]) + ".svg",
                                 screen_contact(c, maxlen))
                body.append(page.linked(src, c["label"] + ": " + c["value"], c["url"]))
            tail = page.asset("screen-contact-tail.svg", screen_list_tail(
                "end of screen  ·  pick another key from the menu"))
            body.append(page.plain(tail, ""))
        elif key == "Q":
            url = "https://github.com/" + data["github"]
            head = page.asset("screen-quit.svg", screen_quit(data))
            redial = page.asset("screen-redial.svg", screen_redial(url.split("//")[1]))
            body = [page.plain(head, "Logging off. Goodbye. NO CARRIER."),
                    page.linked(redial, "Redial " + url, url)]
        else:
            continue
        page.menu(item, body)

    prompt = page.asset("prompt.svg", screen_prompt(data))
    page.add('<p>' + page.plain(prompt, "Command [" + menu_keys(data) + "] >") + '</p>', '')
    page.add(*plain_text_mode(data, stats))
    page.add('<p align="center"><sub>ANSI · 80s–90s BBS scene (ACiD/iCE) · generated from code — '
             '<code>generator/generate.py</code> · <code>data/profile.json</code></sub></p>', '')
    return page


def plain_text_mode(data, stats):
    """The same content as real text, for screen readers, search and small screens."""
    L = ['<details>', '<summary><sub>plain-text mode (no ANSI)</sub></summary>',
         '<h3>' + xesc(data["name"]) + '</h3>',
         '<p><i>' + xesc(data.get("title", "")) + '</i></p>',
         '<ul>']
    L.extend('<li>' + xesc(line) + '</li>' for line in data.get("about", []))
    L.append('</ul>')
    L.append('<h4>Projects</h4>')
    L.append('<ul>')
    group = None
    for p in data.get("projects", []):
        if p.get("group") and p["group"] != group:
            group = p["group"]
            if L[-1] == '<ul>':
                L.pop()
            else:
                L.append('</ul>')
            L.extend(['<p><b>' + xesc(group) + '</b></p>', '<ul>'])
        L.append('<li><a href="' + xesc(p["url"]) + '"><b>' + xesc(p["name"]) + '</b></a> — '
                 + xesc(p.get("desc", "")) + ' <sub>' + xesc(" · ".join(p.get("tags", [])))
                 + '</sub></li>')
    L.append('</ul>')
    L.append('<h4>Work Experience</h4>')
    L.append('<ul>')
    for w in data.get("work", []):
        head = '<b>' + xesc(w.get("role", "")) + '</b>'
        if w.get("org"):
            head += ' — ' + xesc(w["org"])
        if w.get("period"):
            head += ' (' + xesc(w["period"]) + ')'
        bullets = "".join('<br />– ' + xesc(bl) for bl in w.get("bullets", []))
        L.append('<li>' + head + bullets + '</li>')
    L.append('</ul>')
    L.append('<h4>Skills</h4>')
    L.append('<ul>')
    for group, items in data.get("skills", {}).items():
        L.append('<li><b>' + xesc(group) + '</b>: ' + xesc(" · ".join(items)) + '</li>')
    L.append('</ul>')
    L.append('<h4>Contact</h4>')
    L.append('<ul>')
    for c in data.get("contact", []):
        L.append('<li><b>' + xesc(c["label"]) + '</b>: <a href="' + xesc(c["url"]) + '">'
                 + xesc(c["value"]) + '</a></li>')
    L.append('</ul>')
    if stats:
        L.append('<p><sub>repos ' + str(stats.get("repos", "—"))
                 + ' · followers ' + str(stats.get("followers", "—"))
                 + ' · following ' + str(stats.get("following", "—"))
                 + ' · stars ' + str(stats.get("stars", "—")) + '</sub></p>')
    L.extend(['</details>', ''])
    return L


PREVIEW_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<base href="../">
<title>%s BBS — local preview</title>
<style>
  body { background:#0d1117; color:#c9d1d9; margin:0; padding:24px;
         font:16px/1.5 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif; }
  .markdown-body { max-width:848px; margin:0 auto; }
  .markdown-body p, .markdown-body details, .markdown-body ul { margin:0 0 16px; }
  .markdown-body img { max-width:100%%; }
  .markdown-body summary { cursor:pointer; }
  .markdown-body a { color:#58a6ff; }
  .note { max-width:848px; margin:0 auto 16px; color:#8b949e; font-size:13px; }
</style>
</head>
<body>
<p class="note">Local preview of README.md. GitHub's own styling differs slightly.</p>
<div class="markdown-body">
"""


def write_outputs(page, handle):
    os.makedirs(ASSETS, exist_ok=True)
    os.makedirs(PREVIEW, exist_ok=True)
    for stale in os.listdir(ASSETS):
        if stale.endswith(".svg") and stale not in page.files:
            os.remove(os.path.join(ASSETS, stale))
    for name, svg in page.files.items():
        with open(os.path.join(ASSETS, name), "w", encoding="utf-8") as fh:
            fh.write(svg)
    readme = NL.join(page.html)
    with open(os.path.join(BASE, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(readme)
    with open(os.path.join(PREVIEW, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(PREVIEW_HEAD % xesc(handle) + readme + "</div>" + NL + "</body>" + NL
                 + "</html>" + NL)


def main():
    with open(DATA_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    stats = load_stats(data)
    page = build_page(data, stats)
    write_outputs(page, data["handle"])
    print("wrote README.md, preview/index.html and %d SVG screens" % len(page.files))


if __name__ == "__main__":
    main()
