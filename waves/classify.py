from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from osgeo import gdal

gdal.UseExceptions()


CLASSES = pd.DataFrame(
    {
        "class_int": range(1, 11),
        "trinn": ["0", "a", "b", "c", "d", "e", "f", "g", "h", "y"],
        "navn_no": [
            "minimal vannforstyrrelse",
            "svært beskyttet",
            "temmelig beskyttet",
            "litt beskyttet",
            "svakt eksponert",
            "litt eksponert",
            "temmelig eksponert",
            "svært eksponert",
            "ekstremt eksponert",
            "disruptivt eksponert",
        ],
        "navn_en": [
            "minimal water movement",
            "very sheltered",
            "moderately sheltered",
            "slightly sheltered",
            "weakly exposed",
            "slightly exposed",
            "moderately exposed",
            "very exposed",
            "extremely exposed",
            "disruptively exposed",
        ],
        # Lower bound (exclusive), upper bound (inclusive); None = no bound
        "swm_lower": [None, 1_200, 4_000, 10_000, 50_000, 100_000, 500_000, 1_000_000, 2_000_000, 4_000_000],
        "swm_upper": [1_200, 4_000, 10_000, 50_000, 100_000, 500_000, 1_000_000, 2_000_000, 4_000_000, None],
    }
)

# Breakpoints for numpy.digitize (right=True: bins[i-1] < x <= bins[i])
SWM_BINS = [1_200, 4_000, 10_000, 50_000, 100_000, 500_000, 1_000_000, 2_000_000, 4_000_000]




def classify_swm_values(data: np.ndarray, nodata: int = 0) -> np.ndarray:
    """Map SWM raster values to NiN 3 class integers 1–10.

    Nodata pixels (value == nodata) are returned as 0 in the output.
    Values ≤ 1 200 → 1, > 1 200 ≤ 4 000 → 2, …, > 4 000 000 → 10.
    """
    mask = data == nodata
    classified = (np.digitize(data, SWM_BINS, right=True) + 1).astype(np.uint8)
    classified[mask] = 0
    return classified




def reclassify_raster(src_path: Path | str, dst_path: Path | str, block_size: int = 4096) -> None:
    """Reclassify an SWM raster to NiN 3 class integers (1–10, nodata=0).

    Processes the large raster in blocks to avoid loading it into memory.

    Args:
        src_path: Path to input SWM raster (Int32, nodata=0).
        dst_path: Path for output classified raster (Byte, nodata=0).
        block_size: Block size in pixels for tiled processing.
    """
    src_ds = gdal.Open(str(src_path), gdal.GA_ReadOnly)
    src_band = src_ds.GetRasterBand(1)
    nodata_val = int(src_band.GetNoDataValue() or 0)

    xsize, ysize = src_ds.RasterXSize, src_ds.RasterYSize

    driver = gdal.GetDriverByName("GTiff")
    dst_ds = driver.Create(
        str(dst_path),
        xsize,
        ysize,
        1,
        gdal.GDT_Byte,
        options=["COMPRESS=LZW", "TILED=YES", "BLOCKXSIZE=256", "BLOCKYSIZE=256", "BIGTIFF=IF_SAFER"],
    )
    dst_ds.SetGeoTransform(src_ds.GetGeoTransform())
    dst_ds.SetProjection(src_ds.GetProjection())
    dst_band = dst_ds.GetRasterBand(1)
    dst_band.SetNoDataValue(0)

    n_x = (xsize + block_size - 1) // block_size
    n_y = (ysize + block_size - 1) // block_size
    total = n_x * n_y
    done = 0

    for y0 in range(0, ysize, block_size):
        bh = min(block_size, ysize - y0)
        for x0 in range(0, xsize, block_size):
            bw = min(block_size, xsize - x0)
            data = src_band.ReadAsArray(x0, y0, bw, bh)
            dst_band.WriteArray(classify_swm_values(data, nodata_val), x0, y0)
            done += 1
            gdal.TermProgress_nocb(done / total)

    dst_band.FlushCache()
    dst_ds = src_ds = None


def sieve_filter(
    src_path: Path | str,
    dst_path: Path | str,
    threshold: int = 1,
    connectedness: int = 8,
) -> None:
    """Remove isolated pixel regions from a classified raster.

    Args:
        src_path: Input classified raster.
        dst_path: Output sieved raster.
        threshold: Regions with ≤ threshold pixels are removed.
        connectedness: 4 or 8 pixel connectivity.
    """
    src_ds = gdal.Open(str(src_path), gdal.GA_ReadOnly)
    src_band = src_ds.GetRasterBand(1)

    driver = gdal.GetDriverByName("GTiff")
    print("Copying classified raster...")
    dst_ds = driver.CreateCopy(
        str(dst_path),
        src_ds,
        options=["COMPRESS=LZW", "TILED=YES", "BLOCKXSIZE=256", "BLOCKYSIZE=256", "BIGTIFF=IF_SAFER"],
        callback=gdal.TermProgress_nocb,
    )
    dst_band = dst_ds.GetRasterBand(1)

    print(f"Applying sieve filter (threshold={threshold}, connectedness={connectedness})...")
    gdal.SieveFilter(src_band, None, dst_band, threshold=threshold, connectedness=connectedness, callback=gdal.TermProgress_nocb)

    dst_band.FlushCache()
    dst_ds = src_ds = None


def add_class_attributes(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Merge NiN 3 class attributes (trinn, navn_no, navn_en) into a GeoDataFrame.

    Args:
        gdf: GeoDataFrame with a ``class_int`` column.

    Returns:
        GeoDataFrame with added ``trinn``, ``navn_no``, and ``navn_en`` columns.
    """
    cols = ["class_int", "trinn", "navn_no", "navn_en"]
    return gdf.merge(CLASSES[cols], on="class_int", how="left")



