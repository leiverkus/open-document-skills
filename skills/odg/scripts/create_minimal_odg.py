#!/usr/bin/env python3
"""Create a minimal ODG drawing from a JSON specification."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from odg_common import ODG_MIMETYPE, ensure_manifest_entry, media_type_for, pack_dir_as_odg, q, unique_picture_name


def add_text(page: ET.Element, item: dict[str, object]) -> None:
    frame = ET.SubElement(page, q("draw", "frame"), {q("draw", "name"): str(item.get("name", "Text")), q("svg", "x"): str(item.get("x", "1cm")), q("svg", "y"): str(item.get("y", "1cm")), q("svg", "width"): str(item.get("width", "8cm")), q("svg", "height"): str(item.get("height", "2cm"))})
    box = ET.SubElement(frame, q("draw", "text-box"))
    p = ET.SubElement(box, q("text", "p"))
    p.text = str(item.get("text", ""))


def add_shape(page: ET.Element, item: dict[str, object]) -> None:
    shape_type = str(item.get("type", "rect"))
    if shape_type not in {"rect", "ellipse", "line", "connector"}:
        raise SystemExit(f"Unsupported shape type: {shape_type}")
    attrs = {q("draw", "name"): str(item.get("name", shape_type))}
    if shape_type in {"line", "connector"}:
        for key, default in [("x1", "1cm"), ("y1", "1cm"), ("x2", "5cm"), ("y2", "1cm")]:
            attrs[q("svg", key)] = str(item.get(key, default))
    else:
        for key, default in [("x", "1cm"), ("y", "1cm"), ("width", "4cm"), ("height", "2cm")]:
            attrs[q("svg", key)] = str(item.get(key, default))
    shape = ET.SubElement(page, q("draw", shape_type), attrs)
    text = item.get("text")
    if text:
        p = ET.SubElement(shape, q("text", "p"))
        p.text = str(text)


def add_image(page: ET.Element, item: dict[str, object], root_dir: Path, manifest_entries: list[tuple[str, str]], existing: set[str]) -> None:
    source = Path(str(item["path"]))
    package_path = unique_picture_name(existing, source)
    existing.add(package_path)
    target = root_dir / package_path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    manifest_entries.append((package_path, media_type_for(source)))
    frame = ET.SubElement(page, q("draw", "frame"), {q("draw", "name"): str(item.get("name", "Image")), q("svg", "x"): str(item.get("x", "1cm")), q("svg", "y"): str(item.get("y", "1cm")), q("svg", "width"): str(item.get("width", "6cm")), q("svg", "height"): str(item.get("height", "4cm"))})
    ET.SubElement(frame, q("draw", "image"), {q("xlink", "href"): package_path, q("xlink", "type"): "simple", q("xlink", "show"): "embed", q("xlink", "actuate"): "onLoad"})


def build_styles() -> ET.Element:
    root = ET.Element(q("office", "document-styles"), {q("office", "version"): "1.3"})
    styles = ET.SubElement(root, q("office", "styles"))
    ET.SubElement(styles, q("style", "style"), {q("style", "name"): "DefaultGraphic", q("style", "family"): "graphic"})
    automatic = ET.SubElement(root, q("office", "automatic-styles"))
    layout = ET.SubElement(automatic, q("style", "page-layout"), {q("style", "name"): "Screen"})
    ET.SubElement(layout, q("style", "page-layout-properties"), {q("fo", "page-width"): "28cm", q("fo", "page-height"): "15.75cm", q("style", "print-orientation"): "landscape"})
    masters = ET.SubElement(root, q("office", "master-styles"))
    ET.SubElement(masters, q("style", "master-page"), {q("style", "name"): "Default", q("style", "page-layout-name"): "Screen"})
    return root


def simple_doc(root_name: str) -> ET.Element:
    return ET.Element(q("office", root_name), {q("office", "version"): "1.3"})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("output_odg", type=Path)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    with tempfile.TemporaryDirectory() as tmp:
        root_dir = Path(tmp)
        (root_dir / "META-INF").mkdir()
        (root_dir / "Pictures").mkdir()
        (root_dir / "mimetype").write_text(ODG_MIMETYPE)
        content = ET.Element(q("office", "document-content"), {q("office", "version"): "1.3"})
        body = ET.SubElement(content, q("office", "body"))
        drawing = ET.SubElement(body, q("office", "drawing"))
        manifest_entries = [("content.xml", "text/xml"), ("styles.xml", "text/xml"), ("meta.xml", "text/xml"), ("settings.xml", "text/xml")]
        existing_media: set[str] = set()
        for idx, page_spec in enumerate(spec.get("pages", []), start=1):
            page = ET.SubElement(drawing, q("draw", "page"), {q("draw", "name"): page_spec.get("name", f"Page {idx}"), q("draw", "master-page-name"): "Default"})
            for item in page_spec.get("items", []):
                kind = item.get("type", "text")
                if kind == "text":
                    add_text(page, item)
                elif kind in {"rect", "ellipse", "line", "connector"}:
                    add_shape(page, item)
                elif kind == "image":
                    add_image(page, item, root_dir, manifest_entries, existing_media)
                else:
                    raise SystemExit(f"Unknown item type: {kind}")
        if not list(drawing):
            ET.SubElement(drawing, q("draw", "page"), {q("draw", "name"): "Page 1", q("draw", "master-page-name"): "Default"})
        meta = simple_doc("document-meta")
        meta_body = ET.SubElement(meta, q("office", "meta"))
        created = ET.SubElement(meta_body, q("meta", "creation-date"))
        created.text = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        settings = simple_doc("document-settings")
        ET.SubElement(settings, q("office", "settings"))
        manifest = ET.Element(q("manifest", "manifest"), {q("manifest", "version"): "1.3"})
        ensure_manifest_entry(manifest, "/", ODG_MIMETYPE)
        for full_path, media_type in manifest_entries:
            ensure_manifest_entry(manifest, full_path, media_type)
        ET.ElementTree(content).write(root_dir / "content.xml", encoding="utf-8", xml_declaration=True)
        ET.ElementTree(build_styles()).write(root_dir / "styles.xml", encoding="utf-8", xml_declaration=True)
        ET.ElementTree(meta).write(root_dir / "meta.xml", encoding="utf-8", xml_declaration=True)
        ET.ElementTree(settings).write(root_dir / "settings.xml", encoding="utf-8", xml_declaration=True)
        ET.ElementTree(manifest).write(root_dir / "META-INF" / "manifest.xml", encoding="utf-8", xml_declaration=True)
        pack_dir_as_odg(root_dir, args.output_odg)
    print(args.output_odg)


if __name__ == "__main__":
    main()
