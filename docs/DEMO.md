# Live demo script (about 5 minutes)

Prereq: `docker compose up -d`, `python scripts/publish.py`. Service on :8080 (direct) and :8081 (read-only gateway).

1. **Problem (30 s).** Show Bhoonidhi: cart download only; STAC API = search + download. Show `docs/GAP.md` findings.
2. **WMTS capabilities (30 s).**
   `curl "http://localhost:8081/geoserver/gwc/service/wmts?service=WMTS&request=GetCapabilities&version=1.0.0"`
   Point out 4 layers and tile matrix sets EPSG:3857 / EPSG:900913 / EPSG:4326.
3. **GetTile (30 s).** Save a tile:
   `curl -o t.png "http://localhost:8081/geoserver/gwc/service/wmts?service=WMTS&request=GetTile&version=1.0.0&layer=bhoonidhi:sar_change_db&style=&format=image/png&tilematrixset=EPSG:3857&tilematrix=EPSG:3857:10&tilerow=449&tilecol=750"`
4. **GetFeatureInfo (30 s).** Reservoir vs land values (see README commands): about -19 dB vs -8 dB; water layer 1 vs 0.
5. **QGIS (60 s).** Layer > Add Layer > WMTS: `http://localhost:8081/geoserver/gwc/service/wmts?REQUEST=GetCapabilities`;
   add `sar_dry_db`, then `sar_change_db` on top.
6. **OGC API - Tiles (45 s).** `.../ogc/tiles/v1/collections?f=application/json`, then a `map/tiles` tileset and one tile.
7. **Web map (45 s).** Open `http://localhost:8081/demo/`: toggle dry / monsoon / change / water, click for values.
8. **Safety (30 s).** `curl -i http://localhost:8081/geoserver/rest/workspaces.json` returns 403: admin and REST are never exposed.
9. **Tests (30 s).** `GATEWAY_URL=http://localhost:8081 pytest -q tests` (28 passing).
