"""Classification and vectorization pipeline for stortare (large kelp) data."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections import defaultdict
from enum import IntEnum
from pathlib import Path

import numpy as np
from osgeo import gdal, osr

# Douglas-Peucker threshold for v.generalize (metres).
SMOOTH_THRESHOLD: float = 12.0

# Nodata value used in the classified byte raster
_NODATA: int = 255


class Klasse(IntEnum):
    """Stortare density classes (ind/m²)."""

    ENKELTINDIVIDER = 1  # 0.1–0.5 ind/m²
    SPREDT = 2           # 0.5–5  ind/m²
    MIDDELS_TETT = 3     # 5–10   ind/m²
    TETT = 4             # >10    ind/m²


KLASSE_INFO_STORTARE: dict[Klasse, dict[str, str]] = {
    Klasse.ENKELTINDIVIDER: {
        "navn_no": "Enkeltindivider (0,1–0,5/m²)",
        "navn_en": "Single individuals (0.1–0.5/m²)",
    },
    Klasse.SPREDT: {
        "navn_no": "Spredte forekomster (0,5–5/m²)",
        "navn_en": "Scarce occurrences (0.5–5/m²)",
    },
    Klasse.MIDDELS_TETT: {
        "navn_no": "Middels tett tareskog (5–10/m²)",
        "navn_en": "Moderately dense kelp forest (5–10/m²)",
    },
    Klasse.TETT: {
        "navn_no": "Tett tareskog (>10/m²)",
        "navn_en": "Dense kelp forest (>10/m²)",
    },
}

KLASSE_INFO_MERGED_STORTARE: dict[Klasse, dict[str, str]] = {
    1: {
        "navn_no": "Tett/Middels tett tareskog (>5/m²)",
        "navn_en": "Dense/Moderately dense kelp forest (>5/m²)",
    },
}

class KlasseSukkertare(IntEnum):
    """Sukkertare (Saccharina latissima) density classes (ind/m²)."""

    ENKELTPLANTER = 1  # 0.1–1  ind/m²
    SPREDT = 2         # 1–7   ind/m²
    MIDDELS_TETT = 3   # 7–15  ind/m²
    TETT = 4           # >15   ind/m²


KLASSE_INFO_SUKKERTARE: dict[KlasseSukkertare, dict[str, str]] = {
    KlasseSukkertare.ENKELTPLANTER: {
        "navn_no": "Enkeltplanter (0,1–1/m²)",
        "navn_en": "Single plants (0.1–1/m²)",
    },
    KlasseSukkertare.SPREDT: {
        "navn_no": "Spredt (1–7/m²)",
        "navn_en": "Scarce (1–7/m²)",
    },
    KlasseSukkertare.MIDDELS_TETT: {
        "navn_no": "Middels tett (7–15/m²)",
        "navn_en": "Moderately dense (7–15/m²)",
    },
    KlasseSukkertare.TETT: {
        "navn_no": "Tett/heldekkende skog (>15/m²)",
        "navn_en": "Dense/full-cover forest (>15/m²)",
    },
}

KLASSE_INFO_MERGED_SUKKERTARE: dict[KlasseSukkertare, dict[str, str]] = {

    3: {
        "navn_no": "Tett/Middels tett (>7/m²)",
        "navn_en": "Dense/Moderately dense (>7/m²)",
    }
}

def _classify_block(
    block: np.ndarray,
    valid: np.ndarray,
    thresholds: list[tuple[float, float, int]],
) -> np.ndarray:
    """Apply class thresholds to a raster block. Returns a uint8 array."""
    out = np.full(block.shape, _NODATA, dtype=np.uint8)
    for lo, hi, class_int in thresholds:
        mask = valid & (block > lo)
        if hi is not None:
            mask &= block <= hi
        out[mask] = class_int
    return out


def classify_skog(
    src_ds: gdal.Dataset,
    out_path: str | Path,
) -> gdal.Dataset:
    """Map continuous density values (ind/m²) to skog class integers.

    Values 5–10  → MIDDELS_TETT (3)
    Values  >10  → TETT (4)
    All other values (including nodata) → nodata.

    Processes block-by-block to avoid loading full raster into memory.
    Returns the open output Dataset (set to None to close).
    """
    _STORTARE_THRESHOLDS = [
        (5.0, 10.0, int(Klasse.MIDDELS_TETT)),
        (10.0, None, int(Klasse.TETT)),
    ]
    return _classify_raster(src_ds, out_path, _STORTARE_THRESHOLDS)


def classify_sukkertare(
    src_ds: gdal.Dataset,
    out_path: str | Path,
) -> gdal.Dataset:
    """Map continuous density values (ind/m²) to sukkertare class integers.

    Values 0.1–1   → ENKELTPLANTER (1)
    Values 1–7     → SPREDT (2)
    Values 7–15    → MIDDELS_TETT (3)
    Values  >15    → TETT (4)
    All other values (including nodata) → nodata.

    Processes block-by-block to avoid loading full raster into memory.
    Returns the open output Dataset (set to None to close).
    """
    _SUKKERTARE_THRESHOLDS = [
        (7.0, 15.0, int(KlasseSukkertare.MIDDELS_TETT)),
        (15.0, None, int(KlasseSukkertare.TETT)),
    ]
    return _classify_raster(src_ds, out_path, _SUKKERTARE_THRESHOLDS)


def _classify_raster(
    src_ds: gdal.Dataset,
    out_path: str | Path,
    thresholds: list[tuple[float, float | None, int]],
) -> gdal.Dataset:
    """Write a classified byte raster using (lo, hi, class_int) threshold tuples."""
    src_band = src_ds.GetRasterBand(1)
    src_nodata = src_band.GetNoDataValue()
    block_x, block_y = src_band.GetBlockSize()
    nx, ny = src_ds.RasterXSize, src_ds.RasterYSize

    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(
        str(out_path),
        nx, ny, 1, gdal.GDT_Byte,
        options=["COMPRESS=LZW", "TILED=YES", "BIGTIFF=YES"],
    )
    out_ds.SetGeoTransform(src_ds.GetGeoTransform())
    out_ds.SetProjection(src_ds.GetProjection())
    out_band = out_ds.GetRasterBand(1)
    out_band.SetNoDataValue(_NODATA)

    for y_off in range(0, ny, block_y):
        rows = min(block_y, ny - y_off)
        for x_off in range(0, nx, block_x):
            cols = min(block_x, nx - x_off)
            block = src_band.ReadAsArray(x_off, y_off, cols, rows).astype(np.float32)
            valid = (block != src_nodata) if src_nodata is not None else np.isfinite(block)
            out = _classify_block(block, valid, thresholds)
            out_band.WriteArray(out, x_off, y_off)

    out_band.FlushCache()
    out_ds.FlushCache()
    print(f"Classified raster written to: {out_path}")
    return out_ds


def _grass_env() -> dict:
    env = os.environ.copy()
    env["GISBASE"] = str(Path(sys.executable).parent.parent / "grass84")
    return env


def _grass_bin() -> str:
    return shutil.which("grass") or str(Path(sys.executable).parent / "grass")


def vectorize_skog(
    input_raster: Path | str,
    output_gpkg: Path | str,
) -> Path:
    """Vectorize classified skog raster to polygons via GRASS (r.in.gdal → r.to.vect).

    No generalisation is applied here; call generalize_skog afterwards.
    """
    input_raster = Path(input_raster).resolve()
    output_gpkg = Path(output_gpkg).resolve()

    ds = gdal.Open(str(input_raster))
    epsg = osr.SpatialReference(ds.GetProjection()).GetAuthorityCode(None)
    ds = None

    print(f"Vectorizing {input_raster.name} (EPSG:{epsg}) …")
    subprocess.run(
        [
            _grass_bin(), "--tmp-project", f"EPSG:{epsg}", "--exec",
            sys.executable, str(Path(__file__).resolve()),
            "--vectorize", str(input_raster), str(output_gpkg),
        ],
        check=True,
        env=_grass_env(),
    )
    print(f"Done → {output_gpkg}")
    return output_gpkg


def subtract_land(
    gdf,
    land_path: Path | str,
    land_layer: str = "landareal",
):
    """Subtract land polygons from a stortare GeoDataFrame using STRtree indexing.

    Args:
        gdf:        GeoDataFrame with stortare polygons (any CRS).
        land_path:  Path to land polygons file (GeoPackage or similar).
        land_layer: Layer name inside the land file.

    Returns:
        GeoDataFrame with land areas removed and empty geometries dropped.
    """
    import geopandas as gpd
    from shapely.geometry import MultiPolygon, Polygon
    from shapely.ops import unary_union
    from shapely.strtree import STRtree

    def _to_polygons(geom):
        if geom is None or geom.is_empty:
            return geom
        if isinstance(geom, (Polygon, MultiPolygon)):
            return geom
        polys = [
            g for g in getattr(geom, "geoms", [])
            if isinstance(g, (Polygon, MultiPolygon))
        ]
        if not polys:
            return Polygon()
        return MultiPolygon([
            p for mp in polys
            for p in (mp.geoms if isinstance(mp, MultiPolygon) else [mp])
        ])

    land = gpd.read_file(str(land_path), layer=land_layer).to_crs(gdf.crs)

    geoms = gdf.geometry.values.copy()
    tree = STRtree(geoms)
    land_idxs, geom_idxs = tree.query(land.geometry, predicate="intersects")

    geom_to_land = defaultdict(list)
    for l_i, g_i in zip(land_idxs.tolist(), geom_idxs.tolist()):
        geom_to_land[g_i].append(l_i)

    print(f"Subtracting land from {len(geom_to_land):,} of {len(geoms):,} polygons …")
    for g_i, l_indices in geom_to_land.items():
        land_union = unary_union(land.geometry.iloc[l_indices].values)
        geoms[g_i] = _to_polygons(geoms[g_i].difference(land_union))

    result = gdf.copy()
    result["geometry"] = geoms
    return result[~result.is_empty].reset_index(drop=True)


def generalize_skog(
    input_gpkg: Path | str,
    output_gpkg: Path | str,
    threshold: float = SMOOTH_THRESHOLD,
) -> Path:
    """Apply topology-preserving Douglas-Peucker to a skog vector via GRASS.

    Uses GRASS GIS (v.in.ogr → v.generalize method=douglas → v.out.ogr).
    """
    input_gpkg = Path(input_gpkg).resolve()
    output_gpkg = Path(output_gpkg).resolve()

    from osgeo import ogr
    ds = ogr.Open(str(input_gpkg))
    epsg = ds.GetLayer().GetSpatialRef().GetAuthorityCode(None)
    ds = None

    print(f"Generalizing {input_gpkg.name} (threshold={threshold} m) …")
    subprocess.run(
        [
            _grass_bin(), "--tmp-project", f"EPSG:{epsg}", "--exec",
            sys.executable, str(Path(__file__).resolve()),
            "--generalize", str(input_gpkg), str(output_gpkg), str(threshold),
        ],
        check=True,
        env=_grass_env(),
    )
    print(f"Done → {output_gpkg}")
    return output_gpkg


# ── GRASS inner implementations (called via subprocess --exec) ───────────────

def _vectorize_inside_grass(input_raster: str, output_gpkg: str) -> None:
    import grass.script as gs  # noqa: PLC0415

    gs.run_command("r.in.gdal", input=input_raster, output="raster", overwrite=True)
    gs.run_command("g.region", raster="raster")
    gs.run_command(
        "r.to.vect",
        flags="s",
        input="raster",
        output="vector",
        type="area",
        column="klasse_int",
        overwrite=True,
    )
    gs.run_command(
        "v.out.ogr",
        input="vector",
        output=output_gpkg,
        output_layer="stortare_skog",
        format="GPKG",
        overwrite=True,
        quiet=True,
    )


def _generalize_inside_grass(input_gpkg: str, output_gpkg: str, threshold: float) -> None:
    import grass.script as gs  # noqa: PLC0415

    gs.run_command("v.in.ogr", input=input_gpkg, output="vector", overwrite=True)
    gs.run_command(
        "v.generalize",
        input="vector",
        output="vector_smooth",
        method="douglas",
        threshold=threshold,
        type="area",
        overwrite=True,
    )
    gs.run_command(
        "v.out.ogr",
        input="vector_smooth",
        output=output_gpkg,
        output_layer="stortare_skog",
        format="GPKG",
        overwrite=True,
        quiet=True,
    )


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--vectorize":
        _, _, _raster, _gpkg = sys.argv
        _vectorize_inside_grass(_raster, _gpkg)
    elif len(sys.argv) >= 2 and sys.argv[1] == "--generalize":
        _, _, _gpkg_in, _gpkg_out, _threshold = sys.argv
        _generalize_inside_grass(_gpkg_in, _gpkg_out, float(_threshold))
