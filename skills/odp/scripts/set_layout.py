#!/usr/bin/env python3
"""Set the slide layout and/or master page on one or more ODP slides.

Reassigns ``presentation:presentation-page-layout-name`` (and optionally
``draw:master-page-name``) on the target ``draw:page`` elements, and
repositions existing placeholder frames to the zones of the new layout.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

from odp_common import (
    find_slides,
    parse_xml_from_zip,
    q,
    select_slide,
    update_meta_for_edit,
    write_odp_with_replacements,
    xml_bytes,
)
from odp_layouts import LAYOUT_STYLE_NAMES, LAYOUTS, build_presentation_page_layout


def ensure_layout_style(styles_root: ET.Element, layout_name: str) -> None:
    """Ensure styles.xml defines the style:presentation-page-layout for *layout_name*."""
    office_styles = styles_root.find(q("office", "styles"))
    if office_styles is None:
        office_styles = ET.Element(q("office", "styles"))
        styles_root.insert(0, office_styles)
    target = LAYOUT_STYLE_NAMES[layout_name]
    for ppl in office_styles.findall(q("style", "presentation-page-layout")):
        if ppl.attrib.get(q("style", "name")) == target:
            return
    office_styles.append(build_presentation_page_layout(layout_name))


def reposition_frames(slide: ET.Element, layout_name: str) -> None:
    """Move the slide's placeholder frames to the zones of the new layout.

    Frames are matched to zones by ``presentation:class``, in document order
    (so the two ``outline`` zones of ``two-content`` get the first two outline
    frames). Frames whose class has no zone in the new layout are left as-is.
    """
    zones_by_class: dict[str, list] = defaultdict(list)
    for zone in LAYOUTS[layout_name]:
        zones_by_class[zone.cls].append(zone)
    used: dict[str, int] = defaultdict(int)
    for frame in slide.findall(q("draw", "frame")):
        cls = frame.attrib.get(q("presentation", "class"))
        if cls is None:
            continue
        bucket = zones_by_class.get(cls, [])
        if used[cls] < len(bucket):
            zone = bucket[used[cls]]
            frame.set(q("svg", "x"), zone.x)
            frame.set(q("svg", "y"), zone.y)
            frame.set(q("svg", "width"), zone.width)
            frame.set(q("svg", "height"), zone.height)
            used[cls] += 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_odp", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--slide", required=True, help="slide index (1-based), draw:name, or 'all'")
    parser.add_argument("--layout", help=f"slide layout: {', '.join(sorted(LAYOUTS))}")
    parser.add_argument("--master", help="master-page name to assign")
    args = parser.parse_args()

    if not args.layout and not args.master:
        raise SystemExit("specify --layout and/or --master")
    if args.layout and args.layout not in LAYOUTS:
        raise SystemExit(f"unknown layout {args.layout!r}; choose from {sorted(LAYOUTS)}")

    content = parse_xml_from_zip(args.input_odp, "content.xml")
    styles = parse_xml_from_zip(args.input_odp, "styles.xml")

    if args.slide == "all":
        targets = find_slides(content)
    else:
        targets = [select_slide(content, args.slide)]

    if args.master:
        known = {m.attrib.get(q("style", "name")) for m in styles.iter(q("style", "master-page"))}
        if args.master not in known:
            print(f"warning: master {args.master!r} is not defined in styles.xml", file=sys.stderr)

    for slide in targets:
        if args.layout:
            slide.set(q("presentation", "presentation-page-layout-name"), LAYOUT_STYLE_NAMES[args.layout])
            reposition_frames(slide, args.layout)
        if args.master:
            slide.set(q("draw", "master-page-name"), args.master)

    replacements = {"content.xml": xml_bytes(content)}
    if args.layout:
        ensure_layout_style(styles, args.layout)
        replacements["styles.xml"] = xml_bytes(styles)

    meta = parse_xml_from_zip(args.input_odp, "meta.xml")
    update_meta_for_edit(meta)
    replacements["meta.xml"] = xml_bytes(meta)
    write_odp_with_replacements(args.input_odp, args.output, replacements)

    change = []
    if args.layout:
        change.append(f"layout {args.layout!r}")
    if args.master:
        change.append(f"master {args.master!r}")
    print(f"set {' + '.join(change)} on {len(targets)} slide(s)")


if __name__ == "__main__":
    main()
