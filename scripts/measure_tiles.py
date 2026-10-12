"""Measure how many bytes of tiles are needed to view an area, per zoom and number of layers.

    python scripts/measure_tiles.py --bbox 79.0 16.3 79.5 16.9
"""
import argparse
import math

import requests


def tiles(w, s, e, n, z):
    N = 2 ** z
    row = lambda lat: int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * N)
    return [(r, c) for r in range(row(n), row(s) + 1)
            for c in range(int((w + 180) / 360 * N), int((e + 180) / 360 * N) + 1)]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="http://localhost:8080/geoserver")
    ap.add_argument("--bbox", nargs=4, type=float, default=[79.0, 16.3, 79.5, 16.9], metavar=("W", "S", "E", "N"))
    ap.add_argument("--layers", nargs="+", default=["ws_c95", "ws_c96", "ws_c97"])
    ap.add_argument("--zooms", nargs="+", type=int, default=[9, 10, 11])
    a = ap.parse_args()
    for z in a.zooms:
        for layers in ([a.layers[-1]], a.layers):
            total, n = 0, 0
            for layer in layers:
                for r, c in tiles(*a.bbox, z):
                    resp = requests.get(f"{a.base}/gwc/service/wmts", timeout=60, params={
                        "service": "WMTS", "request": "GetTile", "version": "1.0.0", "layer": f"bhoonidhi:{layer}",
                        "style": "", "format": "image/png", "tilematrixset": "EPSG:3857",
                        "tilematrix": f"EPSG:3857:{z}", "tilerow": r, "tilecol": c})
                    resp.raise_for_status()
                    total += len(resp.content)
                    n += 1
            print(f"z{z} layers={len(layers)} tiles={n} bytes={total} ({total / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
