import glob
import numpy as np
import pandas as pd
import geopandas as gpd
import shapely
from osgeo import gdal
from os.path import join, basename
from math import floor
import pgen.config as config
import concurrent.futures
import os
from tqdm import tqdm
import warnings

import sys
IS_GUI = "--gui" in sys.argv

warnings.filterwarnings("ignore", category=shapely.errors.ShapelyDeprecationWarning)


def reverse_geom(geom):
    def _reverse(x, y, z=None):
        if z:
            return x[::-1], y[::-1], z[::-1]
        return x[::-1], y[::-1]

    return shapely.ops.transform(_reverse, geom)


def process_transect(
    input_file,
    transect_idx,
    transect_line,
    reverse,
    cropped_path,
    slope_path,
    resolution,
):
    """Process a single transect for a DEM file"""
    profile = pd.DataFrame()
    cropped_file = join(cropped_path, f"{transect_idx + 1}_crop_{basename(input_file)}")
    slope_file = join(slope_path, f"{transect_idx + 1}_slope_{basename(input_file)}")

    height_raster = gdal.Open(cropped_file)
    slope_raster = gdal.Open(slope_file)

    if height_raster is None or slope_raster is None:
        return None, 0

    try:
        height_array = height_raster.GetRasterBand(1).ReadAsArray()
        slope_array = slope_raster.GetRasterBand(1).ReadAsArray()
        height_nodata = height_raster.GetRasterBand(1).GetNoDataValue()

        env = height_raster.GetGeoTransform()
        x_origin = env[0]
        y_origin = env[3]
        pixel_width = env[1]
        pixel_height = -env[5]

        line = transect_line
        line_length = round(line.length, 2)
        if reverse:
            line = reverse_geom(line)

        current_dist = 0
        x, y, dist, elevation, slope, xg, yg = [], [], [], [], [], [], []

        while current_dist < line_length:
            dist.append(current_dist)
            point = line.interpolate(current_dist)
            col = int((point.x - x_origin) / pixel_width)
            row = int((y_origin - point.y) / pixel_height)
            x_geo = point.x
            y_geo = point.y
            elevation.append(height_array[row][col])
            slope.append(slope_array[row][col])
            x.append(int(row))
            y.append(int(col))
            xg.append(float(x_geo))
            yg.append(float(y_geo))
            current_dist += resolution

        elevation = list(map(lambda i: 0 if i == height_nodata else i, elevation))

        no_point = np.arange(len(elevation))
        profile = pd.DataFrame(
            {
                "no_transect": transect_idx + 1,
                "length_transect": line_length,
                "no_point": no_point,
                "dem": basename(input_file),
                "x_image": x,
                "y_image": y,
                "x_geo": xg,
                "y_geo": yg,
                "elevation": [round(num, 2) for num in elevation],
                "slope": [round(num, 2) for num in slope],
            },
            index=line_length * transect_idx + no_point + 1,
        )

        # Calculate mono for this transect
        mono = 0
        if len(profile[profile.elevation > 0].index) > 0:
            mono = (
                profile.elevation[
                    profile[profile.elevation > 0]
                    .index[0] : profile[profile.elevation > 0]
                    .index[-1]
                ]
                .diff()
                .sum()
            )

        # Clean up resources
        height_raster = None
        slope_raster = None

        return profile, mono

    except Exception as e:
        if height_raster is not None:
            height_raster = None
        if slope_raster is not None:
            slope_raster = None
        print(f"Error processing transect {transect_idx+1}: {str(e)}")
        return None, 0


def generate_profiles(cfg):
    (
        crs,
        dem_path,
        cropped_path,
        slope_path,
        profile_path,
        db,
        profiles_layer,
        transects_layer,
        resolution,
        profile_csv,
    ) = config.parse(cfg, generate_profiles.__name__)

    try:
        # Create output directory if needed
        os.makedirs(profile_path, exist_ok=True)

        dem_input_files = glob.glob(join(dem_path, "*.tif"))
        if not dem_input_files:
            print("No DEM files found in the specified path")
            return

        transects = gpd.read_file(db, layer=transects_layer)
        transects_count = transects.id.count()
        transect_lines = np.asarray(transects.geometry)

        all_profiles = pd.DataFrame()

        for input_file in dem_input_files:
            profiles_for_dem = pd.DataFrame()

            reverse = False

            mono_total = 0
            results = []

            # Process transects in parallel
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_to_transect = {
                    executor.submit(
                        process_transect,
                        input_file,
                        idx,
                        transect_lines[idx],
                        reverse,
                        cropped_path,
                        slope_path,
                        resolution,
                    ): idx
                    for idx in range(transects_count)
                }

                # Use tqdm to show progress
                for future in tqdm(
                    concurrent.futures.as_completed(future_to_transect),
                    total=transects_count,
                    desc=f"... {basename(input_file)}"
                    + (" (reversed)" if reverse else ""),
                    disable=IS_GUI
                ):
                    transect_idx = future_to_transect[future]
                    try:
                        profile, mono = future.result()
                        if profile is not None:
                            results.append(profile)
                            mono_total += mono
                    except Exception as exc:
                        print(f"Error with transect {transect_idx+1}: {exc}")

            if mono_total < 0:
                # reverse
                for result in results:
                    result.no_point = (
                        1 + max(result.no_point) + result.no_point.__invert__()
                    )
                    result.index = list(
                        range(int(max(result.index)), int(min(result.index)) - 1, -1)
                    )

            profiles_for_dem = pd.concat(results, ignore_index=False).sort_index()

            all_profiles = pd.concat(
                [all_profiles, profiles_for_dem], ignore_index=False
            )

        # Save all profiles to separate CSV files
        grouped = all_profiles.groupby(["no_transect", "dem"])
        for (transect_idx, dem_name), profile_df in grouped:
            # Create filename based on transect number and DEM name
            csv_filename = join(profile_path, f"{int(transect_idx)}_whole_{dem_name}")

            # Make sure the filename has .csv extension
            if not csv_filename.endswith(".csv"):
                csv_filename = csv_filename.replace(".tif", ".csv")

            # Save to CSV with specified settings
            profile_df.to_csv(
                csv_filename,
                sep=profile_csv["sep"],
                encoding=profile_csv["encoding"],
                index=False,
            )

        # Save all profiles to GeoPackage
        if not all_profiles.empty:
            gpd.GeoDataFrame(
                all_profiles,
                geometry=gpd.points_from_xy(all_profiles.x_geo, all_profiles.y_geo),
            ).set_crs(crs).to_file(
                db, layer=profiles_layer, driver="GPKG", overwrite="yes"
            )

    except Exception as e:
        print("... generate_profiles function error")
        raise e


def process_single_profile(
    crs, source_file, cropping_buffer, in_profile_csv, out_profile_path, out_profile_csv
):
    """Process a single profile file for cropping"""
    try:
        csv_profile = pd.read_csv(source_file, sep=in_profile_csv["sep"])
        profile = gpd.GeoDataFrame(
            csv_profile,
            geometry=gpd.points_from_xy(csv_profile.x_geo, csv_profile.y_geo),
        ).set_crs(crs)

        cropped_profile = gpd.sjoin(
            profile, cropping_buffer, predicate="within", how="left"
        )
        cropped_profile = cropped_profile.to_crs(crs)

        output_file = join(
            out_profile_path, basename(source_file).replace("whole", "crop")
        )
        cropped_profile.to_csv(
            output_file,
            sep=out_profile_csv["sep"],
            encoding=out_profile_csv["encoding"],
            index=False,
        )
        return True
    except Exception as e:
        print(f"Error processing file {basename(source_file)}: {str(e)}")
        return False


def crop_profiles(cfg):
    (
        crs,
        buffer_path,
        in_profile_path,
        out_profile_path,
        profile_csv,
    ) = config.parse(cfg, crop_profiles.__name__)

    try:
        # Create output directory if it doesn't exist
        os.makedirs(out_profile_path, exist_ok=True)

        # Load buffers
        buffers = glob.glob(join(buffer_path, "*.shp"))
        if not buffers:
            print("No buffer files found in the specified path")
            return

        cropping_buffer = gpd.read_file(buffers[0]).to_crs(crs)
        cropping_buffer.id = 1  # change id

        # Get profile files
        profile_files = glob.glob(join(in_profile_path, "*.csv"))
        if not profile_files:
            print("No profile files found in the specified path")
            return

        # Process files in parallel
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(
                    process_single_profile,
                    crs,
                    source_file,
                    cropping_buffer,
                    profile_csv,
                    out_profile_path,
                    profile_csv,
                ): source_file
                for source_file in profile_files
            }

            # Use tqdm to show progress
            success_count = 0
            with tqdm(total=len(profile_files), desc=f"... all profiles", disable=IS_GUI) as pbar:
                for future in concurrent.futures.as_completed(future_to_file):
                    source_file = future_to_file[future]
                    try:
                        if future.result():
                            success_count += 1
                    except Exception as exc:
                        print(
                            f"Processing of {basename(source_file)} generated an exception: {exc}"
                        )
                    pbar.update(1)  # Update the progress bar

    except Exception as e:
        print("... crop_profiles function error")
        raise e
