# U1 Purge Ledger

What each colour change really costs on a Snapmaker U1, read from the sliced G-code. No printer needed.

```
python3 purge_ledger.py plate_1.gcode          # table
python3 purge_ledger.py plate_1.gcode --json   # same numbers for scripts
```

Web: https://designmaster-solutions.github.io/u1-purge-ledger/ runs the same `purge_ledger.py` in the browser (Python via Pyodide, nothing is uploaded): drop the `.gcode` or `.gcode.gz`, or press the sample button to see the coaster from `docs/evidence`. Release zip of the CLI: https://github.com/DesignMaster-Solutions/u1-purge-ledger/releases.

Snapmaker Orca marks the prime tower (`; WIPE_TOWER_START/END`), each tool change (`; CP TOOLCHANGE START/END`)
and the tower upkeep on layers without a change (`; CP EMPTY GRID START/END`). The ledger sums the E words
between those markers, converts them with the filament diameter and density written in the file header, and
reports:

- per tool change: layer height, pair (`T2>T1`), filament extruded in the tower (mm3 and g) and what the slicer
  was asked for (`prime_volume`; plus the `flush_volumes_matrix` entry when `purge_in_prime_tower = 1`);
- the tower upkeep on layers with no change (the *sparse layers*), which `wipe_tower_no_sparse_layers = 1`
  removes;
- the share of the whole print that goes to the tower and the tower footprint on the plate.

## What the first real file says

Sample: a 2-colour fidget sliced in Snapmaker Orca 2.4.1 (the file from the
[U1 Dry Run](https://github.com/DesignMaster-Solutions/u1-dryrun) sample), 18 tool changes, 23.94 g.

```
tool changes: 18   tower: 2.27 g of 23.94 g (9.5% of the filament goes to the tower)  [slicer trailer: 23.94 g]
     z  change  tower mm3      g  slicer prime mm3
  4.25   T2>T1       47.9   0.06                45
  4.45   T1>T2       47.9   0.06                45
  ...
  7.65   T1>T2       47.9   0.06                45
tower walls on the 18 layers with a change: 144.4 mm3 = 0.18 g
sparse layers (20 tower layers with no change): 794.8 mm3 = 1.0 g  [wipe_tower_no_sparse_layers = 0]
tower footprint: X 8.1..45.9  Y 130.1..167.3  (38 x 37 mm)
```

Two things the slicer's own summary does not show:

1. **On the U1 the tower is a prime tower, not a purge tower.** Each toolhead has its own nozzle, so the
   profile ships with `purge_in_prime_tower = 0` and the 4x4 flush matrix (127 to 487 mm3 per pair in this
   file) is never extruded. Every change costs about 48 mm3, which is the 45 mm3 prime the profile asks for;
   the tower walls of that layer are another 8 mm3 (144 mm3 over the 18 layers).
   Settings copied from single-nozzle multi-material printers (big flush multipliers, wide towers) buy nothing here.
2. **Almost half of the tower is printed on layers with no change.** 1.0 g of the 2.27 g tower is upkeep on the 20
   layers where no tool change happens (the first 4 mm of this print, before the second colour starts).
   `wipe_tower_no_sparse_layers = 1` drops exactly that, at the price of a tower that is not flat on top; the
   0.18 g of tower walls on the layers that do change stay.

The ledger's total is checked against the slicer's own trailer (`; total filament used [g]`), printed on the first
line: 23.94 g against 23.94 g here. Until 2026-11-08 the ledger counted the refill after every retraction as
extrusion, which put the tower at 3.04 g of 29.69 g and each change at about 79 mm3; the per-head retraction
tracking in `purge_ledger.py` fixed that, and the numbers above are the corrected ones.

**What those 20 layers cost in time, measured on the real firmware.** `without_sparse_layers.py` writes a copy of
the file with the tower removed on the no-change layers (the same cut the setting makes, applied after slicing,
for measuring only). Both files through the [U1 Dry Run](https://github.com/DesignMaster-Solutions/u1-dryrun) on
firmware 2.1.0:

| file | moves | motion time (no heating) |
|---|---|---|
| as sliced | 121,206 | 2226 s |
| without the sparse-layer tower | 112,581 | 2102 s |

124 s (5.6% of the motion time) and 1.0 g for 20 layers of tower nobody needs. The travel to the tower on those
layers is left in the measuring copy, so the real saving is slightly larger. The one scar the Dry Run reports in
this file (the final tool change, Orca 2.4.1) is unchanged by this: it is on the last layer, which has a change.

## Re-sliced in the real slicer: a model where the setting has nothing to remove

The two-colour sign from the Dry Run examples (`ring.stl` + `inlay.stl`, 15 layers, 97.55 g) sliced twice in
Snapmaker Orca 2.4.1 on Linux, with `wipe_tower_no_sparse_layers` at 0 and at 1
([docs/evidence/sign](docs/evidence/sign)):

| | tower | sparse layers | moves (Dry Run 2.1.0) | motion time |
|---|---|---|---|---|
| `= 0` | 1.48 g of 97.55 g (1.5%) | 0 layers, 0.0 g | 34,410 | 7120 s |
| `= 1` | 1.48 g of 97.55 g (1.5%) | 0 layers, 0.0 g | 34,410 | 7126 s |

Both colours are present from the first layer, so every one of the 15 layers has a change and there is no sparse
layer to drop: the two files differ only in where the `M73` progress lines sit. The ledger says that from the
first file alone (`sparse layers (0 tower layers with no change)`), which is the point: it tells you whether the
setting will buy anything on your model before you slice twice. On the fidget above it buys 1.0 g and 124 s.

## Checks

`python3 tests/test_ledger.py` runs a synthetic file with one change where every number is known by hand
(a retraction and its refill are not filament, and a refill is only paid back by the head that retracted; the
end-of-print block is not a change; tower walls on a change layer are not sparse layers; `purge_in_prime_tower`
switches the configured column; `without_sparse_layers.py` removes only the no-change layers). The real files
above are the second check: their numbers are reproduced by the command and the totals match the slicer's trailer.

## Re-sliced in the real slicer: a model where the second colour starts above the bed

The common two-colour print is a one-colour body with a logo or text on top. `examples/coaster` is that: a
40 x 40 x 6 mm base (filament 1) with a 20 x 20 mm inlay in its last millimetre (filament 2), one object with
two parts ([coaster.3mf](examples/coaster/coaster.3mf), written by `make_3mf.py`; a loose STL above the bed does
not work, the CLI drops every object onto the plate). Sliced twice in Snapmaker Orca 2.4.1 on Linux, default U1
profiles, `wipe_tower_no_sparse_layers` at 0 and at 1 ([docs/evidence/coaster](docs/evidence/coaster)):

| | tower | sparse layers | walls on the 5 change layers | footprint | moves (Dry Run 2.1.0) | motion time |
|---|---|---|---|---|---|---|
| `= 0` | 1.44 g of 6.77 g (21.3%) | 25 layers, 885.0 mm3 = 1.1 g | 37.9 mm3 = 0.05 g | 38 x 37 mm | 19,099 | 792 s |
| `= 1` | 0.47 g of 5.80 g (8.2%) | 0 layers | 142.6 mm3 = 0.18 g | 33 x 33 mm | 8,829 | 667 s |

The 5 changes (z 5.25 to 6.05, 47.9 mm3 each, the 45 mm3 prime) are identical in both files. What the setting
removes is the 25 tower layers under the logo (0.2 to 5.0 mm, where nothing changes): 1.1 g, a sixth of the
print. It gives 0.13 g back as fuller walls on the layers that do change, so the file is 0.97 g lighter, 14% of
the filament. The ledger reads both from the first file alone: `sparse layers (25 tower layers with no change)`
is the number to look at before deciding to flip the key. The totals match the slicer's trailer in both files
(6.77 g and 5.80 g), and `tests/test_ledger.py` re-reads these two files on every run. On the real firmware the
cut is also 125 s of motion (16%), and the one scar the Dry Run reports (the final tool change at Z6.05, the Orca
2.4.1 regression) is in both files: the setting does not touch the layers that change.

## Status

Phase 2 project for the Snapmaker Innovation Fund, submitted as [forum topic 44126](https://forum.snapmaker.com/t/44126) on 2026-11-08; updates go in one comment there. Next: a per-layer view of where the tower could be shorter.

Unofficial, not affiliated with Snapmaker. GPL-3.0, same as the firmware it reads for.
