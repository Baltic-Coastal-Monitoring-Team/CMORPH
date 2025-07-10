
import importlib
import os
from pathlib import Path

REQUIRED_PACKAGES = [
    "gdal",
    "rasterio",
    "geopandas",
    "shapely",
    "pyproj",
    "fiona",
    "earthpy",
    "streamlit",
    "seaborn",
    "xgboost",
    "natsort",
    "copernicusmarine",
    "imageio",
    "cv2",
    "folium",
    "altair",
    "pydeck",
    "pygeopkg",
    "pyogrio",
    "richdem",
    "halo",
]

REQUIRED_DEMO_FOLDERS = [
    "2021-02/input",
    "2022-02/input",
    "2023-02/input",
    "2024-02/input",
    "2024-05/input"
]

def check_packages():
    print("Checking Python packages...\n")
    missing = []
    for pkg in REQUIRED_PACKAGES:
        if pkg == "gdal":
            try:
                from osgeo import gdal
                print("✅ gdal (via osgeo)")
            except ImportError:
                print("❌ gdal not installed (missing osgeo.gdal)")
                missing.append("gdal")
        else:
            try:
                importlib.import_module(pkg)
                print(f"✅ {pkg}")
            except ImportError:
                print(f"❌ {pkg} not installed")
                missing.append(pkg)
    return missing


def check_demo_structure():
    print("\n Checking demo folder structure...\n")
    demo_root = Path("demo")
    missing = []
    for folder in REQUIRED_DEMO_FOLDERS:
        path = demo_root / folder
        if path.exists() and path.is_dir():
            print(f"✅ {folder}")
        else:
            print(f"❌ Missing: {folder}")
            missing.append(folder)
    return missing

if __name__ == "__main__":
    print("CMORPH Post-Installation Check\n")

    missing_pkgs = check_packages()
    missing_folders = check_demo_structure()

    if not missing_pkgs and not missing_folders:
        print("\n All checks passed. CMORPH is ready to use.")
    else:
        print("\n⚠️ Some issues were found:")
        if missing_pkgs:
            print(f" - Missing packages: {', '.join(missing_pkgs)}")
        if missing_folders:
            print(f" - Missing folders in ./demo/: {', '.join(missing_folders)}")

