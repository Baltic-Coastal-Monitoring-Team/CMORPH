import os
import json
import geopandas as gpd
import streamlit as st
import folium
from folium.plugins import Fullscreen
from shapely.geometry import LineString
from streamlit_folium import st_folium

CONFIG_PATH = "tools/lines-py/config.json"

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as file:
            return json.load(file)
    return {"input_folder": ""}

def save_config(config):
    with open(CONFIG_PATH, "w") as file:
        json.dump(config, file, indent=4)

def resolve_path(path):
    base_dir = os.path.join(os.path.dirname(__file__), "tools/lines-py")
    return os.path.normpath(os.path.join(base_dir, path)) if not os.path.isabs(path) else path

def load_points_from_shp(file_path):
    try:
        return gpd.read_file(file_path)
    except Exception as e:
        st.error(f"File loading error {file_path}: {e}")
        return None

def create_line_from_points(points_gdf):
    points_sorted = points_gdf.sort_values(by=['profile_id', 'point_id'])
    return LineString(points_sorted.geometry.tolist())

def process_lines(input_folder, output_folder, selected_layers):
    required_folders = ["output", "analyser", "shapes"]
    full_path = os.path.join(resolve_path(input_folder), "output", "analyser", "shapes")
    if not os.path.exists(full_path):
        st.error("The required folder structure is missing: output > analyser > shapes")
        return {}
    
    available_folders = [d for d in os.listdir(full_path) if os.path.isdir(os.path.join(full_path, d))]
    valid_layers = {}
    
    for layer in available_folders:
        layer_path = os.path.join(full_path, layer)
        shp_file = os.path.join(layer_path, f"{layer}.shp")
        if os.path.exists(shp_file):
            valid_layers[layer] = shp_file
    
    output_folder = os.path.join(resolve_path(input_folder), "output", "lines")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    output_files = {}
    for layer, file_path in valid_layers.items():
        if layer in selected_layers:
            gdf = load_points_from_shp(file_path)
            if gdf is not None:
                line = create_line_from_points(gdf)
                line_gdf = gpd.GeoDataFrame(geometry=[line], crs=gdf.crs)
                output_path = os.path.join(output_folder, f"{layer}Line.geojson")
                line_gdf.to_file(output_path, driver='GeoJSON')
                output_files[layer] = output_path
        else:
            st.warning(f"File not found {file_path}, skipping {layer}.")
    
    return output_files

def lines_map_ui():
    st.title("Map")
    config = load_config()
    input_folder = config.get("input_folder", "")
    if not input_folder:
        st.warning("No path to data saved. Please return to the configuration and save the path.")
        return

    base_path = resolve_path(input_folder)
    lines_folder = os.path.join(base_path, "output", "lines")
    if not os.path.exists(lines_folder):
        st.warning("No lines generated. First, start the line generation process.")
        return

    geojson_files = [f for f in os.listdir(lines_folder) if f.endswith(".geojson")]
    if not geojson_files:
        st.warning("No GeoJSON files to display.")
        return

    name_map = {
        "topPointsLine.geojson": "top",
        "bottomPointsLine.geojson": "bottom",
        "firstZeroPointsLine.geojson": "first-zero",
        "lastZeroPointsLine.geojson": "last-zero"
    }
    color_map = {
        "top": "blue",
        "bottom": "green",
        "first-zero": "red",
        "last-zero": "purple"
    }

    if "lines_map_html" not in st.session_state:
        m = folium.Map(zoom_start=10, control_scale=True)
        bounds = []

        for geojson_file in geojson_files:
            layer_name = name_map.get(geojson_file, geojson_file)
            color = color_map.get(layer_name, "gray")
            geojson_path = os.path.join(lines_folder, geojson_file)
            try:
                gdf = gpd.read_file(geojson_path)
                if gdf.crs and gdf.crs.to_string() != "EPSG:4326":
                    gdf = gdf.to_crs(epsg=4326)

                group = folium.FeatureGroup(name=layer_name)
                for _, row in gdf.iterrows():
                    gj = folium.GeoJson(
                        row.geometry,
                        tooltip=layer_name,
                        style_function=lambda x, clr=color: {"color": clr, "weight": 4}
                    )
                    gj.add_to(group)
                    bounds.extend(row.geometry.bounds[:2])
                    bounds.extend(row.geometry.bounds[2:])
                group.add_to(m)
            except Exception as e:
                st.warning(f"Could not load {geojson_file}: {e}")

        if bounds:
            m.fit_bounds([[min(bounds[1::2]), min(bounds[::2])], [max(bounds[1::2]), max(bounds[::2])]])

        Fullscreen(position="topright").add_to(m)
        folium.LayerControl(position="topleft", collapsed=False).add_to(m)

        st.session_state["lines_map_html"] = m._repr_html_()

    st.components.v1.html(st.session_state["lines_map_html"], height=600, scrolling=False)
    
def lines_ui():
    subpage = st.sidebar.radio("Lines", ["Create lines", "Map"])
    
    if subpage == "Create lines":
        st.title("Create lines from points")
        config = load_config()
        input_folder = st.text_input("Path to the main folder with data:", value=config["input_folder"], key="input_folder_input")
        
        if st.button("Save path"):
            config["input_folder"] = input_folder
            save_config(config)
        
        resolved_path = resolve_path(input_folder)
        full_path = os.path.join(resolved_path, "output", "analyser", "shapes")
        if os.path.exists(full_path):
            available_layers = [d for d in os.listdir(full_path) if os.path.isdir(os.path.join(full_path, d))]
            selected_layers = []
            
            st.write("Select layers to process:")
            for layer in available_layers:
                layer_path = os.path.join(full_path, layer)
                shp_file = os.path.join(layer_path, f"{layer}.shp")
                if os.path.exists(shp_file):
                    if st.checkbox(layer, key=f"checkbox_{layer}"):
                        selected_layers.append(layer)
            
            if st.button("Create linie"):
                if selected_layers:
                    results = process_lines(input_folder, os.path.join(input_folder, "output", "lines"), selected_layers)
                    st.success("Lines generated and saved!")
                    for layer, file_path in results.items():
                        st.write(f"{file_path}")
                else:
                    st.error("No layers selected for processing!")
        else:
            st.warning("The required folder structure is missing.")
    elif subpage == "Map":
        lines_map_ui()
