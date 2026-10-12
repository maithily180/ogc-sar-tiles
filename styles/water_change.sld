<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
  xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
  <NamedLayer>
    <Name>water_change</Name>
    <UserStyle>
      <Title>Water change between cycles</Title>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <Opacity>1.0</Opacity>
            <ColorMap type="values">
              <ColorMapEntry color="#000000" quantity="0" label="No water" opacity="0"/>
              <ColorMapEntry color="#9ECAE1" quantity="1" label="Stable water" opacity="0.85"/>
              <ColorMapEntry color="#08519C" quantity="2" label="Water gained" opacity="0.95"/>
              <ColorMapEntry color="#FD8D3C" quantity="3" label="Water lost" opacity="0.95"/>
              <ColorMapEntry color="#000000" quantity="255" label="No data" opacity="0"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
