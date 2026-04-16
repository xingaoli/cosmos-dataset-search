#!/usr/bin/env python3
"""Search for similar videos by text or video clip.

Usage:
  python tools/7_search_videos.py --text "a car driving on the highway"
  python tools/7_search_videos.py --video 002dec8e-3d95-4cc2-abbe-99b3a2e78618.camera_front_wide_120fov.mp4
  python tools/7_search_videos.py --text "rainy day" --top-k 10
"""

import argparse
import requests
from _config import COLLECTION_ID, API_BASE


def search_text(text, top_k):
    payload = {
        "query": [{"text": text}],
        "top_k": top_k,
    }
    print(f"Query text: \"{text}\"")
    return _do_search(payload, top_k)


def search_video(filename, top_k):
    from _config import S3_PREFIX, TRANSCODE_PROXY_DOCKER
    url = f"{TRANSCODE_PROXY_DOCKER}/transcode?key={S3_PREFIX}/{filename}"
    print(f"Query video: {filename}")

    payload = {
        "query": [{"video": url}],
        "top_k": top_k,
    }
    return _do_search(payload, top_k)


def _do_search(payload, top_k):
    print(f"Collection: {COLLECTION_ID}")
    print(f"Top K: {top_k}\n")

    response = requests.post(
        f"{API_BASE}/collections/{COLLECTION_ID}/search",
        json=payload,
        timeout=120,
    )

    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")
        return

    results = response.json()
    retrievals = results.get('retrievals', [])
    print(f"Found {len(retrievals)} results:\n")

    if not retrievals:
        print("No results found.")
        return

    for i, r in enumerate(retrievals, 1):
        filename = r.get('metadata', {}).get('filename', '')
        clip_id = filename.split('.')[0] if filename else r.get('id', '')[:16]
        print(f"Result {i}: {filename}")
        print(f"  Score: {r.get('score', 'N/A')}")
        print(f"  Clip ID: {clip_id}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Search videos by text or video clip")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", "-t", help="Search by text description")
    group.add_argument("--video", "-v", help="Search by video filename (must exist in S3)")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of results (default: 5)")
    args = parser.parse_args()

    if not COLLECTION_ID:
        print("ERROR: Set TOOLS_COLLECTION_ID in deploy/standalone/.env")
        exit(1)

    if args.text:
        search_text(args.text, args.top_k)
    elif args.video:
        search_video(args.video, args.top_k)


if __name__ == "__main__":
    main()
