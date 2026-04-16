"""Ingest videos with on-the-fly H.265->H.264 transcoding."""
import requests
import time
import json
import traceback
from _config import (
    COLLECTION_ID, S3_BUCKET, S3_PREFIX, API_BASE,
    TRANSCODE_PROXY_DOCKER, TRANSCODE_PROXY_HOST,
    get_s3_client,
)

if not COLLECTION_ID:
    print("ERROR: Set TOOLS_COLLECTION_ID in deploy/standalone/.env")
    print("  Run tools/5_create_collection.py first to get the ID")
    exit(1)

s3_client = get_s3_client(use_docker_endpoint=False)

print(f"Listing all .mp4 files in s3://{S3_BUCKET}/{S3_PREFIX}/")

paginator = s3_client.get_paginator('list_objects_v2')
video_files = []
for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_PREFIX):
    if 'Contents' in page:
        for obj in page['Contents']:
            key = obj['Key']
            if key.lower().endswith('.mp4'):
                video_files.append(key)
print(f"Found {len(video_files)} MP4 files.")

if not video_files:
    print("No MP4 files found. Exiting.")
    exit(1)

# Test that transcode proxy is reachable
print("Testing transcode proxy...")
test_key = video_files[0]
test_url = f"{TRANSCODE_PROXY_HOST}/transcode?key={test_key}"
try:
    test_response = requests.head(test_url, timeout=10)
    print(f"+ Transcode proxy is reachable (status: {test_response.status_code})")
except requests.exceptions.ConnectionError:
    print(f"x Cannot reach transcode proxy at {TRANSCODE_PROXY_HOST}")
    print("  Start it first: make test-integration-up")
    exit(1)
except Exception as e:
    print(f"Warning: {e}")
    print("  Continuing anyway...")

# Generate documents with transcode proxy URLs
documents = []

print(f"\nPreparing {len(video_files)} video(s) for on-the-fly transcoding...")

for key in video_files:
    filename = key.split('/')[-1]
    transcode_url = f"{TRANSCODE_PROXY_DOCKER}/transcode?key={key}"

    documents.append({
        'url': transcode_url,
        'mime_type': 'video/mp4',
        'metadata': {'filename': filename}
    })

    print(f"  + {filename}")

print(f"\n{'='*60}")
print(f"Prepared {len(documents)} video(s) for ingestion (on-the-fly H.265->H.264)")
print(f"{'='*60}")

if len(documents) > 0:
    print(f"\nFirst document preview:")
    print(json.dumps(documents[0], indent=2))
else:
    print("\nNo documents prepared. Exiting.")
    exit(1)

print(f"\n{'='*60}")
print(f"Starting video ingestion via REST API...")
print(f"{'='*60}")
BATCH_SIZE = 3
total_ingested = 0
total_batches = (len(documents) - 1) // BATCH_SIZE + 1
print(f"Total videos: {len(documents)}")
print(f"Batch size: {BATCH_SIZE}")
print(f"Total batches: {total_batches}")
for i in range(0, len(documents), BATCH_SIZE):
    batch = documents[i:i + BATCH_SIZE]
    batch_num = i // BATCH_SIZE + 1

    print(f"\n{'─'*60}")
    print(f"Batch {batch_num}/{total_batches} ({len(batch)} video(s))")
    print(f"{'─'*60}")
    print(f"Starting request...")

    start_time = time.time()

    try:
        response = requests.post(
            f"{API_BASE}/collections/{COLLECTION_ID}/documents",
            json=batch,
            timeout=300
        )

        elapsed_time = time.time() - start_time
        print(f"Request completed in {elapsed_time:.1f} seconds")

        if response.status_code == 200:
            result = response.json()
            ingested_count = len(result.get('documents', []))
            total_ingested += ingested_count

            if elapsed_time > 0:
                videos_per_min = (ingested_count / elapsed_time) * 60
                print(f"+ Batch {batch_num} succeeded: {ingested_count} video(s)")
                print(f"  Speed: {videos_per_min:.2f} videos/minute")

            if ingested_count > 0:
                doc_ids = [d['id'][:16] + '...' for d in result['documents'][:3]]
                print(f"  Document IDs: {doc_ids}")
                if ingested_count > 3:
                    print(f"  ... and {ingested_count - 3} more")
        else:
            print(f"x Batch {batch_num} failed with status code: {response.status_code}")
            print(f"  Response: {response.text[:500]}")

            if response.status_code == 500:
                print("\nTip: Check container logs:")
                print("   docker logs visual-search --tail 50")
                print("   docker logs cosmos-embed --tail 50")

            print("\nContinuing with next batch...")

    except requests.exceptions.Timeout:
        elapsed_time = time.time() - start_time
        print(f"x Batch {batch_num} timed out after {elapsed_time:.1f} seconds")
        print("\nSuggestions:")
        print("   1. Check cosmos-embed: docker logs cosmos-embed --tail 50")
        print("   2. Check GPU usage: nvidia-smi")
        print("   3. Check transcode proxy: docker logs transcode-proxy --tail 50")
        continue
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"Batch {batch_num} exception after {elapsed_time:.1f}s: {type(e).__name__}")
        print(f"  Error: {e}")
        traceback.print_exc()
        continue

print(f"\n{'='*60}")
print(f"Ingestion Summary")
print(f"{'='*60}")
print(f"Total videos prepared: {len(documents)}")
print(f"Total videos ingested: {total_ingested}")
print(f"Success rate: {total_ingested}/{len(documents)} ({100*total_ingested/len(documents) if len(documents) > 0 else 0:.1f}%)")

if total_ingested == len(documents):
    print(f"\nAll videos successfully ingested!")
else:
    print(f"\nSome videos failed to ingest.")
    print(f"Check logs:")
    print(f"   docker logs visual-search --tail 100")
    print(f"   docker logs cosmos-embed --tail 100")
    print(f"   docker logs transcode-proxy --tail 100")
