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
    <rasterrenderer nodataColor="" band="1" opacity="1" type="singlebandpseudocolor" alphaBand="-1" classificationMin="0" classificationMax="4000000">
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
        <colorrampshader colorRampType="DISCRETE" classificationMode="1" clip="0" minimumValue="0" maximumValue="4000000" labelPrecision="0">
          <item value="1200" alpha="255" color="#EDF8FB" label="LM-VF_0 — Minimal vannforstyrrelse, ≤ 1 200"/>
          <item value="4000" alpha="255" color="#B2E2E2" label="LM-VF_a — Svært beskyttet, > 1 200, ≤ 4 000"/>
          <item value="10000" alpha="255" color="#66C2A4" label="LM-VF_b — Temmelig beskyttet, > 4 000, ≤ 10 000"/>
          <item value="50000" alpha="255" color="#238B45" label="LM-VF_c — Litt beskyttet, > 10 000, ≤ 50 000"/>
          <item value="100000" alpha="255" color="#FFFFB2" label="LM-VF_d — Svakt eksponert, > 50 000, ≤ 100 000"/>
          <item value="500000" alpha="255" color="#FECC5C" label="LM-VF_e — Litt eksponert, > 100 000, ≤ 500 000"/>
          <item value="1000000" alpha="255" color="#FD8D3C" label="LM-VF_f — Temmelig eksponert, > 500 000, ≤ 1 000 000"/>
          <item value="2000000" alpha="255" color="#F03B20" label="LM-VF_g — Svært eksponert, > 1 000 000, ≤ 2 000 000"/>
          <item value="4000000" alpha="255" color="#BD0026" label="LM-VF_h — Ekstremt eksponert, > 2 000 000, ≤ 4 000 000"/>
          <rampLegendSettings suffix="" direction="0" minimumLabel="" maximumLabel="" prefix="" useContinuousLegend="1">
            <numericFormat id="basic">
              <Option type="Map">
                <Option value="" name="decimal_separator" type="QChar"/>
                <Option value="6" name="decimals" type="int"/>
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
