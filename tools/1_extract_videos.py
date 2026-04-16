#!/usr/bin/env python3
"""Extract videos from zip files."""

import zipfile
import os
import glob
from _config import ZIP_DIR, EXTRACT_OUTPUT_DIR

if not ZIP_DIR:
    print("ERROR: Set TOOLS_ZIP_DIR in deploy/standalone/.env")
    exit(1)

def extract_videos():
    os.makedirs(EXTRACT_OUTPUT_DIR, exist_ok=True)

    zip_files = sorted(glob.glob(os.path.join(ZIP_DIR, "*.zip")))
    print(f"Found {len(zip_files)} zip files")

    total_videos = 0
    for zip_path in zip_files:
        zip_name = os.path.basename(zip_path)
        print(f"\nExtracting: {zip_name}")
        print(f"  Target: {EXTRACT_OUTPUT_DIR}")

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            video_count = sum(1 for f in file_list if f.endswith('.mp4'))
            print(f"  {len(file_list)} files, {video_count} videos")

            for file in file_list:
                if any(file.endswith(ext) for ext in ['.mp4', '.mkv', '.avi', '.mov', '.h265', '.hevc']):
                    zip_ref.extract(file, EXTRACT_OUTPUT_DIR)
                    total_videos += 1

    print(f"\nDone! {total_videos} videos extracted to: {EXTRACT_OUTPUT_DIR}")

if __name__ == "__main__":
    extract_videos()
