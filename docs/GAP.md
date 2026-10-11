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
> whole-file download (STAC for discovery, no data service). Their only map view is an authenticated internal
> viewer. A developer cannot load them as a tile layer in QGIS or a web map. This project adds a standards-based,
> public, cached tile interface: WMTS 1.0.0 and OGC API - Tiles.

## Honest scope note

The deployed demo uses Sentinel-1 RTC + JRC Global Surface Water (open, no login) because Bhoonidhi downloads need an
account; Bhoonidhi lists Sentinel-1 among its open missions. The identical pipeline ingests Bhoonidhi EOS-04 tiles.
**Not verified:** a run on actual EOS-04 files.
