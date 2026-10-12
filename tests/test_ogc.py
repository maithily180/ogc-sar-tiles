"""Live conformance smoke tests against the running service.

    BASE_URL=http://localhost:8080/geoserver pytest -v tests
    GATEWAY_URL=http://localhost:8081 pytest -v tests        # also tests the read-only gateway
"""
import math
import os
import xml.etree.ElementTree as ET

import pytest
import requests
from owslib.wmts import WebMapTileService

BASE = os.getenv("BASE_URL", "http://localhost:8080/geoserver")
WMTS = f"{BASE}/gwc/service/wmts"
API = f"{BASE}/ogc/tiles/v1"
LAYERS = ["bhoonidhi:ws_c95", "bhoonidhi:ws_c96", "bhoonidhi:ws_c97", "bhoonidhi:wschange_c95_c97",
          "bhoonidhi:bs_hh_c95", "bhoonidhi:bs_hh_c96", "bhoonidhi:bs_hh_c97",
          "bhoonidhi:bs_hv_c95", "bhoonidhi:bs_hv_c96", "bhoonidhi:bs_hv_c97"]
NS = {"wmts": "http://www.opengis.net/wmts/1.0", "ows": "http://www.opengis.net/ows/1.1"}
PNG = b"\x89PNG"

# Nagarjuna Sagar demo AOI (EOS-04 tile N16E079). Points checked against the data:
LON, LAT = 79.2, 16.6
WATER_PT = (79.22292, 16.96458)     # open water in cycles 95 and 97
GAINED_PT = (79.17907, 16.54638)    # land in cycle 95, water in cycle 97
LAND_PT = (79.8, 16.2)


def get(url, **kw):
    return requests.get(url, timeout=60, **kw)


def tile_3857(lon, lat, z):
    """lon/lat -> (row, col, i, j) in the EPSG:3857 tile matrix at zoom z (256 px tiles)."""
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return int(y), int(x), int((x % 1) * 256), int((y % 1) * 256)   # (row, col, i = x pixel, j = y pixel)


def tile_4326(lon, lat, z):
    size = 180 / 2 ** z   # GeoServer EPSG:4326 gridset: 2^(z+1) x 2^z tiles of 180/2^z degrees
    return int((90 - lat) / size), int((lon + 180) / size)


def gettile_params(layer, gridset, z, row, col):
    return {"service": "WMTS", "request": "GetTile", "version": "1.0.0", "layer": layer, "style": "",
            "format": "image/png", "tilematrixset": gridset, "tilematrix": f"{gridset}:{z}",
            "tilerow": row, "tilecol": col}


# ---------------- WMTS 1.0.0 ----------------
def test_wmts_getcapabilities():
    r = get(WMTS, params={"service": "WMTS", "request": "GetCapabilities", "version": "1.0.0"})
    assert r.status_code == 200
    root = ET.fromstring(r.content)
    assert root.tag.endswith("Capabilities")
    ids = {e.text for e in root.iterfind(".//wmts:Layer/ows:Identifier", NS)}
    assert set(LAYERS) <= ids
    sets = {e.text for e in root.iterfind(".//wmts:TileMatrixSet/ows:Identifier", NS)}
    assert {"EPSG:3857", "EPSG:900913", "EPSG:4326"} <= sets


def test_wmts_owslib_parses():
    wmts = WebMapTileService(WMTS, version="1.0.0")
    assert set(LAYERS) <= set(wmts.contents)


@pytest.mark.parametrize("layer", LAYERS)
@pytest.mark.parametrize("gridset,z", [("EPSG:3857", 10), ("EPSG:900913", 9), ("EPSG:4326", 6)])
def test_wmts_gettile(layer, gridset, z):
    if gridset == "EPSG:4326":
        row, col = tile_4326(LON, LAT, z)
    else:
        row, col, _, _ = tile_3857(LON, LAT, z)
    r = get(WMTS, params=gettile_params(layer, gridset, z, row, col))
    assert r.status_code == 200, r.text[:300]
    assert r.headers["content-type"].startswith("image/png")
    assert r.content[:4] == PNG


def test_wmts_gettile_restful():
    row, col, _, _ = tile_3857(LON, LAT, 10)
    r = get(f"{BASE}/gwc/service/wmts/rest/bhoonidhi:ws_c97/EPSG:900913/EPSG:900913:10/{row}/{col}",
            params={"format": "image/png"})
    assert r.status_code == 200
    assert r.content[:4] == PNG


def fi(layer, lon, lat, z=14):
    row, col, i, j = tile_3857(lon, lat, z)
    r = get(WMTS, params={
        "service": "WMTS", "request": "GetFeatureInfo", "version": "1.0.0", "layer": layer, "style": "",
        "format": "image/png", "infoformat": "application/json", "tilematrixset": "EPSG:3857",
        "tilematrix": f"EPSG:3857:{z}", "tilerow": row, "tilecol": col, "i": i, "j": j})
    assert r.status_code == 200, r.text[:300]
    feats = r.json()["features"]
    return feats[0]["properties"]["GRAY_INDEX"] if feats else None


STEP = 0.00009  # ~10 m, about one zoom-14 tile pixel


def frac(layer, pt, value, n=2):
    """Share of a (2n+1)^2 sample grid around pt whose GetFeatureInfo value equals `value`.

    The SAR water mask is speckled, so single pixels flip; a neighbourhood fraction is the stable check."""
    vals = [fi(layer, pt[0] + dx * STEP, pt[1] + dy * STEP)
            for dx in range(-n, n + 1) for dy in range(-n, n + 1)]
    return sum(v == value for v in vals) / len(vals)


def test_wmts_getfeatureinfo_water_values():
    """EOS-04 water spread coding: 2 = water, 0 = land."""
    assert frac("bhoonidhi:ws_c97", WATER_PT, 2) >= 0.5
    assert frac("bhoonidhi:ws_c95", WATER_PT, 2) >= 0.5
    assert frac("bhoonidhi:ws_c97", LAND_PT, 0) >= 0.9


def test_wmts_getfeatureinfo_change_layer():
    """The reservoir filled between cycle 95 and 97, so the gained point is mostly land -> water."""
    assert frac("bhoonidhi:ws_c95", GAINED_PT, 0) >= 0.5
    assert frac("bhoonidhi:ws_c97", GAINED_PT, 2) >= 0.5
    assert frac("bhoonidhi:wschange_c95_c97", GAINED_PT, 2) >= 0.5   # class 2 = water gained
    assert frac("bhoonidhi:wschange_c95_c97", WATER_PT, 1) >= 0.3    # class 1 = stable water


def mean_value(layer, pt, n=2):
    vals = [fi(layer, pt[0] + dx * STEP, pt[1] + dy * STEP)
            for dx in range(-n, n + 1) for dy in range(-n, n + 1)]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals)


@pytest.mark.parametrize("layer", ["bhoonidhi:bs_hh_c95", "bhoonidhi:bs_hh_c96", "bhoonidhi:bs_hh_c97",
                                   "bhoonidhi:bs_hv_c97"])
def test_wmts_getfeatureinfo_backscatter_db(layer):
    """Gamma-0 in dB: open water (specular) is much darker than land, and values are plausible dB."""
    water, land = mean_value(layer, WATER_PT), mean_value(layer, LAND_PT)
    assert -35 < water < 0 and -35 < land < 0
    assert water < land - 4


def test_wmts_exception_report():
    r = get(WMTS, params={"service": "WMTS", "request": "GetTile", "version": "1.0.0", "layer": "nope:nope"})
    assert r.status_code == 400
    assert "ExceptionReport" in r.text


# ---------------- OGC API - Tiles ----------------
def test_ogcapi_landing_and_conformance():
    r = get(API, params={"f": "application/json"})
    assert r.status_code == 200
    assert any(link["rel"].endswith("/conformance") for link in r.json()["links"])
    c = get(f"{API}/conformance", params={"f": "application/json"}).json()
    assert any("ogcapi-tiles" in u for u in c["conformsTo"])


def test_ogcapi_collections_and_tilesets():
    cols = get(f"{API}/collections", params={"f": "application/json"}).json()["collections"]
    assert set(LAYERS) <= {c["id"] for c in cols}
    # raster layers are advertised as *map* tilesets (OGC API - Tiles, map tiles)
    ts = get(f"{API}/collections/{LAYERS[0]}/map/tiles", params={"f": "application/json"})
    assert ts.status_code == 200
    assert {t["dataType"] for t in ts.json()["tilesets"]} == {"map"}


def test_ogcapi_tilematrixsets():
    r = get(f"{API}/tileMatrixSets", params={"f": "application/json"})
    assert r.status_code == 200
    ids = {t["id"] for t in r.json()["tileMatrixSets"]}
    assert {"WebMercatorQuad", "EPSG:900913", "EPSG:4326"} <= ids


def test_ogcapi_tile():
    row, col, _, _ = tile_3857(LON, LAT, 10)
    r = get(f"{API}/collections/{LAYERS[2]}/map/tiles/EPSG:900913/EPSG:900913:10/{row}/{col}",
            params={"f": "image/png"})
    assert r.status_code == 200
    assert r.content[:4] == PNG


# ---------------- WMS source + gateway ----------------
def test_wms_source_layer_getmap():
    r = get(f"{BASE}/bhoonidhi/wms", params={
        "service": "WMS", "version": "1.1.1", "request": "GetMap", "layers": LAYERS[2], "styles": "",
        "srs": "EPSG:4326", "bbox": "79.0,16.0,80.0,17.0", "width": 256, "height": 256, "format": "image/png"})
    assert r.status_code == 200 and r.content[:4] == PNG


GATEWAY = os.getenv("GATEWAY_URL")  # e.g. http://localhost:8081 (read-only proxy used for public exposure)


@pytest.mark.skipif(not GATEWAY, reason="set GATEWAY_URL to test the read-only gateway")
@pytest.mark.parametrize("path", ["/geoserver/web/", "/geoserver/rest/workspaces.json",
                                  "/geoserver/gwc/rest/layers", "/geoserver/j_spring_security_check"])
def test_gateway_blocks_admin(path):
    assert requests.get(GATEWAY + path, timeout=30).status_code in (403, 404)


@pytest.mark.skipif(not GATEWAY, reason="set GATEWAY_URL to test the read-only gateway")
def test_gateway_serves_wmts_and_blocks_writes():
    ok = requests.get(GATEWAY + "/geoserver/gwc/service/wmts",
                      params={"service": "WMTS", "request": "GetCapabilities", "version": "1.0.0"}, timeout=30)
    assert ok.status_code == 200
    assert requests.post(GATEWAY + "/geoserver/gwc/service/wmts", timeout=30).status_code in (403, 405)
