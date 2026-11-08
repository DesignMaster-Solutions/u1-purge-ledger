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
