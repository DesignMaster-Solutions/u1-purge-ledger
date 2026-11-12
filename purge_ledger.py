#!/usr/bin/env python3
"""U1 Purge Ledger: how much filament each colour change really costs in a Snapmaker Orca G-code.

Reads the sliced file (no printer needed) and reports, per tool change, the filament extruded in the
prime tower (ramming + wipe), the tower upkeep on layers without a change (sparse layers), the slicer's
configured flush volume for that pair, and the tower footprint. Numbers come from the E words between
the markers Snapmaker Orca writes (``; WIPE_TOWER_START/END``, ``; CP TOOLCHANGE START/END``,
``; CP EMPTY GRID START/END``), not from the slicer's estimate.
"""
import gzip
import json
import math
import re
import sys

E_RE = re.compile(r"\bE(-?\d*\.?\d+)")
XY_RE = re.compile(r"\b([XY])(-?\d*\.?\d+)")
HDR_RE = re.compile(r"^; ([a-z_]+)(?: =|:) (.*)$")


def analyze(lines):
    hdr = {}
    for ln in lines:
        m = HDR_RE.match(ln)
        if m and m.group(1) in ("filament_diameter", "filament_density", "flush_volumes_matrix", "flush_multiplier",
                                "wipe_tower_no_sparse_layers", "purge_in_prime_tower", "prime_volume"):
            hdr[m.group(1)] = m.group(2).strip()
    trailer = next((ln for ln in lines if ln.startswith("; total filament used [g] = ")), None)
    slicer_total_g = float(trailer.split("=")[1]) if trailer else None
    diam = float(hdr.get("filament_diameter", "1.75").split(",")[0])
    dens = [float(v) for v in hdr.get("filament_density", "1.24").split(",")]
    area = math.pi * (diam / 2) ** 2
    matrix = [float(v) for v in hdr["flush_volumes_matrix"].split(",")] if "flush_volumes_matrix" in hdr else None
    n_tools = int(round(math.sqrt(len(matrix)))) if matrix else 4
    # shortcut: OrcaSlicer 2.5 writes one multiplier per extruder ("0.3,1,1,1"); the first is used. It only
    # reaches a number when purge_in_prime_tower = 1; upgrade when a 2.5 file with that key at 1 shows up.
    mult = float(hdr.get("flush_multiplier", "1").split(",")[0] or 1) or 1.0  # Orca writes 0 when unset: means 1x
    # U1 toolheads do not share a nozzle, so Snapmaker Orca purges the flush matrix in the tower only when
    # purge_in_prime_tower = 1; otherwise the tower only primes the incoming head (prime_volume, mm3).
    purge_matrix = hdr.get("purge_in_prime_tower", "0") == "1"
    prime_volume = float(hdr.get("prime_volume", "0") or 0)

    # wipe_tower_no_sparse_layers = 1 drops the tower only on layers with no tool change, so the tower
    # filament outside a change block is split by layer: sparse layers vs walls on a layer that has a change.
    change_layers, tower_layers, z = set(), set(), 0.0
    for ln in lines:
        s = ln.strip()
        if s.startswith(";Z:"): z = float(s[3:])
        elif "CP TOOLCHANGE START" in s: change_layers.add(z)
        elif "WIPE_TOWER_START" in s: tower_layers.add(z)

    relative = True  # Snapmaker Orca emits M83; M82/G92 handled below
    last_e = 0.0
    tool = None
    # A retraction pulls filament back; the next positive E only refills it. Counting that refill as
    # extrusion inflated the helado tower by a third (3.04 g vs 2.2 g). Tracked per tool: each U1 head
    # has its own filament, and the toolchange retraction (10 mm) is paid back by the SAME head next time.
    retracted = {}
    in_tower = in_change = False
    cur = None
    changes, grid_mm, walls_mm, object_mm, z = [], 0.0, 0.0, 0.0, 0.0
    bbox = [math.inf, math.inf, -math.inf, -math.inf]
    for ln in lines:
        s = ln.strip()
        if s.startswith(";"):
            if "WIPE_TOWER_START" in s: in_tower = True
            elif "WIPE_TOWER_END" in s: in_tower = False
            elif "CP TOOLCHANGE START" in s: in_change = True; cur = {"from": tool, "to": None, "z": z, "mm": 0.0}
            elif "CP TOOLCHANGE END" in s and cur: in_change = False; changes.append(cur); cur = None
            elif s.startswith(";Z:"): z = float(s[3:])
            continue
        code = s.split(";")[0].strip()
        if not code: continue
        w = code.split()[0]
        if w == "M83": relative = True; continue
        if w == "M82": relative = False; continue
        if w == "G92":
            m = E_RE.search(code); last_e = float(m.group(1)) if m else last_e; continue
        if w.startswith("T") and w[1:].isdigit():
            tool = int(w[1:])
            if cur: cur["to"] = tool
            continue
        if w not in ("G1", "G0"): continue
        m = E_RE.search(code)
        de = 0.0
        if m:
            e = float(m.group(1)); de = e if relative else e - last_e
            if not relative: last_e = e
        if de < 0:
            retracted[tool] = retracted.get(tool, 0.0) - de
            continue
        refill = min(de, retracted.get(tool, 0.0))
        retracted[tool] = retracted.get(tool, 0.0) - refill
        de -= refill
        if de <= 0: continue
        if in_tower:
            for ax, v in XY_RE.findall(code):
                v = float(v); i = 0 if ax == "X" else 1
                bbox[i] = min(bbox[i], v); bbox[i + 2] = max(bbox[i + 2], v)
            if in_change and cur: cur["mm"] += de
            elif z in change_layers: walls_mm += de  # tower walls on a layer that has a change
            else: grid_mm += de  # sparse layer: perimeter + empty grid, no change on this layer
        else:
            object_mm += de

    def mm3(mm): return mm * area
    def grams(mm, t): return mm3(mm) * dens[min(t or 0, len(dens) - 1)] / 1000.0
    rows = []
    for c in changes:
        a, b = c["from"], c["to"]
        if b is None: continue  # end-of-print block has no incoming tool
        if purge_matrix and matrix and a is not None and a != b and max(a, b) < n_tools: cfg = matrix[a * n_tools + b] * mult + prime_volume
        else: cfg = prime_volume
        rows.append({"z": round(c["z"], 2), "from": a, "to": b, "tower_mm3": round(mm3(c["mm"]), 1),
                     "tower_g": round(grams(c["mm"], b), 2), "configured_mm3": cfg})
    pairs = {}  # a 453-change print needs the answer per colour pair, not 453 rows
    for c in changes:
        if c["to"] is None: continue
        p = pairs.setdefault((c["from"], c["to"]), {"from": c["from"], "to": c["to"], "count": 0, "mm": 0.0})
        p["count"] += 1; p["mm"] += c["mm"]
    for p in pairs.values():  # grams from the pair's own volume, not from the rows' rounded grams
        mm = p.pop("mm"); p["tower_mm3"] = round(mm3(mm), 1); p["tower_g"] = round(grams(mm, p["to"]), 2)
    tower_mm = sum(c["mm"] for c in changes if c["to"] is not None) + grid_mm + walls_mm
    if not tower_mm + object_mm: raise ValueError("no extrusion found: is this a sliced .gcode file?")
    return {
        "tool_changes": len(rows), "changes": rows,
        "by_pair": sorted(pairs.values(), key=lambda p: -p["tower_mm3"]),
        "purge_matrix_in_tower": purge_matrix, "prime_volume_mm3": prime_volume,
        "sparse_layers_mm3": round(mm3(grid_mm), 1), "sparse_layers_g": round(grams(grid_mm, 0), 2),
        "sparse_layers": sum(1 for zz in tower_layers if zz not in change_layers),
        "change_layer_walls_mm3": round(mm3(walls_mm), 1), "change_layer_walls_g": round(grams(walls_mm, 0), 2),
        "tower_total_g": round(grams(tower_mm, 0), 2), "object_total_g": round(grams(object_mm, 0), 2),
        "tower_share_pct": round(100 * tower_mm / (tower_mm + object_mm), 1) if tower_mm + object_mm else 0.0,
        "tower_footprint_mm": None if bbox[0] is math.inf else [round(v, 1) for v in bbox],
        "no_sparse_layers_setting": hdr.get("wipe_tower_no_sparse_layers"),
        "slicer_total_g": slicer_total_g,
    }


class read_lines:
    """The file's lines, re-read on each pass: a 216 MB print held as a list took 1.4 GB, and the site runs this in a browser tab."""
    def __init__(self, path):
        self.path = path
        with open(path, "rb") as fh: self.gz = fh.read(2) == b"\x1f\x8b"  # .gcode.gz read as text gave an all-zero table

    def __iter__(self):
        with (gzip.open if self.gz else open)(self.path, "rt", encoding="utf-8", errors="replace") as fh: yield from fh


def report(r):
    out = [f"tool changes: {r['tool_changes']}   tower: {r['tower_total_g']} g of {r['tower_total_g'] + r['object_total_g']:.2f} g "
           f"({r['tower_share_pct']}% of the filament goes to the tower)"
           + (f"  [slicer trailer: {r['slicer_total_g']} g]" if r.get("slicer_total_g") else "")]
    if not r["tower_footprint_mm"]:
        out.append("no prime tower in this file (one colour, or enable_prime_tower = 0): no colour change to charge")
    out.append(f"{'z':>6} {'change':>7} {'tower mm3':>10} {'g':>6} {'slicer prime mm3':>17}")
    for c in r["changes"]:
        name = "T%s>T%s" % (c["from"], c["to"])
        out.append(f"{c['z']:>6} {name:>7} {c['tower_mm3']:>10} {c['tower_g']:>6} {c['configured_mm3']:>17.0f}")
    if r["by_pair"]:
        out.append("by pair, heaviest first:")
        out += ["  T%s>T%s x%d = %s mm3 = %s g" % (p["from"], p["to"], p["count"], p["tower_mm3"], p["tower_g"]) for p in r["by_pair"]]
    out.append(f"tower walls on the {len(set(c['z'] for c in r['changes']))} layers with a change: {r['change_layer_walls_mm3']} mm3 = {r['change_layer_walls_g']} g")
    out.append(f"sparse layers ({r['sparse_layers']} tower layers with no change): {r['sparse_layers_mm3']} mm3 = {r['sparse_layers_g']} g"
               f"  [wipe_tower_no_sparse_layers = {r['no_sparse_layers_setting']}]")
    if r["tower_footprint_mm"]:
        x0, y0, x1, y1 = r["tower_footprint_mm"]
        out.append(f"tower footprint: X {x0}..{x1}  Y {y0}..{y1}  ({x1 - x0:.0f} x {y1 - y0:.0f} mm)")
    return "\n".join(out)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--json"]
    if len(args) != 1: sys.exit("usage: purge_ledger.py FILE.gcode [--json]")
    try: res = analyze(read_lines(args[0]))
    except ValueError as e: sys.exit(f"{args[0]}: {e}")
    print(json.dumps(res, indent=1) if "--json" in sys.argv else report(res))
