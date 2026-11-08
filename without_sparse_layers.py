#!/usr/bin/env python3
"""Write a copy of a Snapmaker Orca G-code without the prime tower on layers that have no tool change.

This is what ``wipe_tower_no_sparse_layers = 1`` removes, applied after slicing so the same print can be
run through the U1 Dry Run (real firmware) with and without those layers and the time difference read.
It is a measuring aid, not a print file: re-slice with the setting to actually print without them.
"""
import sys


def without_sparse_layers(lines):
    change_layers, z = set(), 0.0
    for ln in lines:
        s = ln.strip()
        if s.startswith(";Z:"): z = float(s[3:])
        elif "CP TOOLCHANGE START" in s: change_layers.add(z)
    out, z, skipping = [], 0.0, False
    for ln in lines:
        s = ln.strip()
        if s.startswith(";Z:"): z = float(s[3:])
        if "WIPE_TOWER_START" in s and z not in change_layers: skipping = True
        if not skipping: out.append(ln)
        if "WIPE_TOWER_END" in s: skipping = False
    return out


if __name__ == "__main__":
    if len(sys.argv) != 3: sys.exit("usage: without_sparse_layers.py IN.gcode OUT.gcode")
    with open(sys.argv[1], encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    out = without_sparse_layers(lines)
    with open(sys.argv[2], "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"{len(lines) - len(out)} lines of sparse-layer tower removed -> {sys.argv[2]}")
