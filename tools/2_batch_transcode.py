#!/usr/bin/env python3
"""Batch transcode videos from HEVC to H.264 for cosmos-embed compatibility."""

import subprocess
import os
from pathlib import Path
import time

# Configuration
SOURCE_DIR = Path('cds-data/phaa1000')
OUTPUT_DIR = SOURCE_DIR / 'h264'
INPUT_DIR = SOURCE_DIR / 'h265'

VIDEO_FILES = sorted(INPUT_DIR.glob('*.mp4'))

# Create output directory
OUTPUT_DIR.mkdir(exist_ok=True)

print(f"{'='*60}")
print(f"Batch Video Transcoding: HEVC → H.264")
print(f"{'='*60}")
print(f"Source: {SOURCE_DIR}")
print(f"Output: {OUTPUT_DIR}")
print(f"Total videos: {len(VIDEO_FILES)}")
print(f"{'='*60}\n")

# Check if already transcoded
already_done = len(list(OUTPUT_DIR.glob('*.mp4')))
if already_done > 0:
    print(f"Found {already_done} already transcoded videos. Will skip them.")

# Transcoding function
def transcode_video(input_file: Path, output_file: Path) -> bool:
    """Transcode video to H.264 using ffmpeg."""
    try:
        subprocess.run([
            'ffmpeg', '-i', str(input_file),
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-vf', 'scale=1280:720',
            '-c:a', 'aac', '-b:a', '128k',
            '-y', str(output_file)
        ], capture_output=True, check=True, timeout=300)
        return True
    except subprocess.TimeoutExpired:
        print(f"  ✗ Timeout after 300s")
        return False
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed: {e}")
        return False

# Process each video
start_time = time.time()
success_count = 0
failed_count = 0
skipped_count = 0

for i, video_file in enumerate(VIDEO_FILES, 1):
    output_file = OUTPUT_DIR / video_file.name

    # Skip if already exists
    if output_file.exists():
        print(f"[{i:3d}/{len(VIDEO_FILES)}] ✓ {video_file.name} (already exists)")
        skipped_count += 1
        continue

    print(f"[{i:3d}/{len(VIDEO_FILES)}] Transcoding {video_file.name}...")

    video_start = time.time()
    success = transcode_video(video_file, output_file)
    elapsed = time.time() - video_start

    if success:
        success_count += 1
        input_size = video_file.stat().st_size / 1024 / 1024
        output_size = output_file.stat().st_size / 1024 / 1024
        print(f"  ✓ Done in {elapsed:.1f}s ({input_size:.2f}MB → {output_size:.2f}MB)")
    else:
        failed_count += 1

# Summary
total_elapsed = time.time() - start_time
print(f"\n{'='*60}")
print(f"Transcoding Summary")
print(f"{'='*60}")
print(f"Total videos: {len(VIDEO_FILES)}")
print(f"Success: {success_count}")
print(f"Failed: {failed_count}")
print(f"Skipped: {skipped_count}")
print(f"Total time: {total_elapsed/60:.1f} minutes")
if success_count > 0:
    print(f"Average speed: {total_elapsed/success_count:.1f}s/video")
print(f"{'='*60}")

if failed_count > 0:
    print(f"\n⚠️  {failed_count} videos failed to transcode")
    print(f"Check the videos manually - they may be corrupted or unsupported format")

print(f"\n✅ Transcoded videos saved to: {OUTPUT_DIR}")
print(f"Next step: Upload to S3 using upload_h264_to_s3.py")
