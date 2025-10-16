Blind Hams Solar MUF Mask
=========================

The MUF grid builder now accepts a *mask* file that tells it where to sample at
different resolutions. Masks let us keep oceans coarse (e.g., 5°) while dialing
in 2° or 1° resolution over land-heavy regions such as North America, Europe,
and East Asia. The format is intentionally simple—plain JSON with numeric bounds
so it can be edited with a screen reader and shared via git.

Mask File Layout
----------------

`solar/land_mask.json` ships with the repo as a starting point. It contains:

- `default_step`: fallback resolution in degrees. Anything not matched by a
  region uses this step.
- `regions[]`: ordered list of latitude/longitude boxes (`lat_min`, `lat_max`,
  `lon_min`, `lon_max`) plus a `step` value. Regions can overlap; the builder
  effectively unions the coordinates, so smaller steps add extra sample points
  inside broader boxes.

Example snippet:

```json
{
  "default_step": 5.0,
  "regions": [
    { "name": "north_america_land_2deg", "lat_min": 5.0, "lat_max": 75.0,
      "lon_min": -170.0, "lon_max": -40.0, "step": 2.0 },
    { "name": "north_america_high_1deg", "lat_min": 15.0, "lat_max": 60.0,
      "lon_min": -135.0, "lon_max": -60.0, "step": 1.0 }
  ]
}
```

Generating a Mask from Natural Earth
------------------------------------

Run `solar/generate_land_mask.py` against the Natural Earth 1:50m land
shapefile (`ne_50m_land.shp`). The helper uses the pure-Python **pyshp**
module, so install it first: `python3 -m pip install --user pyshp`.

```bash
python3 solar/generate_land_mask.py solar/ne/ne_50m_land.shp \
  --output solar/land_mask_generated.json \
  --default-step 5 --land-step 1 --verbose
```

- The script walks a 1° grid and tags cells whose centers fall on land.
- Each land cell becomes a 1° region entry; everything else falls back to the
  mask’s `default_step`.
- Adjust `--lat-min`, `--lat-max`, `--lon-min`, `--lon-max` if you only need a
  sub-region while iterating.

Once generated, either replace `solar/land_mask.json` or merge it with any
hand-authored overrides you want to keep.

Using the Mask
--------------

Pass `--mask` to `build_muf_grid.py`:

```bash
python3 solar/build_muf_grid.py \
  --step 2 \
  --mask solar/land_mask.json \
  --workers auto \
  --output solar/solar_muf_grid.json
```

- `--step` still sets the fallback resolution. The mask’s `default_step` takes
  priority if present.
- When the mask is active the script prints the distinct step sizes and embeds a
  `mask_summary` object in the JSON output (default step, region count,
  step list).

Querying a Coordinate
---------------------

Use `solar/mask_query.py` to inspect which step applies at a given latitude and
longitude. This only reads the JSON—no map or GUI required.

```bash
python3 solar/mask_query.py solar/land_mask.json --lat 40.0 --lon -105.0
# lat=+40.00°, lon=-105.00° -> step 1.00° (regions: north_america_high_1deg, north_america_land_2deg)
```

Adjusting Regions
-----------------

- Edit `solar/land_mask.json` directly; keep entries sorted roughly by region.
- Bounds are inclusive and use decimal degrees. Longitude is positive east,
  negative west (matches the IRI driver’s expectations).
- Add targeted 1° boxes for islands or special-interest zones (e.g., Hawaii,
  Azores) and broader 2° boxes to cover large landmasses.
- After edits, run a coarse check (e.g., `--step 10 --mask … --workers auto`)
  and inspect the runtime plus output size before committing to a full 2° pass.

Future Enhancements
-------------------

- Keep the mask config in the repo root and bundle it with deployment artifacts
  so Roarbox and the LA colo host stay in sync.
- Add optional override files to bump specific nets/regions to 1° without
  regenerating the Natural Earth-derived baseline.
