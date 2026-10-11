"""Mosaic downloaded 1deg x 1deg GeoTIFF tiles and write a Cloud Optimized GeoTIFF.

Usage (backscatter DN -> dB; check the product manual for the real gain/offset):
    python scripts/prepare_cogs.py --glob "data/raw/sar_backscatter_db_*.tif" --out data/cogs/sar_backscatter_db.tif --kind continuous
    python scripts/prepare_cogs.py --glob "data/raw/water_spread_*.tif"        --out data/cogs/water_spread.tif        --kind categorical
"""
import os

# A system PROJ (e.g. from PostGIS) can shadow rasterio's bundled proj.db; use the bundled one.
for _v in ("PROJ_LIB", "PROJ_DATA"):
    os.environ.pop(_v, None)

import argparse
import glob
from pathlib import Path

import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.shutil import copy as rio_copy
from rasterio.io import MemoryFile


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--glob", required=True, help="glob of input tiles")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--kind", choices=["continuous", "categorical"], required=True,
                    help="continuous -> bilinear overviews, categorical -> nearest")
    ap.add_argument("--dn-to-db", action="store_true",
                    help="convert linear amplitude/intensity DN to dB: 10*log10(DN*scale+offset)")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--offset", type=float, default=0.0)
    a = ap.parse_args()

    paths = sorted(glob.glob(a.glob))
    if not paths:
        raise SystemExit(f"no files match {a.glob}")
    srcs = [rasterio.open(p) for p in paths]
    nodata = srcs[0].nodata
    mosaic, transform = merge(srcs, nodata=nodata)
    profile = srcs[0].profile.copy()
    for s in srcs:
        s.close()

    data = mosaic.astype("float32") if a.dn_to_db else mosaic
    if a.dn_to_db:
        lin = data * a.scale + a.offset
        with np.errstate(divide="ignore", invalid="ignore"):
            data = np.where(lin > 0, 10 * np.log10(lin), np.nan).astype("float32")
        nodata = -9999.0
        data = np.where(np.isnan(data), nodata, data).astype("float32")
        profile["dtype"] = "float32"

    profile.update(driver="GTiff", height=data.shape[1], width=data.shape[2],
                   transform=transform, nodata=nodata)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    resampling = "BILINEAR" if a.kind == "continuous" else "NEAREST"
    with MemoryFile() as mem:
        with mem.open(**profile) as tmp:
            tmp.write(data)
        rio_copy(mem.open(), a.out, driver="COG", compress="DEFLATE",
                 blocksize=512, overview_resampling=resampling)
    print(f"wrote {a.out}  ({data.shape[2]}x{data.shape[1]} px, {len(paths)} tiles)")


if __name__ == "__main__":
    main()
