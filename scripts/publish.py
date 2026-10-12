"""Publish the COGs in data/cogs through GeoServer (WMS source layers + GeoWebCache tile layers).

Idempotent: re-running updates existing objects. Needs GeoServer from docker-compose.yml running.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import requests

MANIFEST = json.loads((Path(__file__).resolve().parent.parent / "layers.json").read_text(encoding="utf-8"))
WS = MANIFEST["workspace"]
# layer name -> (file in data/cogs, style, title, abstract)
LAYERS = {l["name"]: (l["file"], l["style"], l["title"], l["abstract"]) for l in MANIFEST["layers"]}
STYLES = sorted({l["style"] for l in MANIFEST["layers"]})
# Web Mercator under its EPSG:3857 name (GeoWebCache only ships the legacy alias EPSG:900913)
GRIDSET_3857_XML = """<gridSet>
  <name>EPSG:3857</name>
  <srs><number>3857</number></srs>
  <extent><coords><double>-20037508.34</double><double>-20037508.34</double>
    <double>20037508.34</double><double>20037508.34</double></coords></extent>
  <alignTopLeft>false</alignTopLeft>
  <resolutions>{res}</resolutions>
  <metersPerUnit>1.0</metersPerUnit>
  <pixelSize>2.8E-4</pixelSize>
  <tileHeight>256</tileHeight><tileWidth>256</tileWidth>
  <yCoordinateFirst>false</yCoordinateFirst>
</gridSet>"""
GWC_LAYER_XML = """<GeoServerLayer>
  <enabled>true</enabled>
  <inMemoryCached>true</inMemoryCached>
  <name>{name}</name>
  <mimeFormats><string>image/png</string><string>image/jpeg</string></mimeFormats>
  <gridSubsets>
    <gridSubset><gridSetName>EPSG:900913</gridSetName></gridSubset>
    <gridSubset><gridSetName>EPSG:3857</gridSetName></gridSubset>
    <gridSubset><gridSetName>EPSG:4326</gridSetName></gridSubset>
  </gridSubsets>
  <metaWidthHeight><int>4</int><int>4</int></metaWidthHeight>
  <gutter>0</gutter>
</GeoServerLayer>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default=os.getenv("GEOSERVER_URL", "http://localhost:8080/geoserver"))
    ap.add_argument("--user", default="admin")
    ap.add_argument("--password", default=os.getenv("GEOSERVER_ADMIN_PASSWORD", "geoserver"))
    ap.add_argument("--styles", default=Path(__file__).resolve().parent.parent / "styles", type=Path)
    ap.add_argument("--data-subdir", default="data/cogs", help="COG folder relative to the GeoServer data dir")
    a = ap.parse_args()

    s = requests.Session()
    s.auth = (a.user, a.password)
    rest = f"{a.url}/rest"

    def check(r, ok=(200, 201), what=""):
        if r.status_code not in ok:
            sys.exit(f"FAILED {what}: {r.status_code} {r.text[:400]}")

    # workspace
    r = s.get(f"{rest}/workspaces/{WS}.json")
    if r.status_code != 200:
        check(s.post(f"{rest}/workspaces", json={"workspace": {"name": WS}}), what="create workspace")
    print("workspace ok")

    # remove GeoServer's bundled sample data (topp, nurc, tiger, ne, sf ...) so only our layers are advertised
    groups = s.get(f"{rest}/layergroups.json").json().get("layerGroups")
    for g in (groups.get("layerGroup", []) if isinstance(groups, dict) else []):
        s.delete(f"{rest}/layergroups/{g['name']}")
    wss = s.get(f"{rest}/workspaces.json").json().get("workspaces")
    for w in (wss.get("workspace", []) if isinstance(wss, dict) else []):
        if w["name"] != WS:
            r = s.delete(f"{rest}/workspaces/{w['name']}?recurse=true")
            print(f"removed sample workspace {w['name']}" if r.status_code == 200
                  else f"could not remove workspace {w['name']} ({r.status_code})")

    # tile matrix set EPSG:3857
    if s.get(f"{a.url}/gwc/rest/gridsets/EPSG:3857.xml").status_code != 200:
        res = "".join(f"<double>{156543.03392804097 / 2 ** z!r}</double>" for z in range(25))
        check(s.put(f"{a.url}/gwc/rest/gridsets/EPSG:3857.xml", data=GRIDSET_3857_XML.format(res=res),
                    headers={"Content-Type": "text/xml"}), ok=(200, 201), what="create gridset EPSG:3857")
    print("gridset EPSG:3857 ok")

    # remove stores/tile layers that are no longer in layers.json
    stale = s.get(f"{rest}/workspaces/{WS}/coveragestores.json").json()
    for cs in ((stale.get("coverageStores") or {}) or {}).get("coverageStore", []) if isinstance(stale.get("coverageStores"), dict) else []:
        if cs["name"] not in LAYERS:
            s.delete(f"{a.url}/gwc/rest/layers/{WS}:{cs['name']}.xml")
            s.delete(f"{rest}/workspaces/{WS}/coveragestores/{cs['name']}?recurse=true&purge=none")
            print(f"removed stale layer {cs['name']}")

    for layer, (fname, style, title, abstract) in LAYERS.items():
        # style
        sld = (a.styles / f"{style}.sld").read_text(encoding="utf-8")
        if s.get(f"{rest}/workspaces/{WS}/styles/{style}.json").status_code != 200:
            check(s.post(f"{rest}/workspaces/{WS}/styles",
                         json={"style": {"name": style, "filename": f"{style}.sld"}}), what=f"create style {style}")
        check(s.put(f"{rest}/workspaces/{WS}/styles/{style}", data=sld.encode("utf-8"),
                    headers={"Content-Type": "application/vnd.ogc.sld+xml"}), what=f"upload style {style}")

        # coverage store + coverage
        store_url = f"{rest}/workspaces/{WS}/coveragestores/{layer}"
        # always recreate so bounds/CRS follow the current COG (stale config otherwise breaks GetFeatureInfo)
        if s.get(f"{store_url}.json").status_code == 200:
            check(s.delete(f"{store_url}?recurse=true&purge=none"), what=f"delete old store {layer}")
        if True:
            check(s.post(f"{rest}/workspaces/{WS}/coveragestores",
                         json={"coverageStore": {"name": layer, "type": "GeoTIFF", "enabled": True,
                                                 "workspace": {"name": WS},
                                                 "url": f"file:{a.data_subdir}/{fname}"}}),
                  what=f"create store {layer}")
        if s.get(f"{store_url}/coverages/{layer}.json").status_code != 200:
            check(s.post(f"{store_url}/coverages",
                         json={"coverage": {"name": layer, "nativeName": layer}}),
                  what=f"create coverage {layer}")
        check(s.put(f"{store_url}/coverages/{layer}.json",
                    json={"coverage": {"title": title, "abstract": abstract,
                                       "keywords": {"string": ["EOS-04", "SAR", "Bhoonidhi", "ISRO"]}}}),
              what=f"update coverage {layer}")
        check(s.put(f"{rest}/layers/{WS}:{layer}.json",
                    json={"layer": {"defaultStyle": {"name": f"{WS}:{style}", "workspace": WS}}}),
              what=f"set default style {layer}")

        # GeoWebCache tile layer (serves both WMTS and OGC API - Tiles)
        r = s.put(f"{a.url}/gwc/rest/layers/{WS}:{layer}.xml",
                  data=GWC_LAYER_XML.format(name=f"{WS}:{layer}"),
                  headers={"Content-Type": "text/xml"})
        check(r, ok=(200, 201), what=f"gwc layer {layer}")
        # drop stale tiles when the source COG was replaced
        s.post(f"{a.url}/gwc/rest/masstruncate", data=f"<truncateLayer><layerName>{WS}:{layer}</layerName></truncateLayer>",
               headers={"Content-Type": "text/xml"})
        print(f"published {WS}:{layer}")

    print("done")


if __name__ == "__main__":
    main()
