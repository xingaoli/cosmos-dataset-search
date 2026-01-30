#!/usr/bin/env python3
"""Upload transcoded H.264 videos to S3."""

import boto3
from pathlib import Path

# list s3 storage
# aws s3 ls s3://cosmos-test-bucket/videos/

# Initialize S3 client
s3_client = boto3.client(
    's3',
    endpoint_url='http://localstack:4566',
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name='us-east-1'
)

# Configuration
H264_DIR = Path('cds-data/phaa1000/h264')
BUCKET = 'cosmos-test-bucket'
PREFIX = 'phaa1000/h264'

# Find all transcoded videos
video_files = sorted(H264_DIR.glob('*.mp4'))

if not video_files:
    print(f"❌ No videos found in {H264_DIR}")
    print("Please run batch_transcode.py first!")
    exit(1)

print(f"{'='*60}")
print(f"Upload H.264 Videos to S3")
print(f"{'='*60}")
print(f"Source: {H264_DIR}")
print(f"Destination: s3://{BUCKET}/{PREFIX}/")
print(f"Total videos: {len(video_files)}")
print(f"{'='*60}\n")

# Upload each video
for i, video_file in enumerate(video_files, 1):
    key = f"{PREFIX}/{video_file.name}"

    print(f"[{i:3d}/{len(video_files)}] Uploading {video_file.name}...")

    try:
        s3_client.upload_file(str(video_file), BUCKET, key)
        size_mb = video_file.stat().st_size / 1024 / 1024
        print(f"  ✓ Uploaded ({size_mb:.2f} MB)")
    except Exception as e:
        print(f"  ✗ Failed: {e}")

# Verify uploads
print(f"\n{'='*60}")
print(f"Verifying uploads...")
print(f"{'='*60}")

response = s3_client.list_objects_v2(Bucket=BUCKET, Prefix=PREFIX)
if 'Contents' in response:
    uploaded_count = len([obj for obj in response['Contents'] if obj['Key'].endswith('.mp4')])
    print(f"✓ {uploaded_count} videos found in s3://{BUCKET}/{PREFIX}/")
else:
    print("✗ No videos found in S3!")

print(f"\n✅ Upload complete!")
print(f"You can now use these videos with URL format ingestion.")
