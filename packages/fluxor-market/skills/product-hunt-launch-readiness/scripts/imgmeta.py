#!/usr/bin/env python3
"""Dependency-free image metadata (format, width, height, animated, bytes).

Reads only the header bytes it needs, so it works on PNG, JPEG, GIF, WebP,
ICO, AVIF/HEIC and SVG without Pillow. Used by the other audit scripts, and
usable on its own:

    python3 imgmeta.py path/to/logo.png another.jpg
"""
from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path


def _png(data: bytes):
    if len(data) < 24 or data[12:16] != b"IHDR":
        return None
    w, h = struct.unpack(">II", data[16:24])
    return {"format": "png", "width": w, "height": h, "animated": b"acTL" in data[:4096]}


def _gif(data: bytes):
    if len(data) < 10:
        return None
    w, h = struct.unpack("<HH", data[6:10])
    # More than one Graphic Control Extension almost always means animation.
    return {"format": "gif", "width": w, "height": h, "animated": data.count(b"\x21\xf9\x04") > 1}


def _jpeg(data: bytes):
    i, n = 2, len(data)
    while i + 9 < n:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        if i + 4 > n:
            break
        seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return {"format": "jpeg", "width": w, "height": h, "animated": False}
        i += 2 + seg_len
    return {"format": "jpeg", "width": None, "height": None, "animated": False}


def _webp(data: bytes):
    chunk = data[12:16]
    if chunk == b"VP8 " and len(data) >= 30:
        w, h = struct.unpack("<HH", data[26:30])
        return {"format": "webp", "width": w & 0x3FFF, "height": h & 0x3FFF, "animated": False}
    if chunk == b"VP8L" and len(data) >= 25:
        b = data[21:25]
        w = 1 + (((b[1] & 0x3F) << 8) | b[0])
        h = 1 + (((b[3] & 0xF) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
        return {"format": "webp", "width": w, "height": h, "animated": False}
    if chunk == b"VP8X" and len(data) >= 30:
        animated = bool(data[20] & 0x02)
        w = 1 + int.from_bytes(data[24:27], "little")
        h = 1 + int.from_bytes(data[27:30], "little")
        return {"format": "webp", "width": w, "height": h, "animated": animated}
    return {"format": "webp", "width": None, "height": None, "animated": False}


def _ico(data: bytes):
    if len(data) < 6:
        return None
    count = struct.unpack("<H", data[4:6])[0]
    best = (0, 0)
    sizes = []
    for k in range(min(count, 64)):
        off = 6 + 16 * k
        if off + 16 > len(data):
            break
        w = data[off] or 256
        h = data[off + 1] or 256
        sizes.append(f"{w}x{h}")
        if w * h > best[0] * best[1]:
            best = (w, h)
    # PNG-compressed entries can be larger than 256; the directory caps at 256.
    return {"format": "ico", "width": best[0] or None, "height": best[1] or None,
            "animated": False, "sizes": sizes}


def _isobmff(data: bytes):
    brand = data[8:12].decode("latin-1", "replace")
    idx = data.find(b"ispe")
    if idx != -1 and idx + 16 <= len(data):
        w, h = struct.unpack(">II", data[idx + 8:idx + 16])
        return {"format": brand.strip() or "avif", "width": w, "height": h, "animated": False}
    return {"format": brand.strip() or "avif", "width": None, "height": None, "animated": False}


_SVG_NUM = re.compile(r"^\s*([0-9.]+)\s*(px)?\s*$")


def _svg(text: str):
    m = re.search(r"<svg\b[^>]*>", text, re.I | re.S)
    if not m:
        return None
    tag = m.group(0)

    def attr(name):
        a = re.search(r'\b%s\s*=\s*["\']([^"\']+)["\']' % name, tag, re.I)
        return a.group(1) if a else None

    w, h = attr("width"), attr("height")
    width = height = None
    if w and h and _SVG_NUM.match(w) and _SVG_NUM.match(h):
        width, height = float(_SVG_NUM.match(w).group(1)), float(_SVG_NUM.match(h).group(1))
    vb = attr("viewBox")
    if (width is None or height is None) and vb:
        parts = re.split(r"[\s,]+", vb.strip())
        if len(parts) == 4:
            try:
                width, height = float(parts[2]), float(parts[3])
            except ValueError:
                pass
    return {"format": "svg", "width": int(width) if width else None,
            "height": int(height) if height else None, "animated": "<animate" in text,
            "vector": True}


def image_info_from_bytes(data: bytes, total_bytes: int | None = None) -> dict | None:
    """Return metadata for the image in `data` (the first ~64 KB is enough)."""
    info = None
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        info = _png(data)
    elif data[:6] in (b"GIF87a", b"GIF89a"):
        info = _gif(data)
    elif data[:3] == b"\xff\xd8\xff":
        info = _jpeg(data)
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        info = _webp(data)
    elif data[:4] == b"\x00\x00\x01\x00":
        info = _ico(data)
    elif data[4:8] == b"ftyp":
        info = _isobmff(data)
    else:
        head = data[:4096].decode("utf-8", "ignore")
        if "<svg" in head.lower():
            info = _svg(data.decode("utf-8", "ignore"))
    if info is not None:
        info["bytes"] = total_bytes if total_bytes is not None else len(data)
        w, h = info.get("width"), info.get("height")
        info["aspect"] = round(w / h, 3) if w and h else None
    return info


def image_info(path: str | Path) -> dict | None:
    p = Path(path)
    try:
        size = p.stat().st_size
        with p.open("rb") as fh:
            data = fh.read(262144)
    except OSError:
        return None
    return image_info_from_bytes(data, size)


if __name__ == "__main__":
    out = {}
    for arg in sys.argv[1:]:
        out[arg] = image_info(arg)
    print(json.dumps(out, indent=2))
