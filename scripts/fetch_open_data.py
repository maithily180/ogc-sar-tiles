"""Fetch REAL open data (no login) for the demo AOI and write tiles into data/raw.

  * SAR backscatter: Sentinel-1 RTC (gamma0 VV) from Microsoft Planetary Computer (open, anonymous token).
    Sentinel-1 is among the missions Bhoonidhi lists as open data.
  * Water spread: JRC Global Surface Water 'occurrence' (Google Cloud public bucket), thresholded to a
    0/1 water class.

Produces a dry-season and a monsoon scene from the same relative orbit (so they overlay), plus the
water layer. Run build_layers.py afterwards. Defaults cover Hirakud reservoir, Odisha.
"""
import os

for _v in ("PROJ_LIB", "PROJ_DATA"):  # a system PROJ (e.g. PostGIS) can shadow rasterio's bundled proj.db
    os.environ.pop(_v, None)

import argparse
from pathlib import Path

import numpy as np
import rasterio
import requests
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds

PC = "https://planetarycomputer.microsoft.com/api"
JRC = ("https://storage.googleapis.com/global-surface-water/downloads2021/occurrence/"
       "occurrence_{lon}_{lat}v1_4_2021.tif")


def fetch_s1(bbox, datetime, out: Path, max_px: int, orbit: int = 19):
    r = requests.post(f"{PC}/stac/v1/search", timeout=60, json={
        "collections": ["sentinel-1-rtc"], "bbox": bbox, "datetime": datetime, "limit": 20,
        "query": {"sar:polarizations": {"eq": ["VV", "VH"]}, "sat:relative_orbit": {"eq": orbit}}})
    r.raise_for_status()
    items = r.json()["features"]
    if not items:
        raise SystemExit("no Sentinel-1 RTC scene for that bbox/date range")
    # prefer the scene that fully contains the bbox
    def covers(f):
        b = f["bbox"]
        return b[0] <= bbox[0] and b[1] <= bbox[1] and b[2] >= bbox[2] and b[3] >= bbox[3]
    item = next((f for f in items if covers(f)), items[0])
    tok = requests.get(f"{PC}/sas/v1/token/{item['collection']}", timeout=60).json()["token"]
    href = item["assets"]["vv"]["href"] + "?" + tok
    print("scene:", item["id"], item["properties"]["datetime"])
    with rasterio.open(href) as src:
        win = from_bounds(*transform_bounds("EPSG:4326", src.crs, *bbox), transform=src.transform)
        win = win.round_offsets().round_lengths()
        scale = max(1, int(max(win.width, win.height) // max_px))
        h, w = int(win.height // scale), int(win.width // scale)
        data = src.read(1, window=win, out_shape=(h, w), resampling=rasterio.enums.Resampling.average)
        transform = src.window_transform(win) * rasterio.Affine.scale(win.width / w, win.height / h)
        profile = dict(driver="GTiff", height=h, width=w, count=1, dtype="float32", crs=src.crs,
                       transform=transform, nodata=src.nodata, compress="deflate")
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out, "w", **profile) as dst:
        dst.write(data.astype("float32"), 1)
    print(f"wrote {out} ({w}x{h}px, linear gamma0; prepare_cogs.py converts to dB)")


def fetch_water(bbox, out: Path, threshold: int):
    lon = f"{int(bbox[0] // 10 * 10)}E"
    lat = f"{int(bbox[3] // 10 * 10 + 10)}N"
    url = JRC.format(lon=lon, lat=lat)
    with rasterio.open(url) as src:
        win = from_bounds(*bbox, transform=src.transform).round_offsets().round_lengths()
        occ = src.read(1, window=win)
        transform = src.window_transform(win)
        crs = src.crs
    water = (occ >= threshold).astype("uint8")
    water[occ == 255] = 0  # JRC nodata
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out, "w", driver="GTiff", height=water.shape[0], width=water.shape[1], count=1,
                       dtype="uint8", crs=crs, transform=transform, nodata=255, compress="deflate") as dst:
        dst.write(water, 1)
    print(f"wrote {out} ({water.shape[1]}x{water.shape[0]}px, water pixels: {int(water.sum())})")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bbox", nargs=4, type=float, default=[83.5, 21.2, 84.1, 21.8],
                    metavar=("W", "S", "E", "N"))
    ap.add_argument("--dry", default="2024-12-25/2024-12-26", help="dry-season acquisition date range")
    ap.add_argument("--wet", default="2024-08-27/2024-08-28", help="monsoon acquisition date range")
    ap.add_argument("--orbit", type=int, default=19, help="Sentinel-1 relative orbit (same for both dates)")
    ap.add_argument("--max-px", type=int, default=3000)
    ap.add_argument("--water-threshold", type=int, default=50, help="JRC occurrence %% treated as water")
    ap.add_argument("--out", type=Path, default=Path("data/real"))
    a = ap.parse_args()
    fetch_s1(a.bbox, a.dry, a.out / "s1_vv_dry.tif", a.max_px, a.orbit)
    fetch_s1(a.bbox, a.wet, a.out / "s1_vv_monsoon.tif", a.max_px, a.orbit)
    fetch_water(a.bbox, a.out / "water_spread_jrc.tif", a.water_threshold)


if __name__ == "__main__":
    main()
