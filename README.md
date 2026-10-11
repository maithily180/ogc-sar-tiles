# SAR Tiles over OGC WMTS and OGC API – Tiles

A standards-based tile service (**WMTS 1.0.0** and **OGC API – Tiles**) for SAR-derived raster products,
built on GeoServer + GeoWebCache, aimed at the gap in ISRO's [Bhoonidhi](https://bhoonidhi.nrsc.gov.in) open data.
Mid-Sem practical, CyberGIS (M26GS2.402).

![Dry, monsoon, change and water layers served as WMTS tiles](docs/tiles_overview.png)

*Clockwise from top-left: SAR VV dry season, SAR VV monsoon, water spread (JRC), change (monsoon minus dry; blue =
darker = more open water). Hirakud reservoir and the Mahanadi, Odisha. All four are tiles fetched through WMTS.*

> **Data status:** the demo serves **real open data with no login**: Sentinel-1 RTC backscatter (a mission Bhoonidhi
> lists as open data) and JRC Global Surface Water. Bhoonidhi's EOS-04 tiles need a Bhoonidhi account to download; the
> same pipeline ingests them (not yet run on EOS-04 files). See [docs/GAP.md](docs/GAP.md).

## 1. Gap identified

| Today | Missing |
|---|---|
| Portal: cart + whole-file download | A tile endpoint QGIS / a web map can load |
| API: STAC search + `GET /download`, login, rate limits | Any WMTS / OGC API – Tiles / WCS / WFS on open products |
| Vista viewer: browsing inside the portal | A public, documented, cacheable standards endpoint |

- Open EOS-04 products (NRB mosaic, water spread) are **1°×1° GeoTIFF tiles at ~33 m**; to view an area a user
  downloads many large files and styles them locally.
- The Bhoonidhi API is STAC discovery + download; no OGC data service
  ([API docs](https://bhoonidhi.nrsc.gov.in/bhoonidhi-api/)).
- **Counter-evidence, stated openly:** Vista's own scripts load imagery as WMS, with layer URLs returned by an
  authenticated backend (`POST /vista/Vista`). So an *internal* WMS exists; what is missing is a **public, documented,
  cacheable WMTS / OGC API – Tiles**.
- Bhuvan: ~8,900 WMS layers checked, **0** SAR/EOS/Sentinel layers; its WMTS `GetCapabilities` returned HTTP 400
  on 2026-10-11.

Full dated evidence and what is **not verified** (Vista URLs without a token): [docs/GAP.md](docs/GAP.md).

## 2. Service design

```
Sentinel-1 / JRC (or Bhoonidhi tiles) --fetch + build_layers.py--> COGs (data/cogs)
        COGs --publish.py (REST)--> GeoServer --> WMS (source)
                                             |--> GeoWebCache --> WMTS 1.0.0
                                             '--> ogcapi-tiles --> OGC API - Tiles
        nginx gateway :8081 (read-only: WMTS / tiles / WMS / demo page only)
```

| Layer (`bhoonidhi:`) | Content | Style |
|---|---|---|
| `sar_dry_db` | Sentinel-1 VV, 25 Dec 2024, dB | grayscale -25..0 dB |
| `sar_monsoon_db` | Sentinel-1 VV, 27 Aug 2024, dB (same orbit) | grayscale |
| `sar_change_db` | monsoon − dry, dB | blue–white–red, ±6 dB |
| `water_spread` | JRC occurrence ≥ 50% → class 0/1 | transparent land, blue water |

Layers are declared in [layers.json](layers.json).

**Implemented operations** (all covered by `tests/test_ogc.py`, **28 passing**)

- **WMTS 1.0.0:** `GetCapabilities`, `GetTile` (KVP and RESTful), `GetFeatureInfo` (returns pixel values: about −19 dB
  in the reservoir, −8 dB on land); tile matrix sets `EPSG:3857`, `EPSG:900913` (legacy alias) and `EPSG:4326`;
  `image/png`, `image/jpeg`; OGC exception reports on bad requests.
- **OGC API – Tiles** (GeoServer community module): landing page, `/conformance`, `/collections`,
  `/collections/{id}/map/tiles` (raster layers are *map* tilesets), `/tileMatrixSets`,
  `/collections/{id}/map/tiles/{tmsId}/{tileMatrix}/{row}/{col}`.
- **WMS 1.1.1/1.3.0** `GetMap` on the source layers (GeoServer built-in).

## 3. Implementation choices

- **GeoServer + GeoWebCache:** reference WMTS and tile caching; SLD styling.
- **COG inputs:** internal tiling and overviews; nearest-neighbour overviews for the class layer, bilinear for dB.
- **Docker Compose:** one command; the `ogcapi-tiles` community module installs at start-up.
- **Idempotent REST publishing:** `publish.py` recreates stores so bounds and CRS follow the data (stale config
  otherwise broke `GetFeatureInfo`).
- **Read-only gateway (nginx):** the admin UI, REST and GWC REST are never exposed; only GET/HEAD on tile/WMS paths.

## 4. Run it

```bash
pip install -r requirements.txt
python scripts/fetch_open_data.py            # Sentinel-1 dry + monsoon, JRC water -> data/real (no login)
python scripts/build_layers.py               # -> data/cogs/*.tif
docker compose up -d                          # GeoServer :8080 (first start installs extensions), gateway :8081
python scripts/publish.py                     # styles, layers, EPSG:3857 gridset, tile cache
GATEWAY_URL=http://localhost:8081 pytest -v tests
```

Then open `http://localhost:8081/demo/` or, in QGIS, add a WMTS connection to
`http://localhost:8081/geoserver/gwc/service/wmts?REQUEST=GetCapabilities`.

```bash
B=http://localhost:8081/geoserver
curl "$B/gwc/service/wmts?service=WMTS&request=GetCapabilities&version=1.0.0"
curl -o tile.png "$B/gwc/service/wmts?service=WMTS&request=GetTile&version=1.0.0&layer=bhoonidhi:sar_change_db&style=&format=image/png&tilematrixset=EPSG:3857&tilematrix=EPSG:3857:10&tilerow=449&tilecol=750"
curl "$B/gwc/service/wmts?service=WMTS&request=GetFeatureInfo&version=1.0.0&layer=bhoonidhi:sar_dry_db&style=&format=image/png&infoformat=application/json&tilematrixset=EPSG:3857&tilematrix=EPSG:3857:10&tilerow=449&tilecol=750&i=100&j=60"
curl "$B/ogc/tiles/v1/collections?f=application/json"
curl -o t2.png "$B/ogc/tiles/v1/collections/bhoonidhi:water_spread/map/tiles/EPSG:900913/EPSG:900913:10/449/750?f=image/png"
```

Demo script: [docs/DEMO.md](docs/DEMO.md). Change the area with `--bbox W S E N` (Sentinel-1 orbit with `--orbit`).

## 5. Using real Bhoonidhi EOS-04 data

Register (free), download the water-spread and backscatter tiles, put them in `data/raw/`, then mosaic and convert:
`python scripts/prepare_cogs.py --glob "data/raw/<tiles>*.tif" --out data/cogs/<layer>.tif --kind continuous|categorical`
(add `--dn-to-db --scale <gain> --offset <offset>` for linear intensity), and list the layer in `layers.json`.
`scripts/make_sample_data.py` generates a synthetic fallback.

## 6. Known limitations

- Demo data is Sentinel-1 + JRC; the EOS-04 path is built but **not yet exercised on EOS-04 files**.
- OGC API – Tiles in GeoServer is a **community module** (nightly builds); behaviour can change between releases.
- Raster only; values only through `GetFeatureInfo`; no time dimension (dates are separate layers); two scenes only.
- The first request at a new zoom renders on demand (cache not pre-seeded).
- Behind an HTTPS tunnel, GeoServer-generated OGC API links may use `http://`; WMTS URLs are unaffected.
- Whether Vista's WMS works without login is not verified (needs a browser).
