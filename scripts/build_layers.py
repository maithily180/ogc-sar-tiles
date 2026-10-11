"""Turn the fetched rasters into the COG layers published by publish.py.

Outputs in data/cogs/: sar_dry_db, sar_monsoon_db, sar_change_db (monsoon minus dry, dB), water_spread.
"""
import os

for _v in ("PROJ_LIB", "PROJ_DATA"):  # a system PROJ (e.g. PostGIS) can shadow rasterio's bundled proj.db
    os.environ.pop(_v, None)

import argparse
from pathlib import Path

import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.shutil import copy as rio_copy

NODATA_DB = -9999.0


def to_db(path: Path):
    with rasterio.open(path) as src:
        lin = src.read(1).astype("float32")
        profile = src.profile.copy()
    ok = np.isfinite(lin) & (lin > 0)
    db = np.full(lin.shape, NODATA_DB, "float32")
    db[ok] = 10 * np.log10(lin[ok])
    return db, profile


def write_cog(path: Path, data, profile, nodata, resampling):
    profile = {**profile, "driver": "GTiff", "count": 1, "dtype": str(data.dtype), "nodata": nodata,
               "height": data.shape[0], "width": data.shape[1]}
    profile.pop("blockxsize", None); profile.pop("blockysize", None); profile.pop("tiled", None)
    path.parent.mkdir(parents=True, exist_ok=True)
    with MemoryFile() as mem:
        with mem.open(**profile) as tmp:
            tmp.write(data, 1)
        rio_copy(mem.open(), path, driver="COG", compress="DEFLATE", blocksize=512,
                 overview_resampling=resampling)
    print(f"wrote {path} ({data.shape[1]}x{data.shape[0]})")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, default=Path("data/real"))
    ap.add_argument("--out", type=Path, default=Path("data/cogs"))
    a = ap.parse_args()

    dry, prof = to_db(a.src / "s1_vv_dry.tif")
    wet, prof_w = to_db(a.src / "s1_vv_monsoon.tif")
    assert dry.shape == wet.shape and prof["transform"] == prof_w["transform"], "scenes are not on one grid"
    change = np.where((dry != NODATA_DB) & (wet != NODATA_DB), wet - dry, NODATA_DB).astype("float32")

    write_cog(a.out / "sar_dry_db.tif", dry, prof, NODATA_DB, "BILINEAR")
    write_cog(a.out / "sar_monsoon_db.tif", wet, prof, NODATA_DB, "BILINEAR")
    write_cog(a.out / "sar_change_db.tif", change, prof, NODATA_DB, "BILINEAR")
    with rasterio.open(a.src / "water_spread_jrc.tif") as src:
        water, wprof = src.read(1), src.profile.copy()
    write_cog(a.out / "water_spread.tif", water, wprof, 255, "NEAREST")


if __name__ == "__main__":
    main()
