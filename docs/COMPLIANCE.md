# OGC compliance evidence

Checked against the live service on 2026-10-12. "Tested" means a passing case in `tests/test_ogc.py`.
No official OGC CITE / TEAM Engine run was done; this is spec-driven checking plus schema validation.

## WMTS 1.0.0 (OGC 07-057r7)

| Requirement | Evidence |
|---|---|
| `GetCapabilities` returns a Capabilities document | `ServiceType OGC WMTS 1.0.0`, version `1.0.0`; operations advertised: GetCapabilities, GetTile, GetFeatureInfo. Tested. |
| Capabilities validates against the OGC schema | Validated with lxml against `schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd`. **180 errors, all one pattern:** `MaxTileRow` / `MaxTileCol` = `0` where the XSD types them `xs:positiveInteger` (single-tile levels). No structural or missing-element errors. Treated as an implementation/schema mismatch in GeoServer/GeoWebCache, not fixable here. |
| `GetTile`, KVP encoding | Tested for 10 layers x EPSG:3857, EPSG:900913, EPSG:4326 (30 cases). |
| `GetTile`, RESTful encoding | Tested. |
| `GetFeatureInfo` | Tested: returns `GRAY_INDEX` class values (0 / 2 for water spread; 1 / 2 / 3 for the change layer); formats `text/plain`, `application/vnd.ogc.gml`, `text/xml`, `application/json`. |
| Tile matrix sets | `EPSG:3857` (25 levels, `urn:ogc:def:crs:EPSG::3857`), `EPSG:4326` (22 levels), and the legacy `EPSG:900913`. Tested. |
| Exceptions | Bad request returns HTTP 400 with an OGC `ExceptionReport`. Tested. |
| Client interoperability | Parsed by OWSLib `WebMapTileService`. Tested. QGIS not tested in this environment. |

## OGC API – Tiles Part 1 (OGC 20-057), GeoServer `ogcapi-tiles` module

`/ogc/tiles/v1/conformance` declares: `ogcapi-common-1 core`, `ogcapi-common-2 collections`,
`ogcapi-tiles-1 core, tileset, tilesets, tilesets-list, geodata-tilesets, info, tmxs`,
`tilematrixset core, json-tilematrixset`.

| Requirement | Evidence |
|---|---|
| Landing page with `conformance` and `data` links | Tested. |
| `/conformance` lists tiles classes | Tested. |
| `/collections` lists all ten layers | Tested. |
| Tilesets per collection | `/collections/{id}/map/tiles` lists tilesets with `dataType: map`. Tested. |
| Tile matrix sets | `/tileMatrixSets` includes WebMercatorQuad, EPSG:900913, EPSG:4326. Tested. |
| Tile retrieval | `/collections/{id}/map/tiles/{tmsId}/{tileMatrix}/{row}/{col}` returns PNG. Tested. |

Caveats: raster layers are exposed as *map* tilesets under `/map/tiles` (this is how the module models them), which
differs from the `/tiles/...` path written in the original proposal. The module is a GeoServer **community** module.
It does not declare the format conformance classes (`png`, `jpeg`) even though it serves them.

## Beyond the two standards
WMS `GetMap` on the source layers (GeoServer built-in), tested.

## Not done
- Official CITE (TEAM Engine) run for WMTS / OGC API – Tiles.
- QGIS and a second independent client test.
