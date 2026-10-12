"""Build the published COG layers from Bhoonidhi EOS-04 product zips.

Put the downloaded zips (or already extracted folders) in data/bhoonidhi/ and run:

    python scripts/build_bhoonidhi_layers.py

Per EOS-04 SAR MRS 1-degree tile and cycle it writes data/cogs/<layer>.tif and regenerates layers.json:
  * ws_c<cycle>            WATER-SPREAD product (J1G0WSHTD): 0 land, 2 water, 3 background
  * bs_hh_c<cycle>, bs_hv_c<cycle>
                           INDIA-MOSAIC-ARD backscatter (FIGC00ZTD), Gamma-0 in dB. The product's own
                           product.xml gives the conversion: 10*log10(DN^2) - 67.139999
  * wschange_c<a>_c<b>     derived: water change between the first and last cycle
                           (1 stable water, 2 gained, 3 lost)
"""
import os

for _v in ("PROJ_LIB", "PROJ_DATA"):  # a system PROJ (e.g. PostGIS) can shadow rasterio's bundled proj.db
    os.environ.pop(_v, None)

import argparse
import json
import re
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.shutil import copy as rio_copy

WATER_ND = 3        # ImageBackground in the water-spread meta
CHANGE_ND = 255
DB_ND = -9999.0
DEFAULT_CAL = 67.139999   # used only if product.xml has no BackscatterConversionEq


def read_meta(path: Path) -> dict:
    out = {}
    for line in path.read_text(errors="replace").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def discover(root: Path):
    """Extract zips next to themselves; return [(meta, product_dir, stem)] for every product with a .meta file."""
    for z in sorted(root.glob("*.zip")):
        d = root / z.stem
        if not d.exists():
            print(f"unzipping {z.name} ...")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(d)
    prods = []
    for meta in sorted(root.rglob("*.meta")):
        prods.append((read_meta(meta), meta.parent, meta.stem))
    return prods


def calibration_constant(prod_dir: Path) -> float:
    """Parse '10*log10(DN^2) - 67.139999' from the product's own product.xml."""
    xml = prod_dir / "product.xml"
    if xml.exists():
        m = re.search(r"BackscatterConversionEq[^>]*>\s*10\*log10\(DN\^2\)\s*-\s*([0-9.]+)",
                      xml.read_text(errors="replace"))
        if m:
            return float(m.group(1))
    return DEFAULT_CAL


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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, default=Path("data/bhoonidhi"))
    ap.add_argument("--out", type=Path, default=Path("data/cogs"))
    ap.add_argument("--manifest", type=Path, default=Path("layers.json"))
    ap.add_argument("--pols", nargs="+", default=["HH", "HV"], help="backscatter polarisations to publish")
    a = ap.parse_args()

    prods = discover(a.src)
    if not prods:
        raise SystemExit(f"no products found in {a.src}")
    layers, water = [], {}

    for meta, pdir, stem in sorted(prods, key=lambda p: (int(p[0]["Cycle_Number"]), p[0].get("ProdCode", ""))):
        cyc = int(meta["Cycle_Number"])
        code = meta.get("ProdCode", "")
        label = f"cycle {cyc}, {meta['StartDate']} to {meta['EndDate']}"
        if code == "J1G0WSHTD":                      # water spread
            with rasterio.open(pdir / f"{stem}.tif") as src:
                arr, profile = src.read(1), src.profile.copy()
            water[cyc] = (arr, profile)
            name = f"ws_c{cyc}"
            write_cog(a.out / f"{name}.tif", arr, profile, WATER_ND, "NEAREST")
            layers.append({"name": name, "file": f"{name}.tif", "style": "water_class",
                           "title": f"EOS-04 water spread, {label}",
                           "abstract": f"ISRO EOS-04 SAR MRS water-spread product, tile {meta['TileId']}, {label}. "
                                       "0 land, 2 water, 3 background. Source: Bhoonidhi."})
        elif code == "FIGC00ZTD":                    # NRB / ARD India mosaic
            cal = calibration_constant(pdir)
            for pol in a.pols:
                tif = pdir / f"{stem}_{pol}.tif"
                if not tif.exists():
                    print(f"skip {tif.name}: not found")
                    continue
                with rasterio.open(tif) as src:
                    dn, profile = src.read(1).astype("float32"), src.profile.copy()
                ok = dn > 0
                db = np.full(dn.shape, DB_ND, "float32")
                db[ok] = 10 * np.log10(dn[ok] ** 2) - cal
                name = f"bs_{pol.lower()}_c{cyc}"
                write_cog(a.out / f"{name}.tif", db, profile, DB_ND, "BILINEAR")
                layers.append({"name": name, "file": f"{name}.tif",
                               "style": "sar_backscatter_db" if pol == "HH" else "sar_hv_db",
                               "title": f"EOS-04 {pol} backscatter (dB), {label}",
                               "abstract": f"ISRO EOS-04 SAR MRS India mosaic (ARD), {pol} Gamma-0 in dB = "
                                           f"10*log10(DN^2) - {cal}, tile {meta['TileId']}, {label}. "
                                           "Source: Bhoonidhi."})
        else:
            print(f"skipping {stem}: unknown product code {code}")

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
                                   f"cycle {c0} and cycle {c1}."})
        print(f"change c{c0}->c{c1}: stable={int((ch == 1).sum())} gained={int((ch == 2).sum())} "
              f"lost={int((ch == 3).sum())}")

    a.manifest.write_text(json.dumps({"workspace": "bhoonidhi", "layers": layers}, indent=2), encoding="utf-8")
    print(f"wrote {a.manifest} with {len(layers)} layers")


if __name__ == "__main__":
    main()
