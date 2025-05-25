import os
import subprocess
import json
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import sys
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "tools/finder-py/config.json")

def load_config():
    """Loads configuration from JSON file."""
    with open(CONFIG_PATH, "r") as file:
        return json.load(file)

def save_config(config):
    """Saves the configuration to a JSON file."""
    with open(CONFIG_PATH, "w") as file:
        json.dump(config, file, indent=4)

def strip_ansi_codes(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def run_finder():
    """Starts Finder with configuration verification."""
    try:
        finder_dir = os.path.join(BASE_DIR, "tools/finder-py")
        process = subprocess.Popen(
            [sys.executable, "main.py", "--gui"],
            cwd=finder_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout_lines = []
        stderr_lines = []

        # Stream output in real-time
        for line in process.stdout:
            clean_line = strip_ansi_codes(line).strip()
            if clean_line and "it/s" not in clean_line:  # filtrujemy tqdm
                stdout_lines.append(clean_line)

        for err in process.stderr:
            clean_err = strip_ansi_codes(err).strip()
            if clean_err:
                stderr_lines.append(clean_err)

        process.wait()

        if stdout_lines:
            st.code("\n".join(stdout_lines), language="bash")

        if stderr_lines:
            for line in stderr_lines:
                st.error(line)

        if process.returncode == 0:
            st.success("Finder process completed successfully")
        else:
            st.error("Finder ended with an error")

    except Exception as e:
        st.error(f"Error while launching Finder: {e}")


def finder_ui():
    st.title("Finder")

    subpage = st.sidebar.radio("Finder:", ["Config", "Results"], key="finder_submenu")

    config = load_config()

    if subpage == "Config":
        st.subheader("Finder Config")

        st.subheader("Paths")
        config["paths"]["base"] = st.text_input("Base Path", value=config["paths"]["base"])
        config["paths"]["input"]["profiles"] = st.text_input("Input Profiles Path", value=config["paths"]["input"]["profiles"])
        config["paths"]["output"]["results"] = st.text_area(
            "Output Results Paths (one per line)", value="\n".join(config["paths"]["output"]["results"])
        ).splitlines()

        #st.subheader("CSV Settings")
        #config["csv"]["sep"] = st.text_input("CSV Separator", value=config["csv"].get("sep", ","))

        config["min_profile_points"] = st.number_input("Min Profile Points", value=config.get("min_profile_points", 10), step=1)
        config["elevation_zero"] = st.number_input("Elevation Zero", value=config.get("elevation_zero", 0.5), step=0.1)
        config["beyond_top_buffer"] = st.number_input("Beyond Top Buffer", value=config.get("beyond_top_buffer", 10), step=1)
        #config["method"] = st.number_input("Method", value=config.get("method", 2), step=1)

        if st.button("Save configuration"):
            save_config(config)
            st.success("Configuration saved!")

        if st.button("Run Finder"):
            st.info("Running Findera...")
            run_finder()

    elif subpage == "Results":
        st.subheader("Finder results")

        from pathlib import Path

        base_path = config["paths"]["base"]
        if os.path.isabs(base_path):
            resolved_base = Path(base_path).resolve()
        else:
            resolved_base = (Path(CONFIG_PATH).parent / base_path).resolve()

        raw_path = Path(config["paths"]["output"]["results"][0])
        result_file = (resolved_base / raw_path).resolve()

        st.code(f"Result file: {result_file}")

        if result_file.exists():
            try:
                df = pd.read_csv(result_file)
                st.write("Results content:")
                st.dataframe(df)

                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="finder.csv",
                    mime="text/csv",
                )

                st.subheader("Quick charts for profiles ID")
                for _, row in df.iterrows():
                    profile_id = row["profile_id"]
                    points = []
                    labels = []
                    colors = ["red", "blue", "green", "orange"]

                    if row["first_zero"] != row["last_zero"]:
                        points.extend([row["first_zero"], row["last_zero"]])
                        labels.extend(["first_zero", "last_zero"])
                    else:
                        points.append(row["first_zero"])
                        labels.append("first_zero")

                    points.extend([row["bottom"], row["top"]])
                    labels.extend(["bottom", "top"])

                    y_values = [1] * len(points)

                    st.markdown(f"**Profile ID: {profile_id}**")
                    fig, ax = plt.subplots(figsize=(8, 1))

                    for x, y, label, color in zip(points, y_values, labels, colors[:len(points)]):
                        ax.scatter(x, y, color=color)
                        ax.text(x, y + 0.01, label, ha="center", fontsize=10, color=color)

                    ax.plot(points, y_values, linestyle="--", color="gray")
                    ax.set_xlim(min(df[["first_zero", "last_zero", "bottom", "top"]].min()) - 5,
                                max(df[["first_zero", "last_zero", "bottom", "top"]].max()) + 5)
                    ax.set_yticks([])
                    ax.set_xlabel("Value")
                    ax.grid(axis="x")
                    st.pyplot(fig)

                st.subheader("All profiles")
                water_position = st.radio("Select the waterline position:", ["Water in the north", "Water in the south"])

                fig, ax = plt.subplots(figsize=(12, 6))

                for column, color in zip(["first_zero", "last_zero", "bottom", "top"], ["red", "blue", "green", "orange"]):
                    if column == "last_zero" and (df["first_zero"] == df["last_zero"]).all():
                        continue
                    ax.plot(df["profile_id"], df[column], label=column, color=color, marker="o")

                ax.set_xlabel("Profile ID")
                ax.set_ylabel("Value")

                if water_position == "Water in the north":
                    ax.invert_yaxis()

                ax.set_title("Value changes in profiles")
                ax.legend()
                ax.grid(True)
                st.pyplot(fig)

            except Exception as e:
                st.error(f"Unable to load result file: {e}")
        else:
            st.warning(f"The result file was not found at: `{result_file}`. Make sure that Finder is running.")





