# Live demo, step by step (copy and paste)

Everything below was tested on this machine (Windows, PowerShell). Total demo time: about 6 minutes.
Lines starting with `PS>` are things you **type or paste into PowerShell**. Lines starting with **SAY:** are what to
tell the examiner. **YOU SEE:** is what should appear. If it does not, go to [Part D](#part-d-if-something-goes-wrong).

---

## Part A. Get ready (do this 10 minutes BEFORE the demo)

**A1.** Open **Docker Desktop** (Start menu). Wait until the bottom-left says "Engine running".

**A2.** Open **PowerShell** (Start menu, type `PowerShell`). Paste:

```powershell
cd "C:\Users\maith\Downloads\cyberGIS_midsem\bhoonidhi-sar-tiles"
docker compose up -d
```

**A3.** Wait 1 to 2 minutes, then paste:

```powershell
docker ps --format "{{.Names}}  {{.Status}}"
```

**YOU SEE:** two lines, `bhoonidhi-geoserver  Up ... (healthy)` and `bhoonidhi-gateway  Up ...`.
If it says `(health: starting)`, wait another minute and run the same command again.

**A4.** Check that all tests pass:

```powershell
$env:GATEWAY_URL = "http://localhost:8081"
python -m pytest -q tests
```

**YOU SEE:** `50 passed` (takes about 30 seconds). If you see failures, jump to Part D.

**A5.** Set a shortcut that the demo commands use (paste it once; **do this in the same PowerShell window you will use for the demo**):

```powershell
$B = "http://localhost:8081/geoserver"
cd "C:\Users\maith\Downloads\cyberGIS_midsem\bhoonidhi-sar-tiles"
cls
```

**A6.** Open these browser tabs, in this order, and leave them open:

1. `https://github.com/maithily180/ogc-sar-tiles` (the repo and README)
2. `https://github.com/maithily180/ogc-sar-tiles/blob/main/docs/GAP.md` (the gap evidence)
3. `http://localhost:8081/demo/` (the web map)
4. `https://bhoonidhi.nrsc.gov.in` (optional, to show the portal)

**A7.** (Optional but recommended) Open **QGIS** and leave it open on an empty project.

Do **not** run `docker compose down`. If you need to stop, use `docker compose stop`.

---

## Part B. The demo

### Step 1. The problem (about 45 s) *(browser tab 2, GAP.md)*

Scroll to the "Data used in this project" table and the "Measured" table.

**SAY:** "Bhoonidhi distributes EOS-04 SAR products as whole-tile zip downloads. The backscatter mosaic is about
555 MB per tile per date, so 1.6 GB for three dates. There is a STAC API, but it only does search and download.
Its map viewer, Vista, is inside the portal. There is no tile service that QGIS or a web map can load.
I built one, using WMTS and OGC API – Tiles on GeoServer."

### Step 2. The service advertises itself: WMTS GetCapabilities (about 30 s)

```powershell
curl.exe -s "$B/gwc/service/wmts?service=WMTS&request=GetCapabilities&version=1.0.0" | Select-String -Pattern "<ows:Identifier>bhoonidhi:" | ForEach-Object { $_.Line.Trim() }
```

**YOU SEE:** 10 lines: `bhoonidhi:bs_hh_c95`, `bs_hh_c96`, `bs_hh_c97`, `bs_hv_c95` ..., `ws_c95` ..., `wschange_c95_c97`.

**SAY:** "GetCapabilities lists ten layers: HH and HV backscatter in dB for three 17-day cycles, the water-spread
product for the same cycles, and a derived water-change layer. It also advertises the tile matrix sets."

Now show the tile matrix sets:

```powershell
curl.exe -s "$B/gwc/service/wmts?service=WMTS&request=GetCapabilities&version=1.0.0" | Select-String -Pattern "<ows:Identifier>EPSG:[0-9]+</ows:Identifier>" | ForEach-Object { $_.Line.Trim() } | Select-Object -Unique
```

**YOU SEE:** `EPSG:3857`, `EPSG:4326`, `EPSG:900913`.

### Step 3. GetTile: download a real map tile (about 40 s)

```powershell
curl.exe -s -o tile_change.png -w "HTTP %{http_code}  %{content_type}  %{size_download} bytes`n" "$B/gwc/service/wmts?service=WMTS&request=GetTile&version=1.0.0&layer=bhoonidhi:wschange_c95_c97&style=&format=image/png&tilematrixset=EPSG:3857&tilematrix=EPSG:3857:10&tilerow=464&tilecol=737"
Start-Process tile_change.png
```

**YOU SEE:** `HTTP 200  image/png  <a few thousand> bytes`, then an image opens (blue and orange water pixels).

**SAY:** "That is one GetTile request: a 256 by 256 PNG, a few kilobytes, instead of a 555 MB download."

Now the big backscatter tile:

```powershell
curl.exe -s -o tile_hh.png -w "HTTP %{http_code}  %{size_download} bytes`n" "$B/gwc/service/wmts?service=WMTS&request=GetTile&version=1.0.0&layer=bhoonidhi:bs_hh_c97&style=&format=image/png&tilematrixset=EPSG:3857&tilematrix=EPSG:3857:10&tilerow=464&tilecol=737"
Start-Process tile_hh.png
```

**YOU SEE:** `HTTP 200`, then a grayscale radar image with the dark reservoir.

### Step 4. GetFeatureInfo: ask the map for a value (about 60 s)

Three points: open water, land, and a spot that **became water** between cycle 95 and cycle 97.

**Open water, HH backscatter in dB (cycle 97):**

```powershell
curl.exe -s "$B/gwc/service/wmts?service=WMTS&request=GetFeatureInfo&version=1.0.0&layer=bhoonidhi:bs_hh_c97&style=&format=image/png&infoformat=application/json&tilematrixset=EPSG:3857&tilematrix=EPSG:3857:14&tilerow=7408&tilecol=11797&i=133&j=99"
```

**YOU SEE:** `"GRAY_INDEX":-23.2...` (about -23 dB: very dark, as expected for calm water).

**Land point, same layer:**

```powershell
curl.exe -s "$B/gwc/service/wmts?service=WMTS&request=GetFeatureInfo&version=1.0.0&layer=bhoonidhi:bs_hh_c97&style=&format=image/png&infoformat=application/json&tilematrixset=EPSG:3857&tilematrix=EPSG:3857:14&tilerow=7444&tilecol=11823&i=201&j=178"
```

**YOU SEE:** `"GRAY_INDEX":-10.0...` (about -10 dB: brighter, land).

**The point that became water. Cycle 95 (before):**

```powershell
curl.exe -s "$B/gwc/service/wmts?service=WMTS&request=GetFeatureInfo&version=1.0.0&layer=bhoonidhi:bs_hh_c95&style=&format=image/png&infoformat=application/json&tilematrixset=EPSG:3857&tilematrix=EPSG:3857:14&tilerow=7428&tilecol=11795&i=135&j=67"
```

**YOU SEE:** `-15.7...`

**Same point, cycle 97 (after):**

```powershell
curl.exe -s "$B/gwc/service/wmts?service=WMTS&request=GetFeatureInfo&version=1.0.0&layer=bhoonidhi:bs_hh_c97&style=&format=image/png&infoformat=application/json&tilematrixset=EPSG:3857&tilematrix=EPSG:3857:14&tilerow=7428&tilecol=11795&i=135&j=67"
```

**YOU SEE:** `-26.1...`

**The water-change layer says the same thing in classes (2 = water gained):**

```powershell
curl.exe -s "$B/gwc/service/wmts?service=WMTS&request=GetFeatureInfo&version=1.0.0&layer=bhoonidhi:wschange_c95_c97&style=&format=image/png&infoformat=application/json&tilematrixset=EPSG:3857&tilematrix=EPSG:3857:14&tilerow=7428&tilecol=11795&i=135&j=67"
```

**YOU SEE:** `"GRAY_INDEX":2`

**SAY:** "The same spot drops from minus 15.7 dB to minus 26.1 dB between cycles 95 and 97, so it went from land to open
water as the reservoir filled. The EOS-04 water-spread product and my derived change layer agree: class 2, water gained."

### Step 5. A wrong request gives a proper OGC error (about 20 s)

```powershell
curl.exe -s "$B/gwc/service/wmts?service=WMTS&request=GetTile&version=1.0.0&layer=nope"
```

**YOU SEE:** XML starting `<ExceptionReport ...>` with `LAYER nope is not known.`

**SAY:** "Invalid requests return a standard OGC ExceptionReport."

### Step 6. OGC API – Tiles (about 60 s)

```powershell
(Invoke-RestMethod "$B/ogc/tiles/v1/collections?f=application/json").collections.id
```

**YOU SEE:** the same 10 `bhoonidhi:...` names (and nothing else).

```powershell
(Invoke-RestMethod "$B/ogc/tiles/v1/conformance?f=application/json").conformsTo
```

**YOU SEE:** a list containing `.../ogcapi-tiles-1/1.0/conf/core`, `.../tileset`, `.../tilesets-list` and more.

```powershell
curl.exe -s -o tile_ogcapi.png -w "HTTP %{http_code}  %{content_type}`n" "$B/ogc/tiles/v1/collections/bhoonidhi:bs_hh_c97/map/tiles/EPSG:900913/EPSG:900913:10/464/737?f=image/png"
Start-Process tile_ogcapi.png
```

**YOU SEE:** `HTTP 200  image/png` and the same radar image.

**SAY:** "The same data is also available through the newer OGC API – Tiles standard. Raster layers appear as 'map tilesets'
under `/map/tiles`, which is how GeoServer models them."

### Step 7. A web map using the service (about 60 s) *(browser tab 3: http://localhost:8081/demo/)*

1. The page opens at Nagarjuna Sagar with the **water change** layer on top (blue = gained, orange = lost).
2. In the layer list on the right, click **"Backscatter HH (dB), cycle 95"**, then **"cycle 97"**. The dark reservoir grows.
3. Click anywhere **on the dark reservoir**: the box says something like `-23.0 dB`.
4. Click on **land**: it says something like `-10.0 dB`.

**SAY:** "This is a plain Leaflet page. It uses nothing but standard WMTS tile URLs and GetFeatureInfo for the click values."

### Step 8. QGIS (about 60 s) *(optional but impressive)*

1. In QGIS: menu **Layer > Add Layer > Add WMS/WMTS Layer...**
2. Click **New**. Name: `Bhoonidhi EOS-04`. URL: `http://localhost:8081/geoserver/gwc/service/wmts?REQUEST=GetCapabilities`. Click **OK**.
3. Click **Connect**. Pick `bhoonidhi:bs_hh_c97` in the list, click **Add**. Then pick `bhoonidhi:wschange_c95_c97`, click **Add**. Close the dialog.
4. Right-click the layer > **Zoom to Layer**. (Or type `79.2,16.6` in the coordinate box at the bottom and set scale `1:200000`.)

**SAY:** "Any standard GIS client can use it. QGIS found all the layers from GetCapabilities with no custom code."

*(I could not test QGIS in my environment. Try this once before the demo. If it fails, skip the step and use Step 7.)*

### Step 9. The server is safe to expose (about 30 s)

```powershell
curl.exe -s -o NUL -w "REST API: HTTP %{http_code}`n" "$B/rest/workspaces.json"
curl.exe -s -o NUL -w "Admin UI : HTTP %{http_code}`n" "$B/web/"
```

**YOU SEE:** both `HTTP 403`.

**SAY:** "I put a read-only gateway in front of GeoServer. Only tile, WMS and the demo page are reachable. The admin
interface and REST API are blocked."

### Step 10. Tests and compliance evidence (about 45 s)

```powershell
python -m pytest -q tests
```

**YOU SEE:** `50 passed`.

Then in the browser open `https://github.com/maithily180/ogc-sar-tiles/blob/main/docs/COMPLIANCE.md`.

**SAY:** "Fifty live tests cover GetCapabilities, GetTile in both encodings, GetFeatureInfo, exception reports, the three
tile matrix sets and the OGC API – Tiles endpoints. I also validated the capabilities document against OGC's XML
schema: the only deviation is one pattern in GeoServer's output, MaxTileRow equal to 0, which the schema types as
positive integer. I did not run the official OGC CITE suite."

### Step 11. Close (about 20 s)

**SAY:** "The code, scripts, tests and write-up are in the GitHub repo. To reproduce: put the Bhoonidhi zips in
`data/bhoonidhi`, run `build_bhoonidhi_layers.py`, `docker compose up`, `publish.py`."

---

## Part C. Answers to likely questions

- **"Bhoonidhi's Vista viewer already shows these."** "Yes, its scripts load imagery as WMS through an authenticated
  backend call. I could not check whether those URLs work without a login. What is missing is a *public, documented, cacheable*
  WMTS / OGC API – Tiles service. Bhuvan's public WMS has about 8,900 layers and none are SAR products; its WMTS
  capabilities returned an error on 11 Oct 2026." (Evidence in `docs/GAP.md`.)
- **"Why is the proposal's ScanSAR mosaic not used?"** "The downloaded product is the MRS-mode `INDIA-MOSAIC-ARD`
  mosaic from the same Bhoonidhi collection (EOS-04 NRB India mosaic)."
- **"Where does the dB come from?"** "The product's own `product.xml`: Gamma-0 dB = 10·log10(DN²) − 67.139999."
- **"Why do tiles live under `/map/tiles`?"** "GeoServer's OGC API – Tiles module treats raster layers as map tilesets."
- **"Is it public?"** "It runs on localhost, which the brief allows. The gateway is read-only, so it is safe to put
  behind a tunnel."
- **"Why are some water pixels speckled?"** "The SAR water mask is per-pixel, so noise shows as speckle."

---

## Part D. If something goes wrong

| Problem | Fix |
|---|---|
| `curl.exe` says "Could not connect" | Docker is not running or containers are down. Open Docker Desktop, then `docker compose up -d`, wait 1 to 2 minutes. |
| `docker ps` shows nothing for `bhoonidhi` | `cd` into the project folder and run `docker compose up -d`. |
| Layers missing from GetCapabilities (list is empty) | Run `python scripts/publish.py`, then repeat the step. |
| Tests fail right after starting | GeoServer needs a minute to warm up. Wait 60 seconds, run the tests again. |
| Port 8080 or 8081 already in use | Close the program using it, or run `docker compose down` then `up -d` (this re-downloads an extension, so only if needed, and you need internet). |
| `curl` prints HTML help or weird PowerShell output | You typed `curl` instead of `curl.exe`. Always use `curl.exe` in PowerShell. |
| The web map shows a blank background | The page needs internet for the OpenStreetMap background and Leaflet. The tiles still load from localhost. |
| Tile appears empty | Zoom to Nagarjuna Sagar (about 16.6 N, 79.2 E). Data covers only 16 to 17 N, 79 to 80 E. |
| Everything is broken | Fallback: show the README images (`docs/tiles_overview.png`), `docs/GAP.md` and `docs/COMPLIANCE.md`, and say the stack could not start. |

## Part E. After the demo

```powershell
docker compose stop
```
