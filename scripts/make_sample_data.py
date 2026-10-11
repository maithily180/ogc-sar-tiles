"""Generate SYNTHETIC EOS-04-like 1deg x 1deg tiles for development and offline demos.

The output imitates the *structure* of the Bhoonidhi products (1x1 degree GeoTIFF tiles,
SAR backscatter in dB plus a binary water-spread class). It is NOT real EOS-04 data.
Replace it with real downloads via scripts/prepare_cogs.py.
"""
import os

# A system PROJ (e.g. from PostGIS) can shadow rasterio's bundled proj.db; use the bundled one.
for _v in ("PROJ_LIB", "PROJ_DATA"):
    os.environ.pop(_v, None)

import argparse
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin
from scipy.ndimage import gaussian_filter

NODATA_DB = -9999.0


def synth_tile(lon0: int, lat0: int, px: int, rng: np.random.Generator):
    """Return (backscatter_db, water_class) arrays for the 1deg tile whose SW corner is (lon0, lat0)."""
    land = rng.normal(-11.0, 2.0, (px, px))
    # smooth blobs -> reservoirs / lakes; thresholded field gives realistic-looking shapes
    field = gaussian_filter(rng.normal(0, 1, (px, px)), sigma=px / 25)
    field = (field - field.mean()) / field.std()
    water = field > 1.3
    db = np.where(water, rng.normal(-22.0, 1.5, (px, px)), land)
    db = np.clip(db, -30, 5).astype("float32")
    return db, water.astype("uint8")


def write_tile(path: Path, arr: np.ndarray, lon0: int, lat0: int, dtype: str, nodata):
    px = arr.shape[0]
    transform = from_origin(lon0, lat0 + 1, 1.0 / px, 1.0 / px)
    with rasterio.open(
        path, "w", driver="GTiff", height=px, width=px, count=1, dtype=dtype,
        crs="EPSG:4326", transform=transform, nodata=nodata, compress="deflate",
    ) as dst:
        dst.write(arr, 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="data/raw", type=Path)
    ap.add_argument("--lon", type=int, default=83, help="SW corner longitude of the block (deg)")
    ap.add_argument("--lat", type=int, default=21, help="SW corner latitude of the block (deg)")
    ap.add_argument("--size", type=int, default=2, help="block is size x size one-degree tiles")
    ap.add_argument("--px", type=int, default=1000, help="pixels per tile side (real EOS-04 ~3333)")
    ap.add_argument("--seed", type=int, default=4)
    a = ap.parse_args()

    rng = np.random.default_rng(a.seed)
    a.out.mkdir(parents=True, exist_ok=True)
    for dx in range(a.size):
        for dy in range(a.size):
            lon0, lat0 = a.lon + dx, a.lat + dy
            db, water = synth_tile(lon0, lat0, a.px, rng)
            write_tile(a.out / f"sar_backscatter_db_{lon0}E_{lat0}N.tif", db, lon0, lat0, "float32", NODATA_DB)
            write_tile(a.out / f"water_spread_{lon0}E_{lat0}N.tif", water, lon0, lat0, "uint8", 255)
            print(f"wrote tiles for {lon0}E {lat0}N")


if __name__ == "__main__":
    main()
