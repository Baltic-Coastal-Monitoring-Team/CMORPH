# -*- coding: utf-8 -*-
"""
Created on 05-2025
@author: ałysko, pforczmański, wmackow, jsledziowski
geopackage database.gpkg can be opened in QGIS
"""

import sys
import json
import pgen

# Check if running in GUI mode (streamlit subprocess)
IS_GUI = "--gui" in sys.argv

# ANSI color codes
YELLOW = "\033[93m"
RESET = "\033[0m"
RED = "\033[91m"

# get config
with open("config.json", "r") as jsonfile:
    config = json.load(jsonfile)

try:
    # check input and db paths and create output paths
    print(f"{YELLOW}... initializing data structures{RESET}")
    pgen.init(config)

    # generate or load transects
    print(f"{YELLOW}... generating transects{RESET}")
    pgen.generate_transects(config)

    # get DEM around transects
    print(f"{YELLOW}... preparing cropped DEM rasters{RESET}")
    pgen.get_DEM(config)

    # generate profiles
    print(f"{YELLOW}... generating profiles{RESET}")
    pgen.generate_profiles(config)

    # crop profiles
    print(f"{YELLOW}... cropping profiles{RESET}")
    pgen.crop_profiles(config)

    sys.exit(0)

except Exception as e:
    print(f"{RED}{type(e)}: {e}{RESET}")
    sys.exit(1)
