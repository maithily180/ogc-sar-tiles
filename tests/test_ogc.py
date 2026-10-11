"""Live conformance smoke tests against the running service.

    BASE_URL=http://localhost:8080/geoserver pytest -v tests
"""
import os
import xml.etree.ElementTree as ET

import pytest
import requests
from owslib.wmts import WebMapTileService

BASE = os.getenv("BASE_URL", "http://localhost:8080/geoserver")
WMTS = f"{BASE}/gwc/service/wmts"
LAYERS = ["bhoonidhi:sar_dry_db", "bhoonidhi:sar_monsoon_db", "bhoonidhi:sar_change_db", "bhoonidhi:water_spread"]
NS = {"wmts": "http://www.opengis.net/wmts/1.0", "ows": "http://www.opengis.net/ows/1.1"}
# centre of the synthetic/real block; override for other data
LON, LAT = float(os.getenv("TEST_LON", 83.8)), float(os.getenv("TEST_LAT", 21.5))  # Hirakud demo AOI


def get(url, **kw):
    r = requests.get(url, timeout=60, **kw)
    return r


# ---------------- WMTS 1.0.0 ----------------
def test_wmts_getcapabilities():
    r = get(WMTS, params={"service": "WMTS", "request": "GetCapabilities", "version": "1.0.0"})
    assert r.status_code == 200
    root = ET.fromstring(r.content)
    assert root.tag.endswith("Capabilities")
    ids = {e.text for e in root.iterfind(".//wmts:Layer/ows:Identifier", NS)}
    for layer in LAYERS:
        assert layer in ids
    sets = {e.text for e in root.iterfind(".//wmts:TileMatrixSet/ows:Identifier", NS)}
    assert {"EPSG:3857", "EPSG:900913", "EPSG:4326"} <= sets


def test_wmts_owslib_parses():
    wmts = WebMapTileService(WMTS, version="1.0.0")
    assert set(LAYERS) <= set(wmts.contents)


@pytest.mark.parametrize("layer", LAYERS)
@pytest.mark.parametrize("gridset,z", [("EPSG:3857", 8), ("EPSG:900913", 6), ("EPSG:4326", 5)])
def test_wmts_gettile(layer, gridset, z):
    import math
    if gridset in ("EPSG:900913", "EPSG:3857"):
        n = 2 ** z
        col = int((LON + 180) / 360 * n)
        lat_r = math.radians(LAT)
        row = int((1 - math.asinh(math.tan(lat_r)) / math.pi) / 2 * n)
    else:  # GeoServer EPSG:4326 gridset: 2^(z+1) x 2^z tiles of 180/2^z degrees
        size = 180 / 2 ** z
        col, row = int((LON + 180) / size), int((90 - LAT) / size)
    r = get(WMTS, params={
        "service": "WMTS", "request": "GetTile", "version": "1.0.0", "layer": layer,
        "style": "", "format": "image/png", "tilematrixset": gridset,
        "tilematrix": f"{gridset}:{z}", "tilerow": row, "tilecol": col})
    assert r.status_code == 200, r.text[:300]
    assert r.headers["content-type"].startswith("image/png")
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_wmts_gettile_restful():
    r = get(f"{BASE}/gwc/service/wmts/rest/bhoonidhi:water_spread/EPSG:900913/EPSG:900913:10/449/750",
            params={"format": "image/png"})
    assert r.status_code == 200
    assert r.content[:4] == b"\x89PNG"


def test_wmts_getfeatureinfo():
    import math
    z, n = 6, 2 ** 6
    col = int((LON + 180) / 360 * n)
    row = int((1 - math.asinh(math.tan(math.radians(LAT))) / math.pi) / 2 * n)
    r = get(WMTS, params={
        "service": "WMTS", "request": "GetFeatureInfo", "version": "1.0.0",
        "layer": "bhoonidhi:sar_dry_db", "style": "", "format": "image/png",
        "infoformat": "application/json", "tilematrixset": "EPSG:900913",
        "tilematrix": f"EPSG:900913:{z}", "tilerow": row, "tilecol": col, "i": 128, "j": 128})
    assert r.status_code == 200, r.text[:300]


def test_wmts_exception_report():
    r = get(WMTS, params={"service": "WMTS", "request": "GetTile", "version": "1.0.0", "layer": "nope:nope"})
    assert r.status_code == 400
    assert "ExceptionReport" in r.text


# ---------------- OGC API - Tiles ----------------
API = f"{BASE}/ogc/tiles/v1"


def test_ogcapi_landing_and_conformance():
    r = get(API, params={"f": "application/json"})
    assert r.status_code == 200
    assert any(link["rel"].endswith("/conformance") for link in r.json()["links"])
    c = get(f"{API}/conformance", params={"f": "application/json"}).json()
    assert any("ogcapi-tiles" in u for u in c["conformsTo"])


def test_ogcapi_collections_and_tilesets():
    cols = get(f"{API}/collections", params={"f": "application/json"}).json()["collections"]
    ids = {c["id"] for c in cols}
    assert set(LAYERS) <= ids
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
    import math
    z, n = 6, 2 ** 6
    col = int((LON + 180) / 360 * n)
    row = int((1 - math.asinh(math.tan(math.radians(LAT))) / math.pi) / 2 * n)
    r = get(f"{API}/collections/{LAYERS[3]}/map/tiles/EPSG:900913/EPSG:900913:{z}/{row}/{col}",
            params={"f": "image/png"})
    assert r.status_code == 200
    assert r.content[:4] == b"\x89PNG"


def test_wmts_getfeatureinfo_returns_pixel_values():
    """Reservoir pixel must be water (1) and darker (lower dB) than the land pixel."""
    base = {"service": "WMTS", "request": "GetFeatureInfo", "version": "1.0.0", "style": "",
            "format": "image/png", "infoformat": "application/json", "tilematrixset": "EPSG:3857",
            "tilematrix": "EPSG:3857:10", "tilerow": 449, "tilecol": 750}

    def val(layer, i, j):
        r = get(WMTS, params={**base, "layer": layer, "i": i, "j": j})
        assert r.status_code == 200
        return r.json()["features"][0]["properties"]["GRAY_INDEX"]

    if os.getenv("DEMO_DATA") == "synthetic":
        pytest.skip("pixel positions are for the real Hirakud demo data")
    assert val("bhoonidhi:water_spread", 100, 60) == 1
    assert val("bhoonidhi:water_spread", 100, 180) == 0
    assert val("bhoonidhi:sar_dry_db", 100, 60) < val("bhoonidhi:sar_dry_db", 100, 180) - 3
    # change layer holds a monsoon-minus-dry difference, so values are small
    assert abs(val("bhoonidhi:sar_change_db", 100, 180)) < 15


# ---------------- WMS source + gateway ----------------
def test_wms_source_layer_getmap():
    r = get(f"{BASE}/bhoonidhi/wms", params={
        "service": "WMS", "version": "1.1.1", "request": "GetMap", "layers": LAYERS[3], "styles": "",
        "srs": "EPSG:4326", "bbox": "83.5,21.2,84.1,21.8", "width": 256, "height": 256, "format": "image/png"})
    assert r.status_code == 200 and r.content[:4] == b"\x89PNG"


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
