# Gap analysis and verification log

Rubric question: *is the gap real, and is the justification convincing?* Evidence below is dated and
reproducible. Items marked **not verified** need a logged-in browser session.

## What Bhoonidhi offers today (checked 2026-10-11/12)

| Channel | What it gives | OGC data service? |
|---|---|---|
| Portal (cart download) | Whole-file download of open products, free registration | No |
| Bhoonidhi API | STAC search + `GET /download`; JWT login, API access enabled on request; 20 auth/h, 3 search/s, 500 results/query | No: STAC is discovery only |
| Vista viewer | Visual browsing of scenes | Internal, see below |
| Codelab | Hosted JupyterHub | No |

Sources: [API docs](https://bhoonidhi.nrsc.gov.in/bhoonidhi-api/),
[ISRO STAC overview (CEOS WGISS-58)](https://ceos.org/document_management/Working_Groups/WGISS/Meetings/WGISS-58/5.4_STACoverview_ISRO_SaiKalpana.pdf),
[Bhoonidhi brochure 2025](https://www.nrsc.gov.in/nrscnew/assets/pdf/brochures/Bhoonidhi_Brochure_2025.pdf).
Open products include EOS-04 water spread / NRB mosaics as 1°x1° tiles at ~33 m, AWiFS NDVI 10°x10° tiles, and
Sentinel-1/2, Landsat.

## Vista (the strongest counter-argument)

Vista's scripts (`https://bhoonidhi.nrsc.gov.in/vista/js/ajaxCalls.js`, `leafletExtend.js`) show that:

- layers come from `POST /vista/Vista` with `token` / `tokenuser` headers (login required);
- the response carries a `layerURL` + `layername`, which `addGeoLayerToMap()` loads as `L.TileLayer.WMS`.

So an **internal WMS exists behind a login**. This project does not claim "no tile service at all". The claim is:
there is no **public, documented, cacheable WMTS / OGC API - Tiles** service for the open products, so QGIS / web
maps / scripts cannot consume them without scraping an authenticated viewer.
**Not verified:** whether those WMS URLs work without a token (needs the browser Network tab while Vista loads data).

## Bhuvan (checked 2026-10-11)

- `bhuvan-vec1.nrsc.gov.in/bhuvan/gwc/service/wms?...GetCapabilities`: HTTP 200, ~5,100 layers.
- `bhuvan-vec2.nrsc.gov.in/bhuvan/wms?...GetCapabilities`: HTTP 200, ~3,800 layers.
- Case-insensitive search of layer names for `eos-04|eos-06|risat|sentinel|nrb|backscatter|sigma0|scansar|resourcesat`: **0 matches**
  in both. Matches for "water" are thematic vector layers (water bodies, watersheds).
- `bhuvan-vec1.nrsc.gov.in/bhuvan/gwc/service/wmts?REQUEST=GetCapabilities` returns **HTTP 400**
  ("Error searching max and min scale denominators for style ..."): the public WMTS capabilities document is broken.
- `bhuvan-ras1` returned 403 and `bhuvan-ras2` 404 for the same requests.

Bhuvan does publish many OGC services (WMS/WFS/WCS/WPS/CSW per
[OGC](https://www.ogc.org/bhuvan-transforming-indias-governance-with-geospatial-insights/)), but none found for
these SAR-derived Bhoonidhi products.

## Gap statement

> Open SAR-derived products distributed through Bhoonidhi are large tiled GeoTIFFs reachable only by login +
> whole-file download (STAC for discovery, no data service). The backscatter mosaic alone is ~555 MB per tile per date.
> Their only map view is an authenticated internal viewer. A developer cannot load them as a tile layer in QGIS or a
> web map. This project adds a standards-based, public, cached tile interface: WMTS 1.0.0 and OGC API - Tiles.

## Data used in this project

Real Bhoonidhi open data, downloaded through the portal cart (free registration): EOS-04 SAR MRS 1-degree tile
**N16E079** (Nagarjuna Sagar reservoir, Telangana / Andhra Pradesh), three 17-day cycles in 2026, two products each:

| Cycle | Dates | Water spread `J1G0WSHTD` (zip) | Backscatter mosaic `FIGC00ZTD` (zip) | Water pixels |
|---|---|---|---|---|
| 95 | 07-Aug to 23-Aug-2026 | 0.26 MB | 554.6 MB | 331,161 |
| 96 | 24-Aug to 09-Sep-2026 | 0.50 MB | 554.6 MB | 467,381 |
| 97 | 10-Sep to 26-Sep-2026 | 0.23 MB | 557.0 MB | 685,075 |

- **Water spread** (L3 GEOPHYSICAL-PARAMETER): 6112 x 6112 px EPSG:4326 GeoTIFF (~18 m, 9.35 MB unzipped), values
  0 land, 2 water, 3 background (see the `.meta`).
- **Backscatter** (`INDIA-MOSAIC-ARD`, the NRB India mosaic): HH and HV bands as 16-bit DN plus local incidence angle,
  area, date and mask rasters. `product.xml` documents Gamma-0 dB = `10*log10(DN^2) - 67.139999`, which the build script
  applies. Resulting HH medians sit near -8 dB over land and well below that over open water.

## Measured

Tiles needed to view the Nagarjuna Sagar area (79.0-79.5 E, 16.3-16.9 N, ~50 x 66 km) through the service
(PNG, EPSG:3857, measured 2026-10-12, `scripts/measure_tiles.py`):

| Zoom | Layers | Tiles | Water spread | HH backscatter |
|---|---|---|---|---|
| 9 | 1 date | 4 | 2.6 KB | 133 KB |
| 9 | 3 dates | 12 | 8.7 KB | 405 KB |
| 10 | 1 date | 6 | 4.7 KB | 291 KB |
| 10 | 3 dates | 18 | 17 KB | 885 KB |
| 11 | 1 date | 16 | 12.6 KB | 935 KB |
| 11 | 3 dates | 48 | 45 KB | 2.8 MB |

Versus downloading the products: the three backscatter zips are **1.59 GiB**; at zoom 10 the same area for the same
three dates is **0.9 MB of tiles, about 1,800 times less** (about 570 times less at zoom 11), and needs no unzipping,
georeferencing or styling. For water spread alone the saving is modest in absolute terms (three zips total ~1 MB);
there the gain is that **no GIS processing or format knowledge is needed** (the 0 / 2 / 3 coding is only in the
`.meta`), and that the data becomes consumable by any OGC client.
