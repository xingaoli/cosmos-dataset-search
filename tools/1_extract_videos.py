#!/usr/bin/env python3
"""
提取视频文件从zip压缩包到指定目录
"""

import zipfile
import os
import glob
from pathlib import Path

# 源zip文件目录（支持多个压缩包）
ZIP_DIR = "/home/xingao/data/PhysicalAI-Autonomous-Vehicles-base-wo-lidar-radar/camera/camera_front_wide_120fov/"

# 目标目录
OUTPUT_DIR = "./cds-data/phaa1000/h265"

def extract_videos():
    """从zip文件中提取所有视频到目标目录"""
    # 创建目标目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 获取所有zip文件
    zip_files = sorted(glob.glob(os.path.join(ZIP_DIR, "*.zip")))
    print(f"找到 {len(zip_files)} 个压缩包")

    total_videos = 0
    for zip_path in zip_files:
        zip_name = os.path.basename(zip_path)
        print(f"\n正在解压: {zip_name}")
        print(f"目标目录: {OUTPUT_DIR}")

        # 打开zip文件
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # 列出zip中的所有文件
            file_list = zip_ref.namelist()
            video_count = sum(1 for f in file_list if f.endswith('.mp4'))
            print(f"  压缩包中共有 {len(file_list)} 个文件，其中 {video_count} 个视频")

            # 解压所有文件
            for file in file_list:
                # 只解压视频文件（.mp4, .mkv等）
                if any(file.endswith(ext) for ext in ['.mp4', '.mkv', '.avi', '.mov', '.h265', '.hevc']):
                    zip_ref.extract(file, OUTPUT_DIR)
                    total_videos += 1

    print(f"\n✓ 提取完成！共提取 {total_videos} 个视频，保存到: {OUTPUT_DIR}")

if __name__ == "__main__":
    extract_videos()
