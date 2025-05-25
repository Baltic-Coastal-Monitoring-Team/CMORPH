import folium
import geopandas as gpd
import json
import matplotlib.pyplot as plt
import os
import pandas as pd
import rasterio
import re
import streamlit as st
import subprocess
import sys
from folium.plugins import Fullscreen
from folium.raster_layers import ImageOverlay
from rasterio.plot import reshape_as_image
from shapely.geometry import Point
from streamlit_folium import st_folium
from streamlit.components.v1 import html

CONFIG_PATH = "tools/analyzer-py/config.json"
MAIN_SCRIPT = "main.py"


def strip_ansi_codes(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

# Load and save configuration
def load_config():
    with open(CONFIG_PATH, "r") as file:
        return json.load(file)

def save_config(config):
    with open(CONFIG_PATH, "w") as file:
        json.dump(config, file, indent=4)

# Paths helper function
def get_base_path():
    config = load_config()
    base_path = config["paths"]["base"]
    analyzer_dir = os.path.join(os.path.dirname(__file__), "tools/analyzer-py")

    if os.path.isabs(base_path):
        return base_path

    return os.path.normpath(os.path.join(analyzer_dir, base_path))



def run_script():
    analyzer_dir = os.path.join(os.path.dirname(__file__), "tools/analyzer-py")
    config_path = os.path.join(analyzer_dir, "config.json")

    with open(config_path, "r") as f:
        config = json.load(f)

    base_path = config["paths"]["base"]
    if not os.path.isabs(base_path) and not base_path.startswith(".."):
        abs_base = os.path.abspath(os.path.join(analyzer_dir, base_path))
        config["paths"]["base"] = abs_base
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)
    process = subprocess.Popen(
        [sys.executable, MAIN_SCRIPT],
        cwd=analyzer_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    stdout_lines = []
    stderr_lines = []

    for line in process.stdout:
        clean = ansi_escape.sub('', line).strip()
        if clean:
            if "it/s" not in clean:
                stdout_lines.append(clean)

    for error in process.stderr:
        clean = ansi_escape.sub('', error).strip()
        if clean:
            stderr_lines.append(clean)

    process.wait()

    if stdout_lines:
        st.code("\n".join(stdout_lines), language="bash")

    if process.returncode == 0:
        st.success("Analyzer completed successfully")
    else:
        st.error("Analyzer failed")
        if stderr_lines:
            with st.expander("Error details"):
                st.error("\n".join(stderr_lines))
        if stdout_lines:
            with st.expander("Output Log"):
                st.text("\n".join(stdout_lines))


def analyzer_config_ui():
    """UI for configuring the Analyzer."""
    st.title("Analyzer")
    st.subheader("Config page")
    "---"
    # Load configuration
    config = load_config()

    # Paths section
    st.subheader("Paths")
    for key, value in config["paths"].items():
        if isinstance(value, dict):
            with st.expander(f"{key.capitalize()} Path"):
                for sub_key, sub_value in value.items():
                    config["paths"][key][sub_key] = st.text_input(f"{key} -> {sub_key}", value=sub_value)
        else:
            config["paths"][key] = st.text_input(key, value)

    # CSV section
    st.subheader("CSV Settings")
    for key, value in config["csv"].items():
        with st.expander(f"{key.capitalize()} CSV Settings"):
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, list):
                    config["csv"][key][sub_key] = st.text_area(
                        f"{key} -> {sub_key}", value="\n".join(sub_value)
                    ).splitlines()
                else:
                    config["csv"][key][sub_key] = st.text_input(f"{key} -> {sub_key}", value=sub_value)

    # Shape section
    st.subheader("Shape Settings")
    for key, value in config["shape"].items():
        config["shape"][key] = st.text_input(key, value)

    # Additional Parameters
    st.subheader("Additional Parameters")

    # Selected Profiles
    config["selected_profiles"] = [
        int(profile.strip()) for profile in st.text_area(
            "Selected Profiles (comma-separated)",
            value=",".join(map(str, config["selected_profiles"] or []))
        ).split(",") if profile.strip().isdigit()
    ]

    # Methods Order
    methods_order_input = st.text_area(
        "Methods Order (comma-separated)",
        value=",".join(map(str, config["methods_order"]))
    )
    config["methods_order"] = [int(method.strip()) for method in methods_order_input.split(",") if method.strip().isdigit()]

    # Max Error
    config["max_error"] = st.number_input("Max Error", value=float(config["max_error"]), step=0.1)

    # Save configuration
    if st.button("Save configuration"):
        save_config(config)
        st.success("Configuration saved!")

    # Run analyzer
    if st.button("Run Analyzer"):
        st.info("Running analyzer...")
        run_script()

def analyzer_results_ui():
    st.title("Results")
    config = load_config()
    base_path = get_base_path()

    csv_name = config["csv"]["output"]["first"]  
    csv_path = os.path.join(base_path, config["paths"]["output"]["finall"], csv_name)

    st.code(f"Looking for file: {csv_path}")

    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        st.subheader("Output content:")
        st.dataframe(df)
        st.download_button(
            label="Download CSV",
            data=df.to_csv(index=False),
            file_name=csv_name,
            mime="text/csv"
        )
        analyzer_results_visualizations(df)
    else:
        st.error(f"No CSV file found: {csv_name}")

def analyzer_results_visualizations(df):
    st.subheader("Visualization")

    with st.expander("Position and elevation"):
        for profile_id in df["profile_id"].unique():
            profile_data = df[df["profile_id"] == profile_id]
            fig, ax = plt.subplots(figsize=(10, 6))

            x_values = [
                profile_data.iloc[0]["first_zero_id"],
                profile_data.iloc[0]["last_zero_id"] if profile_data.iloc[0]["last_zero_id"] != profile_data.iloc[0]["first_zero_id"] else None,
                profile_data.iloc[0]["bottom_id"],
                profile_data.iloc[0]["top_id"]
            ]
            x_values = [x for x in x_values if x is not None]

            y_values = [
                profile_data.iloc[0]["first_zero_elevation"],
                profile_data.iloc[0]["last_zero_elevation"] if profile_data.iloc[0]["last_zero_id"] != profile_data.iloc[0]["first_zero_id"] else None,
                profile_data.iloc[0]["bottom_elevation"],
                profile_data.iloc[0]["top_elevation"]
            ]
            y_values = [y for y in y_values if y is not None]

            ax.plot(x_values, y_values, marker="o")
            ax.set_title(f"Profile ID: {profile_id}")
            ax.set_xlabel("Position (ID)")
            ax.set_ylabel("Elevation (m)")
            st.pyplot(fig)

    with st.expander("Beach width"):
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df["profile_id"], df["beach_width"], marker="o", label="Beach width")
        ax.set_xlabel("Profile ID")
        ax.set_ylabel("Beach width (m)")
        ax.legend()
        st.pyplot(fig)

    # Dune width
    with st.expander("Dune width"):
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df["profile_id"], df["dune_width"], marker="o", label="Dune width")
        ax.set_xlabel("Profile ID")
        ax.set_ylabel("Dune width (m)")
        ax.legend()
        st.pyplot(fig)

    # Beach and Dune slope
    with st.expander("Beach and Dune slope"):
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df["profile_id"], df["beach_slope"], label="Beach slope", marker="o")
        ax.plot(df["profile_id"], df["dune_slope"], label="Dune slope", marker="o")
        ax.set_xlabel("Profile ID")
        ax.set_ylabel("Slope (°)")
        ax.legend()
        st.pyplot(fig)

    # Beach and Dune volume
    with st.expander("Beach and Dune volume"):
        max_volume = max(df["beach_volume"].max(), df["dune_volume"].max())

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 6))

        ax1.bar(df["profile_id"], df["beach_volume"], color="blue")
        ax1.set_title("Beach volume")
        ax1.set_xlabel("Profile ID")
        ax1.set_ylabel("Volume (m³)")
        ax1.set_ylim(0, max_volume)  
        ax2.bar(df["profile_id"], df["dune_volume"], color="green")
        ax2.set_title("Dune volume")
        ax2.set_xlabel("Profile ID")
        ax2.set_ylabel("Volume (m³)")
        ax2.set_ylim(0, max_volume)  
        fig.subplots_adjust(hspace=0.5) 
        st.pyplot(fig)

    # Top and bottom elevation
    with st.expander("Top and bottom elevation"):
        fig, ax = plt.subplots(figsize=(16, 6))
        ax.plot(df["profile_id"], df["bottom_elevation"], marker="o", color="blue", label="Bottom elevation")
        ax.plot(df["profile_id"], df["top_elevation"], marker="o", color="orange", label="Top elevation")

        ax.set_title("Top and bottom elevation")
        ax.set_xlabel("Profile ID")
        ax.set_ylabel("Elevation (m)")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.7)

        st.pyplot(fig)




def analyzer_map_ui():
    st.title("Analyzer")
    st.subheader("Map with detected points")
    
    config = load_config()
    base_path = get_base_path()
    shape_dir = os.path.join(base_path, config["paths"]["output"]["shapes"])

    shp_files = {
        "first_zero": os.path.join(shape_dir, "firstZeroPoints", "firstZeroPoints.shp"),
        "last_zero": os.path.join(shape_dir, "lastZeroPoints", "lastZeroPoints.shp"),
        "bottom": os.path.join(shape_dir, "bottomPoints", "bottomPoints.shp"),
        "top": os.path.join(shape_dir, "topPoints", "topPoints.shp"),
    }

    #st.code(f"Shape directory: {shape_dir}")

    bounds = []
    m = folium.Map(zoom_start=10, control_scale=True)
    Fullscreen(position="bottomleft").add_to(m)

    colors = {
        "first_zero": "red",
        "last_zero": "purple",
        "bottom": "blue",
        "top": "green"
    }

    for name, path in shp_files.items():
        #st.code(f"{name}: {path}")
        if os.path.exists(path):
            try:
                gdf = gpd.read_file(path)
                if gdf.crs and gdf.crs.to_string().lower() != "epsg:4326":
                    gdf = gdf.to_crs(epsg=4326)

                layer = folium.FeatureGroup(name=name)
                for _, row in gdf.iterrows():
                    folium.CircleMarker(
                        location=[row.geometry.y, row.geometry.x],
                        radius=5,
                        color=colors.get(name, "black"),
                        fill=True,
                        fill_opacity=0.7,
                        tooltip=f"{name} | ID: {row.get('profile_id', 'n/a')} | elevation: {round(row.get('elevation', 0), 2)}"
                    ).add_to(layer)
                    bounds.append([row.geometry.y, row.geometry.x])
                layer.add_to(m)
            except Exception as e:
                st.warning(f"Unable to load SHP file {name}: {e}")
        else:
            st.warning(f"SHP file is missing: {name}")

    if bounds:
        m.fit_bounds(bounds)

    folium.LayerControl(position="topleft", collapsed=False).add_to(m)
    map_html = m._repr_html_()
    st.session_state["analyzer_map"] = map_html
    html(st.session_state["analyzer_map"], height=600, scrolling=False)



def analyzer_ui():
    """Main UI for Analyzer with submenu."""
    subpage = st.sidebar.radio("Analyzer", ["Config", "Results", "Map"])

    if subpage == "Config":
        analyzer_config_ui()
    elif subpage == "Results":
        analyzer_results_ui()
    elif subpage == "Map":
        analyzer_map_ui()
