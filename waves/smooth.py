"""Vectorize a classified raster to GeoPackage via GRASS GIS.

Pipeline (r.in.gdal → r.to.vect -s → v.generalize → v.out.ogr) runs inside a
temporary GRASS project and writes to paths.VRAW for prepare.subtract_land().
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from osgeo import gdal, osr

import waves.paths as paths

# Douglas-Peucker threshold: collapses 25 m raster staircase steps (~18 m max deviation).
SMOOTH_THRESHOLD: float = 12.0


def _run_inside_grass(input_raster: str, output_gpkg: str) -> None:
    import grass.script as gs  # noqa: PLC0415

    print("Importing raster into GRASS …")
    gs.run_command("r.in.gdal", input=input_raster, output="raster", overwrite=True)
    gs.run_command("g.region", raster="raster")

    print("Vectorizing (r.to.vect -s) …")
    gs.run_command(
        "r.to.vect",
        flags="s",
        input="raster",
        output="vector",
        type="area",
        column="class_int",
        overwrite=True,
    )

    print(f"Generalizing with Douglas (threshold={SMOOTH_THRESHOLD} m) …")
    gs.run_command(
        "v.generalize",
        input="vector",
        output="vector_smooth",
        method="douglas",
        threshold=SMOOTH_THRESHOLD,
        type="area",
        overwrite=True,
    )

    print(f"Exporting to {output_gpkg} …")
    gs.run_command(
        "v.out.ogr",
        input="vector_smooth",
        output=output_gpkg,
        output_layer="wave_exposure",
        format="GPKG",
        overwrite=True,
        quiet=True,
    )


def vectorize_raster(
    input_raster: Path | str = paths.SIE,
    output_gpkg: Path | str = paths.VRAW,
) -> Path:
    """Vectorize *input_raster* and write polygons to *output_gpkg*."""
    input_raster = Path(input_raster).resolve()
    output_gpkg = Path(output_gpkg).resolve()

    ds = gdal.Open(str(input_raster))
    epsg = osr.SpatialReference(ds.GetProjection()).GetAuthorityCode(None)
    ds = None

    print(f"Vectorizing {input_raster} (EPSG:{epsg}) …")

    subprocess.run(
        [
            "grass", "--tmp-project", f"EPSG:{epsg}", "--exec",
            sys.executable, str(Path(__file__).resolve()),
            "--inner", str(input_raster), str(output_gpkg),
        ],
        check=True,
    )

    print(f"Done → {output_gpkg}")
    return output_gpkg


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--inner":
        _, _, input_raster, output_gpkg = sys.argv
        _run_inside_grass(input_raster, output_gpkg)
    else:
        vectorize_raster()
