import numpy as np
from osgeo import gdal


def sieve_filter(
    src_path,
    dst_path,
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


def apply_depth_mask(
    src_ds: gdal.Dataset,
    depth_ds: gdal.Dataset,
    out_path: str,
    max_depth: float = -50.0,
    vector_path: str | None = None,
) -> gdal.Dataset:
    """Mask pixels in src_ds where depth < max_depth or depth is nodata.

    Processes block-by-block to avoid loading full rasters into memory.
    depth_ds must be aligned to src_ds (same grid).

    If vector_path is provided, also writes a second raster where depth-nodata
    pixels are NOT removed (only genuinely too-deep pixels are masked). This is
    intended for vector production where land pixels (which have depth nodata)
    will later be removed by a land clip.

    Returns the output gdal.Dataset for out_path (open, caller should set to None to close).
    """
    src_band   = src_ds.GetRasterBand(1)
    depth_band = depth_ds.GetRasterBand(1)
    src_nodata   = src_band.GetNoDataValue()
    depth_nodata = depth_band.GetNoDataValue()
    out_nodata   = src_nodata if src_nodata is not None else -9999.0

    tiff_opts = ["COMPRESS=LZW", "TILED=YES", "BIGTIFF=YES"]
    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(
        out_path,
        src_ds.RasterXSize,
        src_ds.RasterYSize,
        1,
        gdal.GDT_Float32,
        options=tiff_opts,
    )
    out_ds.SetGeoTransform(src_ds.GetGeoTransform())
    out_ds.SetProjection(src_ds.GetProjection())
    out_band = out_ds.GetRasterBand(1)
    out_band.SetNoDataValue(out_nodata)

    vec_ds = vec_band = None
    if vector_path is not None:
        vec_ds = driver.Create(
            vector_path,
            src_ds.RasterXSize,
            src_ds.RasterYSize,
            1,
            gdal.GDT_Float32,
            options=tiff_opts,
        )
        vec_ds.SetGeoTransform(src_ds.GetGeoTransform())
        vec_ds.SetProjection(src_ds.GetProjection())
        vec_band = vec_ds.GetRasterBand(1)
        vec_band.SetNoDataValue(out_nodata)

    block_x, block_y = src_band.GetBlockSize()
    nx, ny = src_ds.RasterXSize, src_ds.RasterYSize
    n_total = n_kept = 0

    for y_off in range(0, ny, block_y):
        rows = min(block_y, ny - y_off)
        for x_off in range(0, nx, block_x):
            cols = min(block_x, nx - x_off)
            src_block   = src_band.ReadAsArray(x_off, y_off, cols, rows).astype(np.float32)
            depth_block = depth_band.ReadAsArray(x_off, y_off, cols, rows).astype(np.float32)

            # Valid = not nodata in source
            valid = (src_block != out_nodata) if src_nodata is not None else np.isfinite(src_block)
            n_total += int(valid.sum())

            # Mask where depth is nodata or below threshold
            depth_is_nodata = (depth_block == depth_nodata) if depth_nodata is not None else ~np.isfinite(depth_block)
            too_deep = depth_is_nodata | (depth_block < max_depth)

            # Final raster: mask depth nodata AND too-deep pixels
            masked = src_block.copy()
            masked[~valid | too_deep] = out_nodata
            n_kept += int((valid & ~too_deep).sum())
            out_band.WriteArray(masked, x_off, y_off)

            # Vector raster: only mask genuinely too-deep pixels (keep depth-nodata pixels)
            if vec_band is not None:
                too_deep_vec = (depth_block < max_depth) & ~depth_is_nodata
                vec_block = src_block.copy()
                vec_block[~valid | too_deep_vec] = out_nodata
                vec_band.WriteArray(vec_block, x_off, y_off)

    out_band.FlushCache()
    out_ds.FlushCache()

    if vec_band is not None:
        vec_band.FlushCache()
        vec_ds.FlushCache()
        vec_ds = None

    pct = 100.0 * n_kept / n_total if n_total else 0.0
    print(f"Pixels before depth filter: {n_total:,}")
    print(f"Pixels after  depth filter: {n_kept:,}  ({pct:.1f}% retained)")
    print(f"Written to: {out_path}")
    if vector_path is not None:
        print(f"Vector raster (depth nodata kept): {vector_path}")
    return out_ds


def reproject_and_mask_depth(
    src_ds: gdal.Dataset,
    depth_ds: gdal.Dataset,
    dst_crs: str,
    reproj_path: str,
    depth_aligned_path: str,
    filtered_path: str,
    max_depth: float = -50.0,
    vector_path: str | None = None,
) -> gdal.Dataset:
    """Reproject src_ds, align depth_ds to the reprojected grid, and apply depth mask.

    Steps:
      1. Reproject src_ds → dst_crs, written to reproj_path.
      2. Align depth_ds to the reprojected grid (same extent, pixel size, CRS),
         written to depth_aligned_path.
      3. Mask pixels deeper than max_depth (or where depth is nodata),
         written to filtered_path (the final/class-based product).

    If vector_path is provided, also writes a second raster where depth-nodata pixels
    are kept (only genuinely too-deep pixels removed), for use in vector production.

    Returns the filtered output gdal.Dataset (set to None to close).
    """
    warp_opts = gdal.WarpOptions(
        dstSRS=dst_crs,
        resampleAlg=gdal.GRA_NearestNeighbour,
        creationOptions=["COMPRESS=LZW", "TILED=YES", "BIGTIFF=YES"],
        multithread=True,
        warpMemoryLimit=512,
        format="GTiff",
    )
    reproj_ds = gdal.Warp(str(reproj_path), src_ds, options=warp_opts)
    reproj_ds.FlushCache()

    gt = reproj_ds.GetGeoTransform()
    xmin = gt[0]
    xmax = gt[0] + gt[1] * reproj_ds.RasterXSize
    ymax = gt[3]
    ymin = gt[3] + gt[5] * reproj_ds.RasterYSize

    align_opts = gdal.WarpOptions(
        dstSRS=dst_crs,
        outputBounds=(xmin, ymin, xmax, ymax),
        xRes=gt[1],
        yRes=abs(gt[5]),
        resampleAlg=gdal.GRA_NearestNeighbour,
        creationOptions=["COMPRESS=LZW", "TILED=YES", "BIGTIFF=YES"],
        multithread=True,
        warpMemoryLimit=512,
        format="GTiff",
    )
    depth_aligned_ds = gdal.Warp(str(depth_aligned_path), depth_ds, options=align_opts)
    depth_aligned_ds.FlushCache()

    assert depth_aligned_ds.RasterXSize == reproj_ds.RasterXSize
    assert depth_aligned_ds.RasterYSize == reproj_ds.RasterYSize

    filtered_ds = apply_depth_mask(
        src_ds=reproj_ds,
        depth_ds=depth_aligned_ds,
        out_path=str(filtered_path),
        max_depth=max_depth,
        vector_path=str(vector_path) if vector_path is not None else None,
    )
    depth_aligned_ds = None
    return filtered_ds


def apply_value_threshold(
    src_ds: gdal.Dataset,
    out_path: str,
    min_value: float,
    out_dtype: int = gdal.GDT_Float32,
) -> gdal.Dataset:
    """Mask pixels in src_ds where value > max_value or src has nodata.

    Processes block-by-block to avoid loading full rasters into memory.

    Returns the output gdal.Dataset (open, caller should set to None to close).
    """
    src_band = src_ds.GetRasterBand(1)
    src_nodata = src_band.GetNoDataValue()
    out_nodata = src_nodata if src_nodata is not None else -9999.0

    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(
        out_path,
        src_ds.RasterXSize,
        src_ds.RasterYSize,
        1,
        out_dtype,
        options=["COMPRESS=LZW", "TILED=YES", "BIGTIFF=YES"],
    )
    out_ds.SetGeoTransform(src_ds.GetGeoTransform())
    out_ds.SetProjection(src_ds.GetProjection())
    out_band = out_ds.GetRasterBand(1)
    out_band.SetNoDataValue(out_nodata)

    block_x, block_y = src_band.GetBlockSize()
    nx, ny = src_ds.RasterXSize, src_ds.RasterYSize
    n_total = n_kept = 0

    for y_off in range(0, ny, block_y):
        rows = min(block_y, ny - y_off)
        for x_off in range(0, nx, block_x):
            cols = min(block_x, nx - x_off)
            block = src_band.ReadAsArray(x_off, y_off, cols, rows).astype(np.float32)

            valid = (block != out_nodata) if src_nodata is not None else np.isfinite(block)
            n_total += int(valid.sum())

            too_low = valid & (block < min_value)
            block[~valid | too_low] = out_nodata
            n_kept += int((valid & too_low).sum())

            out_band.WriteArray(block, x_off, y_off)

    out_band.FlushCache()
    out_ds.FlushCache()

    pct = 100.0 * n_kept / n_total if n_total else 0.0
    print(f"Pixels before value filter: {n_total:,}")
    print(f"Pixels after  value filter: {n_kept:,}  ({pct:.1f}% retained)")
    print(f"Written to: {out_path}")
    return out_ds
