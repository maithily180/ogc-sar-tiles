"""Build the published COG layers from Bhoonidhi EOS-04 product zips.

Put the downloaded zips (or already extracted folders) in data/bhoonidhi/ and run:

    python scripts/build_bhoonidhi_layers.py

Per EOS-04 SAR MRS 1x1-degree tile it writes data/cogs/<layer>.tif and regenerates layers.json:
  * ws_c<cycle>            water spread (GEOPHYSICAL-PARAMETER WATER-SPREAD: 0 land, 2 water, 3 background)
  * bs_c<cycle>            backscatter mosaic (converted to dB, see --bs-mode)
  * wschange_c<a>_c<b>     derived: water change between the first and last cycle
                            (1 stable water, 2 gained, 3 lost)
"""
import os

for _v in ("PROJ_LIB", "PROJ_DATA"):  # a system PROJ (e.g. PostGIS) can shadow rasterio's bundled proj.db
    os.environ.pop(_v, None)

import argparse
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.shutil import copy as rio_copy

WATER_ND = 3      # ImageBackground in the product meta
CHANGE_ND = 255
BS_ND = -9999.0


def read_meta(path: Path) -> dict:
    out = {}
    for line in path.read_text(errors="replace").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def discover(root: Path):
    """Extract zips next to themselves and return [(meta, tif_path)]."""
    for z in sorted(root.glob("*.zip")):
        d = root / z.stem
        if not d.exists():
            with zipfile.ZipFile(z) as zf:
                zf.extractall(d)
    prods = []
    for meta in sorted(root.glob("*/*.meta")):
        tif = meta.with_suffix(".tif")
        if tif.exists():
            prods.append((read_meta(meta), tif))
    return prods


def write_cog(path: Path, data: np.ndarray, profile: dict, nodata, resampling: str):
    prof = {k: v for k, v in profile.items() if k not in ("blockxsize", "blockysize", "tiled", "photometric")}
    prof.update(driver="GTiff", count=1, dtype=str(data.dtype), nodata=nodata,
                height=data.shape[0], width=data.shape[1], compress="deflate")
    path.parent.mkdir(parents=True, exist_ok=True)
    with MemoryFile() as mem:
        with mem.open(**prof) as tmp:
            tmp.write(data, 1)
        rio_copy(mem.open(), path, driver="COG", compress="DEFLATE", blocksize=512,
                 overview_resampling=resampling)
    print(f"wrote {path} ({data.shape[1]}x{data.shape[0]})")


def span(m):  # '07-AUG-2026'/'23AUG2026' style dates -> short label
    return f"{m['StartDate'].replace('-', ' ').title()} to {m['EndDate'].replace('-', ' ').title()}" if " " in m["EndDate"] or "-" in m["EndDate"] else f"{m['StartDate'].title()} to {m['EndDate'].title()}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, default=Path("data/bhoonidhi"))
    ap.add_argument("--out", type=Path, default=Path("data/cogs"))
    ap.add_argument("--manifest", type=Path, default=Path("layers.json"))
    ap.add_argument("--bs-mode", choices=["auto", "db", "linear"], default="auto",
                    help="how to interpret backscatter DN; 'auto' reads the product meta")
    a = ap.parse_args()

    prods = discover(a.src)
    if not prods:
        raise SystemExit(f"no products found in {a.src}")
    layers, water = [], {}

    for meta, tif in sorted(prods, key=lambda p: int(p[0]["Cycle_Number"])):
        cyc = int(meta["Cycle_Number"])
        desc = meta.get("GPDescription", "")
        label = f"cycle {cyc}, {meta['StartDate']} to {meta['EndDate']}"
        with rasterio.open(tif) as src:
            arr, profile = src.read(1), src.profile.copy()
        if desc == "WATER-SPREAD":
            water[cyc] = (arr, profile)
            name = f"ws_c{cyc}"
            write_cog(a.out / f"{name}.tif", arr, profile, WATER_ND, "NEAREST")
            layers.append({"name": name, "file": f"{name}.tif", "style": "water_class",
                           "title": f"EOS-04 water spread, {label}",
                           "abstract": f"ISRO EOS-04 SAR MRS water-spread product, tile {meta['TileId']}, {label}. "
                                       "0 land, 2 water, 3 background. Source: Bhoonidhi."})
        else:
            print(f"skipping {tif.name}: backscatter handled in build step 2 ({desc or meta.get('ProductType')})")

    if len(water) >= 2:
        c0, c1 = min(water), max(water)
        (w0, prof), (w1, _) = water[c0], water[c1]
        valid = (w0 != WATER_ND) & (w1 != WATER_ND)
        a0, a1 = (w0 == 2), (w1 == 2)
        ch = np.zeros(w0.shape, "uint8")
        ch[a0 & a1] = 1
        ch[~a0 & a1] = 2
        ch[a0 & ~a1] = 3
        ch[~valid] = CHANGE_ND
        name = f"wschange_c{c0}_c{c1}"
        write_cog(a.out / f"{name}.tif", ch, prof, CHANGE_ND, "NEAREST")
        layers.append({"name": name, "file": f"{name}.tif", "style": "water_change",
                       "title": f"Water change, cycle {c0} to {c1}",
                       "abstract": f"Derived from EOS-04 water spread: 1 stable water, 2 gained, 3 lost between "
                                   f"cycle {c0} and cycle {c1}. Gained = {int((ch == 2).sum())} px, lost = {int((ch == 3).sum())} px."})
        print(f"change c{c0}->c{c1}: stable={int((ch == 1).sum())} gained={int((ch == 2).sum())} lost={int((ch == 3).sum())}")

    manifest = {"workspace": "bhoonidhi", "layers": layers}
    a.manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {a.manifest} with {len(layers)} layers")


if __name__ == "__main__":
    main()
