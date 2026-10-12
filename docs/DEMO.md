# Live demo script (about 5 minutes)

Prereq: Docker Desktop running, `docker compose up -d`, `python scripts/publish.py` (GeoServer on :8080, gateway on :8081).

1. **Problem (30 s).** Bhoonidhi gives whole-file download of EOS-04 tiles (~555 MB per backscatter tile per date, 1.59 GiB
   for three dates) and a STAC search API. No tile endpoint a map can load. Show `docs/GAP.md`.
2. **WMTS capabilities (30 s).**
   `curl "http://localhost:8081/geoserver/gwc/service/wmts?service=WMTS&request=GetCapabilities&version=1.0.0"`
   Point out the layers (`bs_hh_c95..97`, `bs_hv_c95..97`, `ws_c95..97`, `wschange_c95_c97`) and the matrix sets EPSG:3857 / 900913 / 4326.
3. **GetTile (30 s).**
   `curl -o t.png "http://localhost:8081/geoserver/gwc/service/wmts?service=WMTS&request=GetTile&version=1.0.0&layer=bhoonidhi:wschange_c95_c97&style=&format=image/png&tilematrixset=EPSG:3857&tilematrix=EPSG:3857:10&tilerow=464&tilecol=737"`
4. **GetFeatureInfo (30 s).** A point that was land in cycle 95 and water in cycle 97 (79.179 E, 16.546 N) returns
   0 on `ws_c95`, 2 on `ws_c97`, 2 on `wschange_c95_c97` (water gained). See README for the request.
5. **QGIS (60 s).** Layer > Add Layer > WMTS: `http://localhost:8081/geoserver/gwc/service/wmts?REQUEST=GetCapabilities`;
   add `ws_c95`, `ws_c97` and the change layer; zoom to Nagarjuna Sagar.
6. **OGC API - Tiles (45 s).** `.../ogc/tiles/v1/collections?f=application/json`, a `map/tiles` tileset, then one tile.
7. **Web map (45 s).** `http://localhost:8081/demo/`: switch cycles, watch the reservoir fill, click for values.
8. **Safety (30 s).** `curl -i http://localhost:8081/geoserver/rest/workspaces.json` returns 403: admin and REST are never exposed.
9. **Tests (30 s).** `GATEWAY_URL=http://localhost:8081 pytest -q tests` (50 passing).
