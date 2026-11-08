#!/usr/bin/env python3
"""Cover for the U1 Purge Ledger forum topic: docs/cover.png, 1280x760.

Every number on the cover is read from docs/evidence (the ledger's own --json output on the
sample file, and the Dry Run timing) and checked here, so the image cannot drift from the data:

  DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run --no-project --with pillow python3 docs/cover/make_cover.py

shortcut: uses the macOS system fonts (SF Pro, SF Mono); change SANS/MONO to run elsewhere.
"""
import json
import re
import statistics
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, features

ROOT = Path(__file__).resolve().parents[2]
EV = ROOT / "docs" / "evidence"
OUT = ROOT / "docs" / "cover.png"
SANS = "/System/Library/Fonts/SFNS.ttf"
MONO = "/System/Library/Fonts/SFNSMono.ttf"

led = json.loads((EV / "helado-orca-2.4.1-ledger.json").read_text())
timing = (EV / "dryrun-2.1.0-timing.txt").read_text()


def field(key, name):
    m = re.search(r"^%s .*\b%s=(\d+)" % (key, name), timing, re.M)
    assert m, (key, name)
    return int(m.group(1))


changes = led["tool_changes"]
per_change = statistics.median(c["tower_mm3"] for c in led["changes"])
tower_g, total_g = led["tower_total_g"], round(led["tower_total_g"] + led["object_total_g"], 2)
share = led["tower_share_pct"]
sparse_g, sparse_mm3, sparse_n = led["sparse_layers_g"], led["sparse_layers_mm3"], led["sparse_layers"]
t0, t1 = field("as_sliced", "motion_s"), field("without_sparse", "motion_s")
saved = t0 - t1
assert changes == 18 and not led["purge_matrix_in_tower"]
assert abs(sparse_g / tower_g - 1 / 3) < 0.03, sparse_g / tower_g
assert 0 < saved < t0 and abs(share - 100 * tower_g / total_g) < 0.2

CARDS = [
    ("18 colour changes", "Where the tower filament goes",
     ("%.2f g of %.2f g" % (tower_g, total_g), "%.1f%% of the filament, prime tower" % share, "#58a6ff", "Tower"),
     ("%.0f mm³ per change" % per_change, "%.0f mm³ prime + walls of that layer" % led["prime_volume_mm3"], "#d29922", "On the U1")),
    ("%d layers with no change" % sparse_n, "Tower upkeep nobody needs",
     ("%.1f g" % sparse_g, "%.0f mm³, a third of the tower" % sparse_mm3, "#d29922", "Sparse layers"),
     ("%d s saved" % saved, "firmware 2.1.0: %d s → %d s" % (t0, t1), "#3fb950", "wipe_tower_no_sparse_layers = 1")),
]

S = 2  # draw at 2x, downsample once: smooth card corners and text
W, H, M = 1280, 760, 72
BG, CARD, LINE = "#0e1013", "#15181d", "#252a31"
INK, SUB, MUTED, DETAIL, FOOT = "#f2f4f7", "#a2abb6", "#8a939e", "#b9c1ca", "#7a838e"
ENGINE = ImageFont.Layout.RAQM if features.check("raqm") else ImageFont.Layout.BASIC


def sans(px, weight):
    f = ImageFont.truetype(SANS, px * S, layout_engine=ENGINE)
    # Width axis pinned at 100: the normal cut, never condensed or expanded
    axes = {b"Width": 100, b"Optical Size": min(96, max(17, px)), b"GRAD": 400, b"Weight": weight}
    f.set_variation_by_axes([axes[a["name"]] for a in f.get_variation_axes()])
    return f


def mono(px, weight=b"Regular"):
    f = ImageFont.truetype(MONO, px * S, layout_engine=ENGINE)
    f.set_variation_by_name(weight)
    return f


img = Image.new("RGB", (W * S, H * S), BG)
d = ImageDraw.Draw(img)


def text(x, y, s, font, fill, maxw):
    """Left-baseline text at 1x coordinates; fails instead of letting text run out of its box."""
    w = d.textlength(s, font=font) / S
    assert w <= maxw, (s, round(w), maxw)
    d.text((x * S, y * S), s, font=font, fill=fill, anchor="ls")
    return w


text(M, 126, "U1 Purge Ledger", sans(88, 700), INK, W - 2 * M)
for i, line in enumerate(["What each colour change costs on a Snapmaker U1, read from the sliced G-code.",
                          "No printer needed. First real file: 2 colours, Snapmaker Orca 2.4.1, default profiles."]):
    text(M, 174 + 38 * i, line, sans(28, 400), SUB, W - 2 * M)

PAD, GUTTER, CARD_H = 32, 40, 192
HALF = (W - 2 * M - 2 * PAD - GUTTER) // 2
f_id, f_head, f_label, f_big, f_mono = mono(22), sans(26, 600), sans(22, 600), sans(34, 600), mono(21, b"Medium")
for n, (cid, title, left, right) in enumerate(CARDS):
    top = 252 + n * (CARD_H + 18)
    d.rounded_rectangle([M * S, top * S, (W - M) * S, (top + CARD_H) * S], radius=14 * S,
                        fill=CARD, outline=LINE, width=S)
    x = M + PAD
    w = text(x, top + 47, cid, f_id, MUTED, HALF)
    text(x + w + 16, top + 47, title, f_head, INK, W - M - PAD - (x + w + 16))
    for i, (big, detail, color, label) in enumerate([left, right]):
        hx = x + i * (HALF + GUTTER)
        d.rectangle([hx * S, (top + 74) * S, (hx + 4) * S - 1, (top + 168) * S], fill=color)
        text(hx + 20, top + 96, label, f_label, color, HALF - 20)
        text(hx + 20, top + 134, big, f_big, INK, HALF - 20)
        text(hx + 20, top + 164, detail, f_mono, DETAIL, HALF - 20)

text(M, 708, "github.com/DesignMaster-Solutions/u1-purge-ledger · GPL-3.0", sans(22, 400), FOOT, W - 2 * M)

out = img.resize((W, H), Image.LANCZOS)
assert out.size == (1280, 760)
out.save(OUT, optimize=True)
print("%s %dx%d layout=%s" % (OUT, W, H, "raqm" if ENGINE == ImageFont.Layout.RAQM else "basic"))
