import sys
import re
import json
import glob
from natsort import natsorted
import pandas as pd
import numpy as np
from os.path import join, basename
from tqdm import tqdm

from finder import smooth_profile, get_main_points, get_zero_points

# Check if running in GUI mode (streamlit subprocess)
IS_GUI = "--gui" in sys.argv

# ANSI color codes
YELLOW = "\033[93m"
RESET = "\033[0m"

pd.options.mode.chained_assignment = None

try:
    # get config
    with open("config.json", "r") as jsonfile:
        config = json.load(jsonfile)

    profile_input_path = join(
        config["paths"]["base"], config["paths"]["input"]["profiles"]
    )

    csv_sep = config["csv"]["sep"]
    method = config["method"]
    elevation_zero = config["elevation_zero"]

    # all or selected profiles?
    selected = True if len(config["selected_profiles"]) > 0 else False

    # list of obtained results
    results = []

    # list profile files
    profile_files = natsorted(glob.glob(f"{profile_input_path}/*.csv"))
    profile_files_count = len(profile_files)
    # counter = 0

    print(f"{YELLOW}... looking for the base and top of profiles{RESET}")

    if IS_GUI:
        profile_iterator = enumerate(profile_files, 1)
    else:
        profile_iterator = tqdm(enumerate(profile_files, 1), total=len(profile_files), desc="... all profiles")

    for idx, name in profile_iterator:
        if IS_GUI:
            print(f"... processing profile {idx}/{len(profile_files)}")

        # get profile number from file name
        profile_id = int(re.findall(r"\d{1,4}", basename(name))[0])

        if selected and profile_id not in config["selected_profiles"]:
            continue

        csv = pd.read_csv(name, encoding="utf-8", sep=csv_sep, skipinitialspace=True)
        cut = csv[csv["id"] > 0]
        if len(cut) == 0:
            continue

        first_no = cut.iloc[0]["no_point"].astype(int).item()
        buffer = config["beyond_top_buffer"] if method == 2 else 0
        highest_point = cut.elevation.idxmax().astype(int).item() + buffer
        last_point = cut["no_point"].iloc[-1]
        last_no = last_point if highest_point > last_point else highest_point

        zero_result = get_zero_points(
            csv,
            first_no,
            last_no,
            elevation_zero,
            min_profile_points=config["min_profile_points"],
        )
        if first_no < zero_result["last"]:
            first_no = zero_result["last"]

        if config["smoothness"]["profile"]:
            smooth = smooth_profile(csv, first_no, last_no)
            if smooth is not None:
                csv.elevation[first_no:last_no] = np.array(smooth)
            else:
                continue

        if method == 2:
            result = get_main_points(
                csv,
                first_no,
                last_no,
                method=2,
                min_profile_points=config["min_profile_points"],
            )

        results.append(
            {
                "profile_id": profile_id,
                "method": method,
                "profile_smooth": config["smoothness"]["profile"],
                "first_zero": zero_result["first"],
                "last_zero": zero_result["last"],
                "bottom": result["bottom"],
                "top": result["top"],
            }
        )


    results = pd.DataFrame(results)

    # export results to CSV file/files (all profiles together)
    print(f"{YELLOW}... exporting CSV data{RESET}")
    output = config["paths"]["output"]["results"]
    files = output if isinstance(output, list) else [output]
    for file in files:
        file = join(config["paths"]["base"], file)
        results.to_csv(file, sep=csv_sep, index=False, encoding="utf-8")
    sys.exit(0)

except Exception as e:
    print(f"{type(e)}: {e}")
    sys.exit(1)
