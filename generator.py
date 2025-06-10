import earthpy.plot as ep
import earthpy.spatial as es
import fiona
import folium
import geopandas as gpd
import io
import json
import matplotlib.cm as cm
import matplotlib.colors as colors
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import rasterio
import re
import streamlit as st
import subprocess
import sys
from folium.plugins import Fullscreen
from PIL import Image
from pyproj import Transformer
from rasterio.plot import show
from scipy.ndimage import gaussian_filter
from shapely.geometry import Point
from streamlit_folium import st_folium
from streamlit.components.v1 import html


def clean_line(line):
    """Remove ANSI escape sequences (e.g. colors) and strip whitespace."""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', line).strip()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "tools/generator-py/config.json")

def load_config():
    with open(CONFIG_PATH, "r") as file:
        return json.load(file)

def save_config(config):
    with open(CONFIG_PATH, "w") as file:
        json.dump(config, file, indent=4)

def run_generator():
    generator_dir = os.path.join(BASE_DIR, "tools/generator-py")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    process = subprocess.Popen(
        [sys.executable, "main.py", "--gui"],
        cwd=generator_dir,  
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        universal_newlines=True,
        env=env
    )
    
    progress = st.progress(0)
    status_text = st.empty()

    step_mapping = {
        "initializing": 0,
        "transects": 20,
        "cropped DEM": 40,
        "profiles": 60,
        "cropping profiles": 80,
    }

    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

    for line in process.stdout:
        clean_line = ansi_escape.sub('', line).strip()
        st.text(clean_line)

        if "initializing" in clean_line:
            progress.progress(step_mapping["initializing"])
            status_text.info("Initializing data structures...")
        elif "transects" in clean_line:
            progress.progress(step_mapping["transects"])
            status_text.info("Generating transects...")
        elif "cropped DEM" in clean_line:
            progress.progress(step_mapping["cropped DEM"])
            status_text.info("Preparing cropped DEM...")
        elif "generating profiles" in clean_line:
            progress.progress(step_mapping["profiles"])
            status_text.info("Generating profiles...")
        elif "cropping profiles" in clean_line:
            progress.progress(step_mapping["cropping profiles"])
            status_text.info("Cropping profiles...")

    for error in process.stderr:
        st.error(error)

    process.wait()
    progress.progress(100)
    status_text.success("Process completed!")

    if process.returncode != 0:
        st.error("Process ended with an error")


def generator_ui():
    st.title("Generator")
    config = load_config()

    st.subheader("Paths")
    for key, value in config["paths"].items():
        if isinstance(value, dict):
            with st.expander(f"{key.capitalize()}"):
                for sub_key, sub_value in value.items():
                    config["paths"][key][sub_key] = st.text_input(f"{key} → {sub_key}", sub_value)
        else:
            config["paths"][key] = st.text_input(key, value)

    #st.subheader("Database Layers")
    #for key, value in config["db_layers"].items():
    #    config["db_layers"][key] = st.text_input(f"{key}", value)

    st.subheader("CRS")
    config["crs"] = st.text_input("Coordinate Reference System (crs)", config.get("crs", "epsg:2154"))

    #st.subheader("CSV Settings")
    #config["csv"]["sep"] = st.text_input("CSV Separator", config["csv"].get("sep", ","))
    #config["csv"]["encoding"] = st.text_input("CSV Encoding", config["csv"].get("encoding", "utf-8-sig"))

    st.subheader("Parameters")
    config["parameters"]["use_precalculated_transects"] = st.checkbox(
        "Use Precalculated Transects",
        value=config["parameters"].get("use_precalculated_transects", False)
    )
    config["parameters"]["transect_distance"] = st.number_input(
        "Transect Distance (m)", value=config["parameters"].get("transect_distance", 50)
    )
    config["parameters"]["transect_length"] = st.number_input(
        "Transect Length (m)", value=config["parameters"].get("transect_length", 40)
    )
    config["parameters"]["profile_resolution"] = st.number_input(
        "Profile Resolution (m)", value=config["parameters"].get("profile_resolution", 0.5)
    )
    config["parameters"]["buffer_width"] = st.number_input(
        "Buffer Width (m)", value=config["parameters"].get("buffer_width", 10)
    )

    if st.button("Save Configuration"):
        save_config(config)
        st.success("Configuration saved!")

    if st.button("Run Generator"):
        st.info("Running generator...")
        run_generator()


def generator_results():
    st.title("Generator Results")
    base_path = get_base_path_from_config()
    if base_path:
        display_results(base_path)
    else:
        st.error("Cannot display results. No valid configuration found.")

def get_base_path_from_config():
    """Read `base` value from config.json."""
    config_path = os.path.join(BASE_DIR, "tools/generator-py/config.json")
    if not os.path.exists(config_path):
        st.error("Configuration file was not found!")
        return None
    with open(config_path, "r") as f:
        config = json.load(f)
    
    base_path = config["paths"]["base"]
    if not os.path.isabs(base_path):
        base_path = os.path.abspath(os.path.join(BASE_DIR, "tools/generator-py", base_path))

    if not os.path.exists(base_path):
        st.error(f"Base folder {base_path} does not exist!")
        return None

    return base_path

def display_results(base_path):
    """Display results from `base_path`."""
    if not base_path:
        return
    
    db_path = os.path.join(base_path, "db", "database.gpkg")
    profiles_path = os.path.join(base_path, "output", "generator", "profiles")
    dem_path = os.path.join(base_path, "output", "generator", "dem", "cropped")

    st.subheader("DB data")
    if os.path.exists(db_path):
        try:
            layer_names = fiona.listlayers(db_path)  
            #st.write(f"Layers available: {layer_names}")

            if "cached_db_html" not in st.session_state:
                m = folium.Map(zoom_start=12)
                Fullscreen(position="bottomleft").add_to(m)
                bounds = []

                for layer_name in layer_names:
                    try:
                        gdf = gpd.read_file(db_path, layer=layer_name)
                        if gdf.crs and gdf.crs.to_string() != "EPSG:4326":
                            gdf = gdf.to_crs(epsg=4326)

                        layer = folium.FeatureGroup(name=layer_name)
                        if layer_name in ["profiles", "points"]:
                            for _, row in gdf.iterrows():
                                folium.CircleMarker(
                                    location=[row.geometry.y, row.geometry.x],
                                    radius=2,
                                    color="blue",
                                    fill=True,
                                    fill_color="blue",
                                    fill_opacity=0.7,
                                ).add_to(layer)
                        else:
                            folium.GeoJson(gdf).add_to(layer)

                        layer.add_to(m)
                        bounds.append(gdf.total_bounds)
                    except Exception as e:
                        st.warning(f"The layer cannot be loaded. `{layer_name}`: {e}")

                folium.LayerControl(position="topleft", collapsed=False).add_to(m)

                if bounds:
                    minx = min(b[0] for b in bounds)
                    miny = min(b[1] for b in bounds)
                    maxx = max(b[2] for b in bounds)
                    maxy = max(b[3] for b in bounds)
                    m.fit_bounds([[miny, minx], [maxy, maxx]])

                st.session_state.cached_db_html = m.get_root().render()

            html(st.session_state.cached_db_html, height=700)

        except Exception as e:
            st.error(f"Error while reading GeoPackage layers: {e}")
    else:
        st.error("GeoPackage file not found!")


    st.subheader("CSV files")
    for folder_name, title in [("cropped", "Cropped"), ("whole", "Whole")]:
        folder_path = os.path.join(profiles_path, folder_name)
        if os.path.exists(folder_path):
            csv_files = [f for f in os.listdir(folder_path) if f.endswith(".csv")]
            if csv_files:
                selected_csv = st.selectbox(f"Select CSV file ({title}):", csv_files, key=folder_name)
                csv_path = os.path.join(folder_path, selected_csv)
                df = pd.read_csv(csv_path)
                st.write(df)
            else:
                st.warning(f"No CSV files in the folder {folder_name}.")
        else:
            st.error(f"Folder {folder_name} not found!")

    st.subheader("DEM visualization")
    dem_dir = os.path.join(base_path, "output", "generator", "dem", "cropped")

    if os.path.exists(dem_dir):
        dem_files = [f for f in os.listdir(dem_dir) if f.endswith(".tif")]

        selected_dem = st.selectbox("Select DEM:", dem_files)

        cache_key = f"cached_dem_map_{selected_dem}"

        if selected_dem:
            if cache_key in st.session_state:
                html(st.session_state[cache_key], height=600)
            else:
                dem_path = os.path.join(dem_dir, selected_dem)

                try:
                    with rasterio.open(dem_path) as src:
                        st.write(f"File info {selected_dem}:")
                        st.json({
                            "driver": src.driver,
                            "dtype": src.dtypes[0],
                            "nodata": src.nodatavals[0],
                            "width": src.width,
                            "height": src.height,
                            "count": src.count,
                            "crs": src.crs.to_string(),
                            "transform": list(src.transform)
                        }, expanded=False)

                        raster_data = src.read(1)
                        bounds = src.bounds
                        nodata_value = src.nodatavals[0]
                        if nodata_value is not None:
                            raster_data = np.ma.masked_equal(raster_data, nodata_value).filled(fill_value=np.nan)
                        if raster_data.size == 0 or np.isnan(raster_data).all():
                            raise ValueError("DEM files are empty or incorrect!")
                        hillshade = es.hillshade(raster_data, azimuth=315, altitude=30)
                        fig, ax = plt.subplots(figsize=(8, 6))
                        ax.imshow(hillshade, cmap="Greys", alpha=0.5)
                        ax.imshow(raster_data, cmap="terrain", alpha=0.7)
                        ax.axis("off")
                        tmp_image_path = "/tmp/dem_hillshade.png"
                        fig.savefig(tmp_image_path, dpi=300, bbox_inches="tight", pad_inches=0, transparent=True)
                        plt.close(fig)
                        transformer = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True)
                        top_left = transformer.transform(bounds.left, bounds.top)
                        bottom_right = transformer.transform(bounds.right, bounds.bottom)
                        raster_bounds = [[top_left[1], top_left[0]], [bottom_right[1], bottom_right[0]]]
                        centroid_lat = (top_left[1] + bottom_right[1]) / 2
                        centroid_lon = (top_left[0] + bottom_right[0]) / 2
                        m = folium.Map(location=[centroid_lat, centroid_lon], zoom_start=18)

                        folium.raster_layers.ImageOverlay(
                            image=plt.imread(tmp_image_path),
                            bounds=raster_bounds,
                            opacity=0.9
                        ).add_to(m)
                        #folium.LayerControl().add_to(m)

                        html_str = m.get_root().render()
                        st.session_state[cache_key] = html_str
                        html(html_str, height=600)

                except Exception as e:
                    st.error(f"DEM file read error: {e}")
    else:
        st.error("No folder containing DEM files was found.")



def input_data_viewer(base_path):
    st.title("Input data")

    input_dir = os.path.join(base_path, "input")
    if not os.path.exists(input_dir):
        st.error("The folder `input` was not found.")
        return

    if "cached_input_map_html" in st.session_state:
        html(st.session_state.cached_input_map_html, height=800)
        st.stop()

    m = folium.Map(zoom_start=12)
    Fullscreen(position="bottomleft").add_to(m)
    bounds = []
    subfolders = ["coast", "crop", "dem"]

    for subfolder in subfolders:
        folder_path = os.path.join(input_dir, subfolder)
        if not os.path.exists(folder_path):
            continue
        for file in os.listdir(folder_path):
            if file.endswith(".shp"):
                try:
                    gdf = gpd.read_file(os.path.join(folder_path, file))
                    if gdf.crs and gdf.crs.to_string() != "EPSG:4326":
                        gdf = gdf.to_crs(epsg=4326)
                    layer = folium.FeatureGroup(name=f"{subfolder} - {file}")
                    folium.GeoJson(gdf).add_to(layer)
                    layer.add_to(m)
                    bounds.append(gdf.total_bounds)
                except Exception as e:
                    st.warning(f"Failed to read {file}: {e}")

    if bounds:
        minx = min(b[0] for b in bounds)
        miny = min(b[1] for b in bounds)
        maxx = max(b[2] for b in bounds)
        maxy = max(b[3] for b in bounds)
        m.fit_bounds([[miny, minx], [maxy, maxx]])

    folium.LayerControl(position="topleft", collapsed=False).add_to(m)

    # Render and cache HTML
    st.session_state.cached_input_map_html = m.get_root().render()
    html(st.session_state.cached_input_map_html, height=800)


