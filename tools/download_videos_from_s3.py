#!/usr/bin/env python3
"""Download videos from LocalStack S3 to local directory."""

from pathlib import Path
from _config import S3_BUCKET, S3_PREFIX, DATA_DIR, get_s3_client

s3_client = get_s3_client(use_docker_endpoint=False)
local_dir = Path(DATA_DIR) / 'downloads'

local_dir.mkdir(parents=True, exist_ok=True)

print(f"Listing videos from s3://{S3_BUCKET}/{S3_PREFIX}")
paginator = s3_client.get_paginator('list_objects_v2')
video_count = 0

for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_PREFIX):
    if 'Contents' in page:
        for obj in page['Contents']:
            key = obj['Key']
            filename = key.split('/')[-1]
            local_path = local_dir / filename

            print(f"[{video_count + 1:3d}] Downloading {filename}...")
            s3_client.download_file(S3_BUCKET, key, str(local_path))
            video_count += 1

print(f"\nDownloaded {video_count} videos to {local_dir}/")
