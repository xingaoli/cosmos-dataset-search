#!/usr/bin/env python3
"""Download videos from LocalStack S3 to local cds-data directory."""

import os
import boto3
from pathlib import Path

# Initialize S3 client
s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:4566',
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name='us-east-1'
)

bucket = 'cosmos-test-bucket'
prefix = 'videos/'
local_dir = Path('cds-data/videos')

# Create local directory
local_dir.mkdir(parents=True, exist_ok=True)

# List all videos
print(f"Listing videos from s3://{bucket}/{prefix}")
paginator = s3_client.get_paginator('list_objects_v2')
video_count = 0

for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
    if 'Contents' in page:
        for obj in page['Contents']:
            key = obj['Key']
            filename = key.split('/')[-1]

            # Download video
            local_path = local_dir / filename
            print(f"[{video_count + 1:3d}/100] Downloading {filename}...")

            s3_client.download_file(bucket, key, str(local_path))
            video_count += 1

print(f"\n✓ Downloaded {video_count} videos to {local_dir}/")
