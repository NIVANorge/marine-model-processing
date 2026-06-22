<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis styleCategories="Symbology" version="3.44.7-Solothurn">
  <pipe-data-defined-properties>
    <Option type="Map">
      <Option value="" name="name" type="QString"/>
      <Option name="properties"/>
      <Option value="collection" name="type" type="QString"/>
    </Option>
  </pipe-data-defined-properties>
  <pipe>
    <provider>
      <resampling enabled="false" maxOversampling="2" zoomedOutResamplingMethod="nearestNeighbour" zoomedInResamplingMethod="nearestNeighbour"/>
    </provider>
    <rasterrenderer nodataColor="" band="1" opacity="1" type="singlebandpseudocolor" alphaBand="-1" classificationMin="0.1" classificationMax="10.0">
      <rasterTransparency/>
      <minMaxOrigin>
        <limits>None</limits>
        <extent>WholeRaster</extent>
        <statAccuracy>Estimated</statAccuracy>
        <cumulativeCutLower>0.02</cumulativeCutLower>
        <cumulativeCutUpper>0.98</cumulativeCutUpper>
        <stdDevFactor>2</stdDevFactor>
      </minMaxOrigin>
      <rastershader>
        <colorrampshader colorRampType="DISCRETE" classificationMode="1" clip="0" minimumValue="0.1" maximumValue="10.0" labelPrecision="2">
          <item value="0.5" alpha="255" color="#C8E6D2" label="Enkeltindivider, ≤ 0,5"/>
          <item value="5.0" alpha="255" color="#64AA78" label="Spredte forekomster, > 0,5, ≤ 5"/>
          <item value="10.0" alpha="255" color="#117733" label="Middels tett tareskog, > 5, ≤ 10"/>
          <item value="1e+10" alpha="255" color="#093C1A" label="Tett tareskog, > 10"/>
          <rampLegendSettings suffix="" direction="0" minimumLabel="" maximumLabel="" prefix="" useContinuousLegend="1">
            <numericFormat id="basic">
              <Option type="Map">
                <Option value="" name="decimal_separator" type="QChar"/>
                <Option value="2" name="decimals" type="int"/>
                <Option value="1" name="rounding_type" type="int"/>
                <Option value="false" name="show_plus" type="bool"/>
                <Option value="true" name="show_thousand_separator" type="bool"/>
                <Option value="false" name="show_trailing_zeros" type="bool"/>
                <Option value="" name="thousand_separator" type="QChar"/>
              </Option>
            </numericFormat>
          </rampLegendSettings>
        </colorrampshader>
      </rastershader>
    </rasterrenderer>
    <brightnesscontrast gamma="1" contrast="0" brightness="0"/>
    <huesaturation colorizeStrength="100" colorizeRed="255" colorizeBlue="128" saturation="0" grayscaleMode="0" colorizeOn="0" colorizeGreen="128" invertColors="0"/>
    <rasterresampler maxOversampling="2"/>
    <resamplingStage>resamplingFilter</resamplingStage>
  </pipe>
  <blendMode>0</blendMode>
</qgis>
