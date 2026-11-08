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
sparse layers (tower upkeep without a change): 1004.1 mm3 = 1.27 g  [wipe_tower_no_sparse_layers = 0]
tower footprint: X 8.1..45.9  Y 130.1..167.3  (38 x 37 mm)
```

Two things the slicer's own summary does not show:

1. **On the U1 the tower is a prime tower, not a purge tower.** Each toolhead has its own nozzle, so the
   profile ships with `purge_in_prime_tower = 0` and the 4x4 flush matrix (127 to 487 mm3 per pair in this
   file) is never extruded. Every change costs about 79 mm3: the 45 mm3 prime plus the tower walls of that layer.
   Settings copied from single-nozzle multi-material printers (big flush multipliers, wide towers) buy nothing here.
2. **Layers without a change cost more than the changes.** 1.27 g of the 3.04 g tower is upkeep on the 42 layers
   where no tool change happens. `wipe_tower_no_sparse_layers = 1` drops it, at the price of a tower that is
   not flat on top.

## Checks

`python3 tests/test_ledger.py` runs a synthetic file with one change where every number is known by hand
(retraction is not counted, the end-of-print block is not a change, `purge_in_prime_tower` switches the
configured column). The real file above is the second check; its numbers are reproduced by the command.

## Status

Phase 2 project for the Snapmaker Innovation Fund, in progress. Next: time cost of the tower measured with the
real firmware (via the Dry Run), and a before/after comparison when the same project is re-sliced with the
settings the ledger points at.

Unofficial, not affiliated with Snapmaker. GPL-3.0, same as the firmware it reads for.
