# U1 Purge Ledger

What each colour change really costs on a Snapmaker U1, read from the sliced G-code. No printer needed.

```
python3 purge_ledger.py plate_1.gcode          # table
python3 purge_ledger.py plate_1.gcode --json   # same numbers for scripts
```

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
[U1 Dry Run](https://github.com/DesignMaster-Solutions/u1-dryrun) sample), 18 tool changes, 29.69 g.

```
tool changes: 18   tower: 3.04 g of 29.69 g (10.2% of the filament goes to the tower)
     z  change  tower mm3      g  slicer prime mm3
  4.25   T2>T1       58.8   0.07                45
  4.45   T1>T2       79.2    0.1                45
  ...
  7.65   T1>T2       79.2    0.1                45
tower walls on the 18 layers with a change: 209.3 mm3 = 0.26 g
sparse layers (20 tower layers with no change): 794.8 mm3 = 1.0 g  [wipe_tower_no_sparse_layers = 0]
tower footprint: X 8.1..45.9  Y 130.1..167.3  (38 x 37 mm)
```

Two things the slicer's own summary does not show:

1. **On the U1 the tower is a prime tower, not a purge tower.** Each toolhead has its own nozzle, so the
   profile ships with `purge_in_prime_tower = 0` and the 4x4 flush matrix (127 to 487 mm3 per pair in this
   file) is never extruded. Every change costs about 79 mm3: the 45 mm3 prime plus the tower walls of that layer.
   Settings copied from single-nozzle multi-material printers (big flush multipliers, wide towers) buy nothing here.
2. **A third of the tower is printed on layers with no change.** 1.0 g of the 3.04 g tower is upkeep on the 20
   layers where no tool change happens (the first 4 mm of this print, before the second colour starts).
   `wipe_tower_no_sparse_layers = 1` drops exactly that, at the price of a tower that is not flat on top; the
   0.26 g of tower walls on the layers that do change stay.

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

## Checks

`python3 tests/test_ledger.py` runs a synthetic file with one change where every number is known by hand
(retraction is not counted, the end-of-print block is not a change, tower walls on a change layer are not
sparse layers, `purge_in_prime_tower` switches the configured column, `without_sparse_layers.py` removes only
the no-change layers). The real file above is the second check; its numbers are reproduced by the command.

## Status

Phase 2 project for the Snapmaker Innovation Fund, in progress. Next: the same project re-sliced in Snapmaker
Orca with `wipe_tower_no_sparse_layers = 1`, run through the ledger and the Dry Run, to compare the real
slicer output with the measuring copy above.

Unofficial, not affiliated with Snapmaker. GPL-3.0, same as the firmware it reads for.
