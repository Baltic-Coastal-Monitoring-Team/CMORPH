import os
import json
import geopandas as gpd
import streamlit as st
import pandas as pd
import folium
import numpy as np
import re
import matplotlib.pyplot as plt
from shapely.geometry import Point, LineString
from streamlit_folium import st_folium
from sklearn.linear_model import LinearRegression
from folium.plugins import Fullscreen
from folium import Map, GeoJson, LayerControl
from streamlit.components.v1 import html
from scipy.stats import t
import scipy.stats as stats

CONFIG_PATH = "tools/stats-py/config.json"

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as file:
            return json.load(file)
    return {"input_folder": "", "selected_folders": [], "selected_line": ""}

def save_config(config):
    with open(CONFIG_PATH, "w") as file:
        json.dump(config, file, indent=4)

BASE_DIR = os.path.join(os.path.dirname(__file__), "tools/stats-py")

def resolve_path(path):
    return os.path.normpath(os.path.join(BASE_DIR, path)) if not os.path.isabs(path) else path

def display_map(base_folder, selected_folders, line_name):
    st.subheader(f"Map of selected lines: {line_name}")

    map_key = f"map_cache_{line_name}_{'-'.join(selected_folders)}"
    if st.session_state.get(map_key):
        html(st.session_state[map_key], height=600)
        return

    m = Map(zoom_start=10, control_scale=True)
    colors = ["red", "blue", "green", "purple", "orange", "darkred", "cadetblue"]
    bounds = []

    for i, folder in enumerate(selected_folders):
        geojson_path = os.path.join(base_folder, folder, "output", "lines", line_name)
        if os.path.exists(geojson_path):
            gdf = gpd.read_file(geojson_path)
            if gdf.crs and gdf.crs.to_string() != "EPSG:4326":
                gdf = gdf.to_crs(epsg=4326)

            gdf["source_folder"] = folder
            color = colors[i % len(colors)]

            layer = GeoJson(
                gdf,
                name=folder,
                tooltip=folder,
                style_function=lambda feature, color=color: {"color": color, "weight": 2}
            )
            layer.add_to(m)
            bounds.append(gdf.total_bounds)

    if bounds:
        minx = min(b[0] for b in bounds)
        miny = min(b[1] for b in bounds)
        maxx = max(b[2] for b in bounds)
        maxy = max(b[3] for b in bounds)
        m.fit_bounds([[miny, minx], [maxy, maxx]])

    Fullscreen(position="bottomleft").add_to(m)
    LayerControl(position="topright", collapsed=False).add_to(m)
    map_html = m.get_root().render()
    st.session_state[map_key] = map_html
    html(map_html, height=600)

def stats_ui():
    subpage = st.sidebar.radio("Statistics", ["Calculation"])

    config = load_config()
    if "input_folder" not in st.session_state:
        st.session_state["input_folder"] = config.get("input_folder", "")
    if "selected_folders" not in st.session_state:
        st.session_state["selected_folders"] = []
    if "line_name" not in st.session_state:
        st.session_state["line_name"] = ""
    if "lrr_results" not in st.session_state:
        st.session_state["lrr_results"] = {}
    if "show_results" not in st.session_state:
        st.session_state["show_results"] = False

    if subpage == "Calculation":
        st.title("Statistics calculation")

        user_input = st.text_input("Path to the main folder with data:", value=st.session_state["input_folder"])

        if st.button("Save path"):
            st.session_state["input_folder"] = user_input
            config["input_folder"] = user_input
            save_config(config)
            st.success("Path saved!")

        base_path = resolve_path(st.session_state["input_folder"])
        if not os.path.exists(base_path):
            st.warning("The specified path does not exist..")
            return

        subfolders = [f for f in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, f))]
        selected_folders = []

        st.write("Select folders for analysis:")
        for folder in subfolders:
            folder_path = os.path.join(base_path, folder, "output", "analyser", "shapes")
            if os.path.exists(folder_path):
                if st.checkbox(folder, key=f"checkbox_{folder}", value=(folder in st.session_state["selected_folders"])):
                    selected_folders.append(folder)

        if st.button("Confirm your selection"):
            if selected_folders:
                st.session_state["selected_folders"] = selected_folders
                st.success("Selected folders saved for analysis.")
            else:
                st.error("No folders selected!")

        available_lines = set()
        for folder in st.session_state["selected_folders"]:
            lines_folder = os.path.join(base_path, folder, "output", "lines")
            if os.path.exists(lines_folder):
                geojson_files = {f for f in os.listdir(lines_folder) if f.endswith(".geojson")}
                available_lines.update(geojson_files)

        selected_line = st.selectbox("Available linie:", list(available_lines) if available_lines else ["No lines available"], index=0)

        if selected_line and selected_line != "No lines available":
            st.session_state["line_name"] = selected_line
            display_map(base_path, st.session_state["selected_folders"], st.session_state["line_name"])

            if st.button("Calculate statistics"):
                if len(st.session_state["selected_folders"]) < 2:
                    st.warning("You need to select at least two folders for the statistics.")
                else:
                    compute_statistics(base_path, st.session_state["selected_folders"], st.session_state["line_name"])


def compute_statistics(base_folder, selected_folders, line_name):
    st.subheader(f"{line_name}")
    
    folder_points = {}

    if len(selected_folders) < 2:
        st.error("To calculate statistics, select at least 2 folders.")
        return

    for folder in selected_folders:
        shp_folder_name = line_name.replace("Line.geojson", "")  
        shp_path = os.path.join(base_folder, folder, "output", "analyser", "shapes", shp_folder_name, f"{shp_folder_name}.shp")

        if os.path.exists(shp_path):
            gdf = gpd.read_file(shp_path)
            gdf = gdf.to_crs(epsg=2180) 
            folder_points[folder] = gdf

    if not folder_points:
        st.error("The required data could not be downloaded (no shp files).")
        return

    min_points = min(len(gdf) for gdf in folder_points.values())
    for folder in folder_points:
        folder_points[folder] = folder_points[folder].iloc[:min_points]

    st.session_state["folder_points"] = folder_points
    st.session_state["selected_folders"] = selected_folders
    st.session_state["line_name"] = line_name
    st.session_state["input_folder"] = resolve_path(base_folder)

    compute_sce(folder_points, selected_folders)
    compute_nsm(folder_points, selected_folders, base_folder)
    compute_lrr(folder_points, selected_folders, base_folder)
    compute_epr(folder_points, selected_folders, base_folder)

    st.session_state["show_results"] = True  
    st.success("Calculations completed!")
    export_stats_to_csv(base_folder, line_name, selected_folders)


def compute_sce(folder_points, selected_folders):        
    data = []
    for profile_id in folder_points[selected_folders[0]]["profile_id"].unique():
        profile_points = []
        for folder in selected_folders:
            point = folder_points[folder][folder_points[folder]["profile_id"] == profile_id]
            if len(point) > 0:
                profile_points.append(point.geometry.iloc[0])  
        
        if len(profile_points) > 1:
            distances = [profile_points[i].distance(profile_points[j]) for i in range(len(profile_points)) for j in range(i+1, len(profile_points))]
            max_distance = max(distances)
            min_distance = min(distances)
            data.append([profile_id, max_distance, min_distance])
    
    df = pd.DataFrame(data, columns=["profile_id", "max_distance", "min_distance"])

    st.session_state["sce_df"] = df  

    total_transects = len(df)
    avg_distance = df["max_distance"].mean()
    max_distance = df["max_distance"].max()
    min_distance = df["min_distance"].min()
    max_transect_id = df[df["max_distance"] == max_distance]["profile_id"].values[0]
    min_transect_id = df[df["min_distance"] == min_distance]["profile_id"].values[0]

    with st.expander("Shoreline Change Envelope (SCE)"):
        st.write(f"Total number of transects: {total_transects}")
        st.write(f"Average distance: {avg_distance:.2f} m")
        st.write(f"Maximum distance: {max_distance:.2f} m (Transect ID: {max_transect_id})")
        st.write(f"Minimum distance: {min_distance:.2f} m (Transect ID: {min_transect_id})")
        st.write(st.session_state["sce_df"])

def compute_nsm(folder_points, selected_folders, base_folder):
    if len(selected_folders) < 2:
        st.error("NSM requires at least two folders for comparison.")
        return

    first_folder = selected_folders[0]
    last_folder = selected_folders[-1]

    first_gdf = folder_points.get(first_folder)
    last_gdf = folder_points.get(last_folder)

    if first_gdf is None or last_gdf is None:
        st.error("No data in selected folders.")
        return

    common_profiles = set(first_gdf["profile_id"]).intersection(set(last_gdf["profile_id"]))
    if not common_profiles:
        st.error("No common transects in selected folders.")
        return

    nsm_data = []
    for profile_id in common_profiles:
        first_point = first_gdf[first_gdf["profile_id"] == profile_id].geometry
        last_point = last_gdf[last_gdf["profile_id"] == profile_id].geometry

        if len(first_point) == 0 or len(last_point) == 0:
            st.warning(f"No points for the transect {profile_id}")
            continue

        nsm_distance = first_point.iloc[0].distance(last_point.iloc[0])

        direction = 1 if last_point.iloc[0].y > first_point.iloc[0].y else -1
        nsm_data.append([profile_id, direction * nsm_distance])

    if not nsm_data:
        st.warning("No data available to calculate NSM.")
        return

    nsm_df = pd.DataFrame(nsm_data, columns=["profile_id", "nsm_distance"])

    st.session_state["nsm_df"] = nsm_df 

    total_transects_nsm = len(nsm_df)
    avg_nsm = nsm_df["nsm_distance"].mean()
    max_nsm = nsm_df["nsm_distance"].max()
    min_nsm = nsm_df["nsm_distance"].min()

    max_nsm_transect_id = (
        nsm_df[nsm_df["nsm_distance"] == max_nsm]["profile_id"].values[0]
        if not nsm_df.empty and max_nsm in nsm_df["nsm_distance"].values
        else "No data"
    )
    min_nsm_transect_id = (
        nsm_df[nsm_df["nsm_distance"] == min_nsm]["profile_id"].values[0]
        if not nsm_df.empty and min_nsm in nsm_df["nsm_distance"].values
        else "No data"
    )

    with st.expander("Net Shoreline Movement (NSM)"):
        st.write(f"Total number of transects: {total_transects_nsm}")
        st.write(f"Average distance: {avg_nsm:.2f} m")
        st.write(f"Maximum distance: {max_nsm:.2f} m (Transect ID: {max_nsm_transect_id})")
        st.write(f"Minimum distance: {min_nsm:.2f} m (Transect ID: {min_nsm_transect_id})")
        st.write(st.session_state["nsm_df"])
    
        img_path = generate_nsm_image(nsm_df, base_folder, selected_folders)
        st.image(img_path, caption="", use_container_width=True)

def compute_lrr(folder_points, selected_folders, base_folder):
    if len(selected_folders) < 2:
        st.error("LRR requires at least two folders to compare.")
        return

    lrr_data = []
    r2_scores = []
    n_values = []

    for profile_id in folder_points[selected_folders[0]]["profile_id"].unique():
        x_values = []
        y_values = []

        for folder in selected_folders:
            point = folder_points[folder][folder_points[folder]["profile_id"] == profile_id]
            if len(point) > 0:
                match = re.search(r"\d{4}", folder)
                if match:
                    year = int(match.group())
                    x_values.append(year)
                    y_values.append(point.geometry.iloc[0].y)

        n = len(x_values)
        if n > 1:
            x_array = np.array(x_values).reshape(-1, 1)
            y_array = np.array(y_values)

            model = LinearRegression()
            model.fit(x_array, y_array)
            slope = model.coef_[0]

            y_pred = model.predict(x_array)
            ss_res = np.sum((y_array - y_pred) ** 2)
            ss_tot = np.sum((y_array - np.mean(y_array)) ** 2)
            r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

            lrr_data.append([profile_id, slope, n])
            r2_scores.append(r2)
            n_values.append(n)

    if not lrr_data:
        st.warning("No data available to calculate LRR.")
        return

    lrr_df = pd.DataFrame(lrr_data, columns=["profile_id", "LRR_rate", "n"])

    total_transects = len(lrr_df)
    avg_lrr = lrr_df["LRR_rate"].mean()
    avg_r2 = np.mean(r2_scores) if r2_scores else 0
    avg_n = np.mean(n_values)

    erosional_df = lrr_df[lrr_df["LRR_rate"] < 0]
    accretional_df = lrr_df[lrr_df["LRR_rate"] > 0]

    num_erosional = len(erosional_df)
    percent_erosional = (num_erosional / total_transects) * 100
    max_erosion = erosional_df["LRR_rate"].min() if not erosional_df.empty else "No data"
    max_erosion_id = erosional_df.loc[erosional_df["LRR_rate"] == max_erosion, "profile_id"].values[0] if not erosional_df.empty else "No data"
    avg_erosion_rate = erosional_df["LRR_rate"].mean() if not erosional_df.empty else "No data"

    num_accretional = len(accretional_df)
    percent_accretional = (num_accretional / total_transects) * 100
    max_accretion = accretional_df["LRR_rate"].max() if not accretional_df.empty else "No data"
    max_accretion_id = accretional_df.loc[accretional_df["LRR_rate"] == max_accretion, "profile_id"].values[0] if not accretional_df.empty else "No data"
    avg_accretion_rate = accretional_df["LRR_rate"].mean() if not accretional_df.empty else "No data"

    with st.expander("Linear Regression Rate (LRR)"):
        st.write(f"Total number of transects: {total_transects}")
        st.write(f"Average rate: {avg_lrr:.3f} m/yr")
        st.write(f"Average R²: {avg_r2:.3f}")
        st.write(f"Average number of years (n): {avg_n:.1f}")

        st.write("\n**Erosion Analysis**")
        st.write(f"Number of erosional transects: {num_erosional}")
        st.write(f"Percent of all transects that are erosional: {percent_erosional:.2f}%")
        st.write(f"Maximum erosion value: {max_erosion} m/yr (Transect ID: {max_erosion_id})")
        if isinstance(avg_erosion_rate, str):
            st.write(f"Average erosional rate: {avg_erosion_rate}")
        else:
            st.write(f"Average erosional rate: {avg_erosion_rate:.3f} m/yr")

        st.write("\n**Accretion Analysis**")
        st.write(f"Number of accretional transects: {num_accretional}")
        st.write(f"Percent of all transects that are accretional: {percent_accretional:.2f}%")
        st.write(f"Maximum accretion value: {max_accretion} m/yr (Transect ID: {max_accretion_id})")
        if isinstance(avg_accretion_rate, str):
            st.write(f"Average accretional rate: {avg_accretion_rate}")
        else:
            st.write(f"Average accretional rate: {avg_accretion_rate:.3f} m/yr")

        st.write(lrr_df)

        img_path = generate_lrr_image(lrr_df, base_folder, selected_folders)
        st.image(img_path, caption="", use_container_width=True)

    st.session_state["lrr_results"] = {row[0]: row[1] for row in lrr_data}
    st.session_state["lrr_df"] = lrr_df
    st.session_state["show_results"] = True


def generate_lrr_image(lrr_df, input_folder, selected_folders):
    fig, ax = plt.subplots(figsize=(10, 2))

    for idx, row in lrr_df.iterrows():
        color = "red" if row["LRR_rate"] < 0 else "green"
        ax.plot([idx, idx+1], [0, 0], color=color, linewidth=5)
        ax.text(idx + 0.5, 0.02, str(int(row["profile_id"])), ha="center", fontsize=8, color="black")

    ax.set_yticks([])
    ax.set_xticks([])
    folder_list_str = "_".join(selected_folders)
    ax.set_title(f"Visualisation of LRR changes for {', '.join(selected_folders)}")

    output_dir = os.path.join(input_folder, "stats", "output")
    os.makedirs(output_dir, exist_ok=True)
    img_path = os.path.join(output_dir, f"lrr_{folder_list_str}.png")

    try:
        plt.savefig(img_path)
        plt.close()
        return img_path
    except Exception as e:
        st.error(f"Image file write error: {e}")
        return None


def generate_nsm_image(nsm_df, input_folder, selected_folders):
    fig, ax = plt.subplots(figsize=(10, 2))

    for idx, row in nsm_df.iterrows():
        color = "red" if row["nsm_distance"] < 0 else "green"
        ax.plot([idx, idx+1], [0, 0], color=color, linewidth=5)

        ax.text(idx + 0.5, 0.02, str(int(row["profile_id"])), ha="center", fontsize=8, color="black")

    ax.set_yticks([])
    ax.set_xticks([])
    folder_list_str = "_".join(selected_folders)
    ax.set_title(f"Visualisation of NSM changes for {', '.join(selected_folders)}")

    output_dir = os.path.join(input_folder, "stats", "output")
    os.makedirs(output_dir, exist_ok=True)  
    img_path = os.path.join(output_dir, f"nsm_{folder_list_str}.png")

    try:
        plt.savefig(img_path)
        plt.close()
        return img_path 
    except Exception as e:
        st.error(f"Image file write error: {e}")
        return None  

def compute_epr(folder_points, selected_folders, base_folder):
    if len(selected_folders) < 2:
        st.error("EPR requires at least two folders to compare.")
        return

    first_folder = selected_folders[0]
    last_folder = selected_folders[-1]

    first_gdf = folder_points.get(first_folder)
    last_gdf = folder_points.get(last_folder)

    if first_gdf is None or last_gdf is None:
        st.error("No data in selected folders.")
        return

    match_first = re.search(r"\d{4}", first_folder)
    match_last = re.search(r"\d{4}", last_folder)

    if not match_first or not match_last:
        st.error("Years cannot be read from the folder names.")
        return

    year_first = int(match_first.group())
    year_last = int(match_last.group())
    num_years = year_last - year_first

    if num_years == 0:
        st.error("The EPR cannot be calculated – the difference in years is 0.")
        return

    epr_data = []
    for profile_id in first_gdf["profile_id"].unique():
        first_point = first_gdf[first_gdf["profile_id"] == profile_id].geometry
        last_point = last_gdf[last_gdf["profile_id"] == profile_id].geometry

        if len(first_point) == 0 or len(last_point) == 0:
            continue

        epr_value = first_point.iloc[0].distance(last_point.iloc[0]) / num_years
        direction = 1 if last_point.iloc[0].y > first_point.iloc[0].y else -1
        epr_data.append([profile_id, direction * epr_value])

    if not epr_data:
        st.warning("No data available to calculate EPR.")
        return

    epr_df = pd.DataFrame(epr_data, columns=["profile_id", "EPR_rate"])
    st.session_state["epr_df"] = epr_df  

    total_transects = len(epr_df)
    avg_epr = epr_df["EPR_rate"].mean()
    max_epr = epr_df["EPR_rate"].max()
    min_epr = epr_df["EPR_rate"].min()

    max_epr_transect_id = epr_df[epr_df["EPR_rate"] == max_epr]["profile_id"].values[0]
    min_epr_transect_id = epr_df[epr_df["EPR_rate"] == min_epr]["profile_id"].values[0]

    with st.expander("End Point Rate (EPR)"):
        st.write(f"Total number of transects: {total_transects}")
        
        if isinstance(avg_epr, str):
            st.write(f"Average rate: {avg_epr}")
        else:
            st.write(f"Average rate: {avg_epr:.3f} m/yr")

        if isinstance(max_epr, str):
            st.write(f"Maximum rate: {max_epr} (Transect ID: {max_epr_transect_id})")
        else:
            st.write(f"Maximum rate: {max_epr:.3f} m/yr (Transect ID: {max_epr_transect_id})")

        if isinstance(min_epr, str):
            st.write(f"Minimum rate: {min_epr} (Transect ID: {min_epr_transect_id})")
        else:
            st.write(f"Minimum rate: {min_epr:.3f} m/yr (Transect ID: {min_epr_transect_id})")

        st.write(st.session_state["epr_df"])

        img_path = generate_epr_image(epr_df, base_folder, selected_folders)
        st.image(img_path, caption="", use_container_width=True)

def generate_epr_image(epr_df, input_folder, selected_folders):
    fig, ax = plt.subplots(figsize=(10, 2))

    for idx, row in epr_df.iterrows():
        color = "red" if row["EPR_rate"] < 0 else "green"
        ax.plot([idx, idx+1], [0, 0], color=color, linewidth=5)

        ax.text(idx + 0.5, 0.02, str(int(row["profile_id"])), ha="center", fontsize=8, color="black")

    ax.set_yticks([])
    ax.set_xticks([])
    folder_list_str = "_".join(selected_folders)
    ax.set_title(f"Visualisation of EPR changes for {', '.join(selected_folders)}")

    output_dir = os.path.join(input_folder, "stats", "output")
    os.makedirs(output_dir, exist_ok=True)  
    img_path = os.path.join(output_dir, f"epr_{folder_list_str}.png")

    try:
        plt.savefig(img_path)
        plt.close()
        return img_path 
    except Exception as e:
        st.error(f"Image file saving error: {e}")
        return None  


def export_stats_to_csv(base_folder, line_name, selected_folders):

    output_dir = os.path.join(base_folder, "stats", "csv")
    os.makedirs(output_dir, exist_ok=True)

    base_name = line_name.replace(".geojson", "").replace("Line", "").lower()
    suffix = "_".join(selected_folders)

    combined_df = []

    def export_and_append(df, method_name):
        df = df.copy()
        df["method"] = method_name
        df["line"] = base_name
        df["from"] = selected_folders[0]
        df["to"] = selected_folders[-1]
        df.to_csv(os.path.join(output_dir, f"{method_name.lower()}_{base_name}_{suffix}.csv"), index=False)
        combined_df.append(df)

    for method_key, method_name in [
        ("sce_df", "SCE"),
        ("nsm_df", "NSM"),
        ("lrr_df", "LRR"),
        ("epr_df", "EPR")
    ]:
        if method_key in st.session_state:
            export_and_append(st.session_state[method_key], method_name)

    # Merged horizontaly (wide)
    try:
        df_sce = st.session_state["sce_df"][["profile_id", "max_distance", "min_distance"]] if "sce_df" in st.session_state else None
        df_nsm = st.session_state["nsm_df"][["profile_id", "nsm_distance"]] if "nsm_df" in st.session_state else None
        df_lrr = st.session_state["lrr_df"][["profile_id", "LRR_rate", "n"]].rename(columns={"LRR_rate": "lrr_rate"}) if "lrr_df" in st.session_state else None
        df_epr = st.session_state["epr_df"][["profile_id", "EPR_rate"]].rename(columns={"EPR_rate": "epr_rate"}) if "epr_df" in st.session_state else None

        df_merged = None
        for df in [df_sce, df_nsm, df_lrr, df_epr]:
            if df is not None:
                df_merged = df if df_merged is None else df_merged.merge(df, on="profile_id", how="outer")

        if df_merged is not None:
            df_merged["line"] = base_name
            df_merged["from"] = selected_folders[0]
            df_merged["to"] = selected_folders[-1]
            merged_path = os.path.join(output_dir, f"merged_stats_{base_name}_{suffix}.csv")
            df_merged.to_csv(merged_path, index=False)
            st.success("Statistics merged horizontally and saved.")
        else:
            st.warning("No data available to merge horizontally.")
    except Exception as e:
        st.error(f"Failed to merge statistics (wide): {e}")

    # Merged verticaly (tidy format)
    try:
        tidy_df_list = []

        if "lrr_df" in st.session_state:
            df = st.session_state["lrr_df"][["profile_id", "LRR_rate"]].copy()
            df["method"] = "LRR"
            df = df.rename(columns={"LRR_rate": "value"})
            df["metric"] = "lrr_rate"
            tidy_df_list.append(df)

        if "epr_df" in st.session_state:
            df = st.session_state["epr_df"][["profile_id", "EPR_rate"]].copy()
            df["method"] = "EPR"
            df = df.rename(columns={"EPR_rate": "value"})
            df["metric"] = "epr_rate"
            tidy_df_list.append(df)

        if "sce_df" in st.session_state:
            df = st.session_state["sce_df"][["profile_id", "max_distance", "min_distance"]].copy()
            for col in ["max_distance", "min_distance"]:
                temp = df[["profile_id"]].copy()
                temp["value"] = df[col]
                temp["metric"] = col
                temp["method"] = "SCE"
                tidy_df_list.append(temp)

        if "nsm_df" in st.session_state:
            df = st.session_state["nsm_df"][["profile_id", "nsm_distance"]].copy()
            df["value"] = df["nsm_distance"]
            df["metric"] = "nsm_distance"
            df["method"] = "NSM"
            tidy_df_list.append(df[["profile_id", "value", "metric", "method"]])

        if tidy_df_list:
            tidy_df = pd.concat(tidy_df_list, ignore_index=True)
            tidy_df["line"] = base_name
            tidy_df["from"] = selected_folders[0]
            tidy_df["to"] = selected_folders[-1]
            tidy_path = os.path.join(output_dir, f"tidy_stats_{base_name}_{suffix}.csv")
            tidy_df.to_csv(tidy_path, index=False)
            st.success("Tidy (ML-friendly) version of statistics saved.")
        else:
            st.warning("No data available to export in tidy format.")
    except Exception as e:
        st.error(f"Failed to create tidy version: {e}")




