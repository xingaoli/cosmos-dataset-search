#!/usr/bin/env python3
"""Upload videos to S3."""

from pathlib import Path
from _config import EXTRACT_OUTPUT_DIR, S3_BUCKET, S3_PREFIX, get_s3_client

s3_client = get_s3_client(use_docker_endpoint=False)

H264_DIR = Path(EXTRACT_OUTPUT_DIR)

video_files = sorted(H264_DIR.glob('*.mp4'))

if not video_files:
    print(f"No videos found in {H264_DIR}")
    print("Please run tools/1_extract_videos.py first!")
    exit(1)

print(f"{'='*60}")
print(f"Upload Videos to S3")
print(f"{'='*60}")
print(f"Source: {H264_DIR}")
print(f"Destination: s3://{S3_BUCKET}/{S3_PREFIX}/")
print(f"Total videos: {len(video_files)}")
print(f"{'='*60}\n")

for i, video_file in enumerate(video_files, 1):
    key = f"{S3_PREFIX}/{video_file.name}"

    print(f"[{i:3d}/{len(video_files)}] Uploading {video_file.name}...")

    try:
        s3_client.upload_file(str(video_file), S3_BUCKET, key)
        size_mb = video_file.stat().st_size / 1024 / 1024
        print(f"  + Uploaded ({size_mb:.2f} MB)")
    except Exception as e:
        print(f"  x Failed: {e}")

# Verify uploads
print(f"\n{'='*60}")
print(f"Verifying uploads...")
print(f"{'='*60}")

response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=S3_PREFIX)
if 'Contents' in response:
    uploaded_count = len([obj for obj in response['Contents'] if obj['Key'].endswith('.mp4')])
    print(f"+ {uploaded_count} videos found in s3://{S3_BUCKET}/{S3_PREFIX}/")
else:
    print("x No videos found in S3!")

print(f"\nUpload complete!")
