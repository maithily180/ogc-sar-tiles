<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
  xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
  <NamedLayer>
    <Name>sar_backscatter_db</Name>
    <UserStyle>
      <Title>SAR backscatter (dB), grayscale -25 to 0</Title>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <Opacity>1.0</Opacity>
            <ColorMap type="ramp" extended="true">
              <ColorMapEntry color="#000000" quantity="-25" label="-25 dB" opacity="1"/>
              <ColorMapEntry color="#555555" quantity="-15" label="-15 dB"/>
              <ColorMapEntry color="#AAAAAA" quantity="-8" label="-8 dB"/>
              <ColorMapEntry color="#FFFFFF" quantity="0" label="0 dB"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
