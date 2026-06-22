"""Generate QGIS raster QML stylesheets for stortare and sukkertare tetthetsklasser rasters.

Produces (per species, per language):
  stylesheets/tare/{species}-tetthetsklasser_norge_2021_25833_{no|en}.qml

Classes and labels are read from waves.tare.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import waves.tare as tare

STYLESHEET_DIR = Path(__file__).resolve().parent.parent / "stylesheets" / "tare"

# Sequential green ramp (light → dark), four classes. Anchor: #117733 at position 3.
_GREEN_RAMP = ["#C8E6D2", "#64AA78", "#117733", "#093C1A"]

# Sequential purple ramp (light → dark), four classes. Anchor: #882255 at position 3.
_BROWN_RAMP = ["#E6B9D7", "#B46496", "#882255", "#44112B"]


@dataclass
class RasterSpec:
    species: str
    klasse_enum: type[IntEnum]
    klasse_info: dict[Any, dict[str, str]]
    upper_bounds: dict[Any, float]
    class_min: float
    class_max: float
    color_ramp: list[str] = None

    def __post_init__(self) -> None:
        if self.color_ramp is None:
            self.color_ramp = _GREEN_RAMP


_SPECS: list[RasterSpec] = [
    RasterSpec(
        species="stortare",
        klasse_enum=tare.Klasse,
        klasse_info=tare.KLASSE_INFO_STORTARE,
        upper_bounds={
            tare.Klasse.ENKELTINDIVIDER: 0.5,
            tare.Klasse.SPREDT:          5.0,
            tare.Klasse.MIDDELS_TETT:    10.0,
            tare.Klasse.TETT:            1e10,
        },
        class_min=0.1,
        class_max=10.0,
    ),
    RasterSpec(
        species="sukkertare",
        klasse_enum=tare.KlasseSukkertare,
        klasse_info=tare.KLASSE_INFO_SUKKERTARE,
        upper_bounds={
            tare.KlasseSukkertare.ENKELTPLANTER: 1.0,
            tare.KlasseSukkertare.SPREDT:        7.0,
            tare.KlasseSukkertare.MIDDELS_TETT:  15.0,
            tare.KlasseSukkertare.TETT:          1e10,
        },
        class_min=0.1,
        class_max=15.0,
        color_ramp=_BROWN_RAMP,
    ),
]


def _base_name(label: str) -> str:
    """Strip the parenthetical range suffix from a KLASSE_INFO label."""
    return re.sub(r"\s*\(.*?\)", "", label).strip()


def _fmt_bound(val: float, lang: str) -> str:
    """Format a bound for display: integer if whole, else one decimal.
    Uses Norwegian decimal comma when lang == 'no'."""
    s = str(int(val)) if val == int(val) else f"{val:.1f}"
    if lang == "no":
        s = s.replace(".", ",")
    return s


def _interval_label(base: str, prev: float | None, upper: float, lang: str) -> str:
    """Build a label like 'Base name, > 0,5, ≤ 5' (or first/last variants)."""
    if prev is None:
        return f"{base}, ≤ {_fmt_bound(upper, lang)}"
    if upper >= 1e9:
        return f"{base}, > {_fmt_bound(prev, lang)}"
    return f"{base}, > {_fmt_bound(prev, lang)}, ≤ {_fmt_bound(upper, lang)}"


def build_qml(spec: RasterSpec, lang: str) -> str:
    label_key = f"navn_{lang}"
    colors = spec.color_ramp[: len(list(spec.klasse_enum))]
    uppers = [spec.upper_bounds[k] for k in spec.klasse_enum]

    items_xml = ""
    for i, (klasse, color) in enumerate(zip(spec.klasse_enum, colors)):
        upper = uppers[i]
        prev = uppers[i - 1] if i > 0 else None
        base = _base_name(spec.klasse_info[klasse][label_key])
        label = _interval_label(base, prev, upper, lang)
        val_str = f"{upper:.1f}" if upper < 1e9 else "1e+10"
        items_xml += (
            f'          <item value="{val_str}" alpha="255"'
            f' color="{color}" label="{label}"/>\n'
        )

    mn, mx = spec.class_min, spec.class_max
    return f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
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
    <rasterrenderer nodataColor="" band="1" opacity="1" type="singlebandpseudocolor" alphaBand="-1" classificationMin="{mn}" classificationMax="{mx}">
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
        <colorrampshader colorRampType="DISCRETE" classificationMode="1" clip="0" minimumValue="{mn}" maximumValue="{mx}" labelPrecision="2">
{items_xml.rstrip()}
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
"""


if __name__ == "__main__":
    STYLESHEET_DIR.mkdir(exist_ok=True)
    generated: list[Path] = []
    for spec in _SPECS:
        for lang in ("no", "en"):
            path = STYLESHEET_DIR / f"{spec.species}-tetthetsklasser_norge_{lang}.qml"
            path.write_text(build_qml(spec, lang), encoding="utf-8")
            print(f"Written: {path}")
            generated.append(path)

    # Convert all QMLs in the stylesheet dir to LYRX (one pass)
    qml_to_lyrx = Path(__file__).resolve().parent / "qml_to_lyrx.py"
    result = subprocess.run(
        [sys.executable, str(qml_to_lyrx)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(result.stdout.strip())
    else:
        print(f"WARNING: lyrx conversion failed: {result.stderr.strip()}")
