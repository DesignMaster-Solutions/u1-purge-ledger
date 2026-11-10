"""Synthetic U1 G-code with one tool change: numbers are known, so every column is checked by hand."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from purge_ledger import analyze

AREA = math.pi * 0.875 ** 2  # 1.75 mm filament
G = """; filament_diameter: 1.75,1.75,1.75,1.75
; filament_density: 1.24,1.24,1.24,1.24
; flush_volumes_matrix = 0,100,100,100,100,0,100,100,100,100,0,100,100,100,100,0
; purge_in_prime_tower = 0
; prime_volume = 45
; wipe_tower_no_sparse_layers = 0
M83
T0
;Z:0.2
G1 X10 Y10 E5.0
G1 E-0.5
G1 X12 Y12 E0.5
; WIPE_TOWER_START
G1 X20 Y130 E1.0
; CP EMPTY GRID START
G1 X40 Y130 E2.0
; CP EMPTY GRID END
; WIPE_TOWER_END
;Z:0.4
G1 X10 Y10 E7.0
; CP TOOLCHANGE START
; WIPE_TOWER_START
G1 E-5.0
G1 X20 Y150 E3.0
T1
G1 X40 Y150 E4.0
; WIPE_TOWER_END
; CP TOOLCHANGE END
; WIPE_TOWER_START
G1 X20 Y130 E1.5
; WIPE_TOWER_END
G1 X10 Y10 E8.0
; CP TOOLCHANGE START
; WIPE_TOWER_START
G1 X20 Y150 E9.0
; WIPE_TOWER_END
; CP TOOLCHANGE END
""".splitlines()

r = analyze(G)
assert r["tool_changes"] == 1, r  # the trailing block without a T is the end of the print, not a change
c = r["changes"][0]
assert (c["from"], c["to"], c["z"]) == (0, 1, 0.4), c
# T0 retracts 5.0 and only refills 3.0 (nothing extruded); T1's 4.0 is extrusion: the 2.0 still retracted on T0 is
# not T1's to pay back. A single counter would give 2.0 here; the old positive-only sum gave 7.0.
assert abs(c["tower_mm3"] - 4.0 * AREA) < 0.06, c  # report rounds to 0.1 mm3
assert c["configured_mm3"] == 45, c  # purge_in_prime_tower = 0: only the prime volume applies
assert abs(r["sparse_layers_mm3"] - round(3.0 * AREA, 1)) < 0.11, r  # perimeter + empty grid on the no-change layer
assert abs(r["change_layer_walls_mm3"] - round(1.5 * AREA, 1)) < 0.11, r  # tower walls after a change stay with the change layer
assert abs(r["object_total_g"] - round((5 + 7 + 8) * AREA * 1.24 / 1000, 2)) < 0.011, r  # E9.0 sits in the tower; the E-0.5/E0.5 pair is a retraction paid back, not filament
assert r["tower_footprint_mm"] == [20.0, 130.0, 40.0, 150.0], r
r2 = analyze([l.replace("purge_in_prime_tower = 0", "purge_in_prime_tower = 1") for l in G])
assert r2["changes"][0]["configured_mm3"] == 145, r2  # matrix[0][1] + prime volume
from without_sparse_layers import without_sparse_layers
r3 = analyze(without_sparse_layers(G))
assert r3["sparse_layers_mm3"] == 0 and r3["tool_changes"] == 1, r3  # only the no-change layer's tower is dropped
assert r3["object_total_g"] == r["object_total_g"] and r3["change_layer_walls_mm3"] == r["change_layer_walls_mm3"], r3
print("ok")

# Real files: the coaster (examples/coaster) sliced in Snapmaker Orca 2.4.1 with the sparse-layer key at 0 and 1.
import gzip
EV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "evidence", "coaster")
def real(name):
    with gzip.open(os.path.join(EV, name), "rt", encoding="utf-8", errors="replace") as fh:
        return analyze(fh.read().splitlines())
k0, k1 = real("coaster-2.4.1-sparse0.gcode.gz"), real("coaster-2.4.1-sparse1.gcode.gz")
assert (k0["no_sparse_layers_setting"], k1["no_sparse_layers_setting"]) == ("0", "1"), (k0, k1)
assert k0["tool_changes"] == k1["tool_changes"] == 5, (k0["tool_changes"], k1["tool_changes"])
assert (k0["sparse_layers"], k1["sparse_layers"]) == (25, 0), (k0["sparse_layers"], k1["sparse_layers"])  # 0.2..5.0 mm, logo starts at 5
for k in (k0, k1):  # the ledger's total is the slicer's own trailer
    assert abs(k["tower_total_g"] + k["object_total_g"] - k["slicer_total_g"]) < 0.011, k
saved = k0["tower_total_g"] - k1["tower_total_g"]
assert abs(saved - (k0["slicer_total_g"] - k1["slicer_total_g"])) < 0.02, (saved, k0["slicer_total_g"], k1["slicer_total_g"])  # the whole difference is the tower
assert k1["sparse_layers_g"] == 0 and k0["sparse_layers_g"] > saved, (k0["sparse_layers_g"], saved)  # the key drops 1.1 g of upkeep and spends ~0.13 g more on the change layers' walls
print("ok real coaster", k0["sparse_layers_g"], "g of sparse layers ->", round(saved, 2), "g saved")

# Files a U1 owner really drops in: OrcaSlicer 2.5.0-rc writes one flush multiplier per extruder and a matrix sized
# to the filaments in use; a single-colour file has no tower at all; the CLI gets the .gcode.gz as often as the site.
G25 = [l.replace("; purge_in_prime_tower = 0", "; purge_in_prime_tower = 1\n; flush_multiplier = 0.3,1,1,1")
        .replace("0,100,100,100,100,0,100,100,100,100,0,100,100,100,100,0", "0,0,0,0") for l in G]
r25 = analyze("\n".join(G25).splitlines())
assert r25["tool_changes"] == 1 and r25["changes"][0]["configured_mm3"] == 45, r25  # 0 mm3 flush x 0.3 + 45 prime
from purge_ledger import report, read_lines
solo = analyze(["M83", "T0", ";Z:0.2", "G1 X10 Y10 E5.0"])
assert solo["tool_changes"] == 0 and "no prime tower in this file" in report(solo), report(solo)
assert "no prime tower" not in report(r), report(r)
assert analyze(read_lines(os.path.join(EV, "coaster-2.4.1-sparse0.gcode.gz"))) == k0  # gzip by magic bytes, not by name
try: analyze(["hello", "world"]); raise AssertionError("garbage accepted")
except ValueError as e: assert "no extrusion" in str(e), e
print("ok orca 2.5 header, no tower, gz, not a g-code")
