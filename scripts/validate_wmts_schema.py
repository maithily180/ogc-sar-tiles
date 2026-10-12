"""Validate the service's WMTS GetCapabilities document against the OGC WMTS 1.0.0 XML schema.

    python scripts/validate_wmts_schema.py [capabilities-url]

Needs network access to schemas.opengis.net. Prints the error classes found (known: MaxTileRow/Col = 0 vs
xs:positiveInteger, see docs/COMPLIANCE.md).
"""
import collections
import sys

import requests
from lxml import etree

XSD = "http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd"


class NetResolver(etree.Resolver):
    def resolve(self, url, pubid, context):
        if url.startswith("http"):
            return self.resolve_string(requests.get(url, timeout=60).content, context, base_url=url)


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else (
        "http://localhost:8080/geoserver/gwc/service/wmts?service=WMTS&request=GetCapabilities&version=1.0.0")
    parser = etree.XMLParser(no_network=False)
    parser.resolvers.add(NetResolver())
    schema = etree.XMLSchema(etree.fromstring(requests.get(XSD, timeout=60).content, parser, base_url=XSD))
    doc = etree.fromstring(requests.get(url, timeout=120).content)
    ok = schema.validate(doc)
    kinds = collections.Counter()
    for e in schema.error_log:
        tile = ("MaxTileRow" in e.message or "MaxTileCol" in e.message) and "positiveInteger" in e.message
        kinds["MaxTileRow/Col = 0 vs xs:positiveInteger" if tile else e.message[:140]] += 1
    print("schema-valid:", ok, "| errors:", dict(kinds) or "none")


if __name__ == "__main__":
    main()
