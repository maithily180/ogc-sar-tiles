<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
  xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
  <NamedLayer>
    <Name>sar_change_db</Name>
    <UserStyle>
      <Title>Backscatter change (dB), blue = darker, red = brighter</Title>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <Opacity>1.0</Opacity>
            <ColorMap type="ramp" extended="true">
              <ColorMapEntry color="#2166AC" quantity="-6" label="-6 dB"/>
              <ColorMapEntry color="#92C5DE" quantity="-3" label="-3 dB"/>
              <ColorMapEntry color="#F7F7F7" quantity="0" label="0 dB"/>
              <ColorMapEntry color="#F4A582" quantity="3" label="+3 dB"/>
              <ColorMapEntry color="#B2182B" quantity="6" label="+6 dB"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
