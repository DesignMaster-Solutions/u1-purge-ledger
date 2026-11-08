# coaster: second colour only on top

`python3 make_models.py out/` writes the STLs (base with a pocket, logo), `python3 make_3mf.py coaster.3mf` writes the
one-object, two-part 3MF with the logo on extruder 2 (`Metadata/model_settings.config`). Slice it headless with a
Snapmaker Orca Linux build (same recipe as the Dry Run's `tools/slice_sign_linux.sh`, without `--load-filament-ids`,
which must match the number of input files):

```
xvfb-run -a squashfs-root/AppRun --arrange 0 --allow-newer-file --load-settings "machine.json;process.json" \
  --load-filaments "fil1.json;fil2.json" --slice 0 --outputdir out coaster.3mf
```

Two loose STLs do not reproduce this case: the CLI drops each object onto the bed, so the logo lands at z 0 inside the
base and slicing stops with a G-code path conflict.
