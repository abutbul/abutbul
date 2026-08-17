"""Validate generated artifacts (no deps, run after generate.py)."""
import os
import re
import sys
import xml.etree.ElementTree as ET

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ok = True
    svg_path = os.path.join(BASE, "assets", "session.svg")
    try:
        ET.parse(svg_path)
        print("OK   session.svg is well-formed XML")
    except Exception as exc:
        print("FAIL session.svg: %s" % exc)
        ok = False

    readme_path = os.path.join(BASE, "README.md")
    readme = open(readme_path).read().lower()
    for bad in ("<script", "<style", "style=", "onclick", "javascript:"):
        if bad in readme:
            print("FAIL README contains forbidden token: %s" % bad)
            ok = False
    print("OK   README has no script/style/inline-style")

    svg = open(svg_path).read()
    bad_amp = re.findall(r"&(?!(amp|lt|gt|quot|apos);)", svg)
    if bad_amp:
        print("FAIL session.svg has %d unescaped ampersands" % len(bad_amp))
        ok = False
    else:
        print("OK   session.svg ampersands are escaped")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
