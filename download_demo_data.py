import os
import zipfile
import requests
from pathlib import Path

DATASETS = [
    "2021-02",
    "2022-02",
    "2023-02",
    "2024-02",
    "2024-05",
]

BASE_URL = "https://zenodo.org/records/15476933/files"
DEST_DIR = Path("demo")


def download_file(url, out_path):
    print(f"[⬇] Downloading {url}")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def extract_zip(zip_path, extract_to):
    print(f"[📦] Extracting {zip_path.name}")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)
    zip_path.unlink()  


def main():
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    for dataset in DATASETS:
        zip_name = f"{dataset}.zip"
        url = f"{BASE_URL}/{zip_name}?download=1"
        zip_path = DEST_DIR / zip_name

        try:
            download_file(url, zip_path)
            extract_zip(zip_path, DEST_DIR)
        except Exception as e:
            print(f"[❌] Failed for {dataset}: {e}")
    print("[✅] All demo data ready in ./demo/")


if __name__ == "__main__":
    main()
