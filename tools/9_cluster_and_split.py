#!/usr/bin/env python3
"""
Video clustering and train/test split.

1. Fetch embeddings from collection
2. Cluster videos using Agglomerative clustering
3. Split train/test per cluster
4. Visualize with t-SNE
"""

import requests
import numpy as np
import json
import os
from typing import List, Dict, Tuple
from sklearn.cluster import AgglomerativeClustering
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
from _config import COLLECTION_ID, API_BASE, DATA_DIR

if not COLLECTION_ID:
    print("ERROR: Set TOOLS_COLLECTION_ID in deploy/standalone/.env")
    exit(1)

TRAIN_RATIO = 0.9
RANDOM_SEED = 42
DISTANCE_THRESHOLD = 75.0
MIN_CLUSTER_SIZE = 20
OUTPUT_DIR = os.path.join(DATA_DIR, 'phaiav_videos')


def get_all_documents_with_embeddings() -> List[Dict]:
    print("Step 1: Fetching embeddings...")

    search_payload = {
        "query": [{"text": "video"}],
        "top_k": 1500,
        "reconstruct": True
    }

    response = requests.post(
        f"{API_BASE}/collections/{COLLECTION_ID}/search",
        json=search_payload
    )

    if response.status_code != 200:
        print(f"Error: {response.text}")
        return []

    results = response.json()
    retrievals = results.get('retrievals', [])
    print(f"Fetched {len(retrievals)} videos")

    documents = []
    for item in retrievals:
        if item.get('embedding'):
            filename = item.get('metadata', {}).get('filename', '')
            video_uuid = filename.split('.')[0] if filename else ''
            documents.append({
                'uuid': video_uuid,
                'filename': filename,
                'embedding': item['embedding']
            })

    print(f"Extracted embeddings for {len(documents)} videos")
    return documents


def cluster_videos(embeddings: List[List[float]]) -> np.ndarray:
    print(f"\nStep 2: Agglomerative clustering (threshold={DISTANCE_THRESHOLD})...")

    X = np.array(embeddings)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    clusterer = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=DISTANCE_THRESHOLD,
        linkage='ward'
    )
    labels = clusterer.fit_predict(X_scaled)

    n_clusters = len(set(labels))
    print(f"Found {n_clusters} clusters:")
    for i in range(n_clusters):
        count = np.sum(labels == i)
        print(f"  Cluster {i}: {count} videos")

    small = [i for i in range(n_clusters) if np.sum(labels == i) < MIN_CLUSTER_SIZE]
    if small:
        print(f"\n  Warning: {len(small)} small clusters (<{MIN_CLUSTER_SIZE})")

    return labels


def split_train_test_by_cluster(documents, labels, train_ratio=TRAIN_RATIO):
    print(f"\nStep 3: Splitting train/test ({train_ratio:.0%})...")

    train_docs, test_docs = [], []
    cluster_groups = {}
    for doc, label in zip(documents, labels):
        cluster_groups.setdefault(label, []).append(doc)

    for cluster_id, docs_in_cluster in cluster_groups.items():
        if cluster_id == -1:
            for doc in docs_in_cluster:
                train_docs.append({'uuid': doc['uuid'], 'filename': doc['filename'], 'cluster': -1, 'split': 'train'})
            continue

        n_train = max(1, int(len(docs_in_cluster) * train_ratio))
        np.random.seed(RANDOM_SEED)
        indices = np.random.permutation(len(docs_in_cluster))

        for i, idx in enumerate(indices):
            doc = docs_in_cluster[idx]
            info = {'uuid': doc['uuid'], 'filename': doc['filename'], 'cluster': int(cluster_id)}
            if i < n_train:
                info['split'] = 'train'
                train_docs.append(info)
            else:
                info['split'] = 'test'
                test_docs.append(info)

        print(f"  Cluster {cluster_id}: {n_train} train / {len(docs_in_cluster) - n_train} test")

    print(f"\nTotal: {len(train_docs)} train, {len(test_docs)} test")
    return train_docs, test_docs


def visualize_clusters(embeddings, labels, documents):
    print(f"\nStep 4: t-SNE visualization...")

    X = np.array(embeddings)
    print("  Computing t-SNE...")
    tsne = TSNE(n_components=2, random_state=RANDOM_SEED, perplexity=min(30, len(X) - 1))
    X_2d = tsne.fit_transform(X)

    plt.figure(figsize=(12, 8))
    unique_labels = set(labels)
    colors = plt.cm.rainbow(np.linspace(0, 1, len(unique_labels)))

    for label, color in zip(unique_labels, colors):
        mask = labels == label
        label_name = f'Cluster {label}' if label >= 0 else 'Noise'
        plt.scatter(X_2d[mask, 0], X_2d[mask, 1], c=[color], label=label_name, alpha=0.7, s=100)

    for i, doc in enumerate(documents):
        if i % 5 == 0:
            uuid_short = doc['uuid'][:8] + '...'
            plt.annotate(uuid_short, (X_2d[i, 0], X_2d[i, 1]), fontsize=6, alpha=0.5)

    plt.title('Video Clusters (t-SNE)', fontsize=14)
    plt.xlabel('t-SNE 1')
    plt.ylabel('t-SNE 2')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, 'clusters_visualization.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  Saved: {output_path}")


def save_results(train_docs, test_docs):
    print(f"\nStep 5: Saving results...")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    train_uuids = [d['uuid'] for d in train_docs]
    with open(os.path.join(OUTPUT_DIR, 'train_uuids.json'), 'w') as f:
        json.dump(train_uuids, f, indent=2)
    print(f"  Train UUIDs saved")

    test_uuids = [d['uuid'] for d in test_docs]
    with open(os.path.join(OUTPUT_DIR, 'test_uuids.json'), 'w') as f:
        json.dump(test_uuids, f, indent=2)
    print(f"  Test UUIDs saved")

    all_docs = train_docs + test_docs
    with open(os.path.join(OUTPUT_DIR, 'split_details.json'), 'w') as f:
        json.dump(all_docs, f, indent=2)

    stats = {
        'total_videos': len(all_docs),
        'train_count': len(train_docs),
        'test_count': len(test_docs),
        'agglo_params': {'distance_threshold': DISTANCE_THRESHOLD},
        'clusters': {}
    }
    for doc in all_docs:
        key = str(doc['cluster'])
        if key not in stats['clusters']:
            stats['clusters'][key] = {'train': 0, 'test': 0, 'uuids': []}
        stats['clusters'][key][doc['split']] += 1
        stats['clusters'][key]['uuids'].append(doc['uuid'])

    with open(os.path.join(OUTPUT_DIR, 'split_stats.json'), 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"  Stats saved")


def main():
    print("=" * 60)
    print("Video Clustering and Train/Test Split")
    print("=" * 60)

    documents = get_all_documents_with_embeddings()
    if not documents:
        print("Error: no video data fetched")
        return

    embeddings = [doc['embedding'] for doc in documents]
    labels = cluster_videos(embeddings)
    train_docs, test_docs = split_train_test_by_cluster(documents, labels)
    visualize_clusters(embeddings, labels, documents)
    save_results(train_docs, test_docs)

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
