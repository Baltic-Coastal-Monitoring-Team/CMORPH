import glob
import geopandas as gpd
from osgeo import gdal, gdalconst
import os
from os.path import join, basename
import pgen.config as config
import concurrent.futures
from tqdm import tqdm  # For progress tracking

import sys
IS_GUI = "--gui" in sys.argv

gdal.UseExceptions()
gdal.SetConfigOption("GDAL_NUM_THREADS", "ALL_CPUS")  # Use all available CPU threads
gdal.SetConfigOption("CPL_TMPDIR", "/tmp")  # Faster temporary directory if available
gdal.SetConfigOption("GDAL_CACHEMAX", "512")  # Increase cache to 512MB
gdal.SetConfigOption("VSI_CACHE", "TRUE")
gdal.SetConfigOption("VSI_CACHE_SIZE", "32000000")  # 32MB cache for file access
try:
    gdal.SetConfigOption("GDAL_USE_OPENCL", "TRUE")
except:
    pass  # If OpenCL isn't available, continue without it


def process_buffer(
    input_file,
    buffer_idx,
    cropped_path,
    slope_path,
    db,
    buffers_layer,
    crs,
    src_nodata,
    dst_nodata,
):
    """Process a single buffer for a given DEM file"""
    dem_cropped_file = join(cropped_path, f"{buffer_idx}_crop_{basename(input_file)}")

    options = gdal.WarpOptions(
        srcSRS=crs,
        dstSRS=crs,
        srcNodata=src_nodata,
        dstNodata=dst_nodata,
        format="GTiff",
        cutlineDSName=db,
        cutlineLayer=buffers_layer,
        cutlineWhere=f"fid={buffer_idx}",
        cropToCutline=True,
        outputType=gdalconst.GDT_Float32,
    )

    dem_input = gdal.Open(input_file, gdal.GA_ReadOnly)
    gdal_dataset = gdal.Warp(dem_cropped_file, dem_input, options=options)
    dem_input = None  # Close the input dataset

    max_val, min_val, mean, stddev = gdal_dataset.GetRasterBand(1).GetStatistics(0, 1)

    # Skip empty datasets
    if mean == 0 and stddev == 0:
        gdal_dataset = None  # Close dataset
        if os.path.exists(dem_cropped_file):
            os.remove(dem_cropped_file)
        return False

    # Process slope
    slope_file = join(slope_path, f"{buffer_idx}_slope_{basename(input_file)}")
    dem_cropped = gdal.Open(dem_cropped_file, gdal.GA_ReadOnly)
    gdal.DEMProcessing(slope_file, dem_cropped, "slope")

    # Close datasets
    dem_cropped = None
    gdal_dataset = None

    return True


def get_DEM(cfg):
    (
        dem_path,
        cropped_path,
        slope_path,
        db,
        transects_layer,
        buffers_layer,
        crs,
        buffer_width,
    ) = config.parse(cfg, get_DEM.__name__)

    try:
        # Create output directories if they don't exist
        os.makedirs(cropped_path, exist_ok=True)
        os.makedirs(slope_path, exist_ok=True)

        dem_input_files = glob.glob(join(dem_path, "*.tif"))
        if not dem_input_files:
            print("No DEM files found in the specified path")
            return

        # Create buffers
        transects = gpd.read_file(db, layer=transects_layer).to_crs(crs)
        buffers = transects.buffer(buffer_width)
        buffers.to_file(db, layer=buffers_layer, driver="GPKG")
        buffers_count = len(buffers.index)

        # Get a sample DEM file to extract nodata value
        sample_dem = gdal.Open(dem_input_files[0], gdal.GA_ReadOnly)
        src_nodata = sample_dem.GetRasterBand(1).GetNoDataValue()
        dst_nodata = -9999
        sample_dem = None  # Close the dataset

        # Create all tasks for parallel processing
        tasks = []
        for input_file in dem_input_files:
            for buffer_idx in range(1, buffers_count + 1):
                tasks.append(
                    (
                        input_file,
                        buffer_idx,
                        cropped_path,
                        slope_path,
                        db,
                        buffers_layer,
                        crs,
                        src_nodata,
                        dst_nodata,
                    )
                )

        # Process buffers in parallel
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Submit all tasks and track progress with tqdm
            futures = {executor.submit(process_buffer, *task): task for task in tasks}

            total_processed = 0
            #with tqdm(total=len(tasks), desc=f"... {basename(input_file)}") as progress:
            with tqdm(total=len(tasks), desc=f"... {basename(input_file)}", disable=IS_GUI) as progress:
                for future in concurrent.futures.as_completed(futures):
                    # Update progress regardless of result
                    progress.update(1)

                    # Check if the buffer was processed successfully
                    if future.result():
                        total_processed += 1

    except Exception as e:
        print("... get_DEM function error")
        raise e
