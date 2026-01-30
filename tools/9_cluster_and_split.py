#!/usr/bin/env python3
"""
视频聚类和训练/测试集划分脚本

流程：
1. 从 Milvus 获取所有视频的特征向量
2. 使用聚类算法（K-Means/DBSCAN）对视频进行聚类
3. 从每个簇中按比例划分训练集和测试集
4. 可选：使用 t-SNE/UMAP 可视化聚类结果
"""

import requests
import numpy as np
import json
from typing import List, Dict, Tuple
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import os

COLLECTION_ID = "a6499a603_28e6_4dc5_b3cd_667fdd620805"
API_BASE = "http://localhost:8888/v1"

# 配置参数
TRAIN_RATIO = 0.9  # 训练集比例（90%训练，10%测试）
RANDOM_SEED = 42

# Agglomerative 聚类参数（自动确定聚类数量）
DISTANCE_THRESHOLD = 75.0  # 距离阈值，越大聚类越少，可以调整此值
MIN_CLUSTER_SIZE = 20  # 最小簇大小，小于此值的簇会被合并


def get_all_documents_with_embeddings() -> List[Dict]:
    """
    从 collection 中获取所有文档及其特征向量
    使用一个通用查询来获取所有文档
    """
    print("Step 1: 获取所有视频的特征向量...")

    # 使用一个通用的文本查询来获取所有文档
    # 设置 reconstruct=true 来获取特征向量
    search_payload = {
        "query": [{"text": "video"}],  # 通用查询
        "top_k": 1500,  # 获取所有视频（999个）
        "reconstruct": True  # 关键：启用特征向量返回
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

    print(f"获取到 {len(retrievals)} 个视频")

    # 提取视频信息（只保留 UUID 作为场景标识）
    documents = []
    for item in retrievals:
        if item.get('embedding'):  # 只包含有特征的文档
            filename = item.get('metadata', {}).get('filename', '')
            # 从文件名提取 UUID（去掉后缀部分）
            # 例如：c3ca785e-3876-4a0a-a8bd-890f2027d795.camera_front_wide_120fov.mp4
            # 提取：c3ca785e-3876-4a0a-a8bd-890f2027d795
            video_uuid = filename.split('.')[0] if filename else ''

            documents.append({
                'uuid': video_uuid,  # 场景唯一标识
                'filename': filename,  # 完整文件名（用于参考）
                'embedding': item['embedding']
            })

    print(f"成功提取 {len(documents)} 个视频的特征向量")
    return documents


def cluster_videos(embeddings: List[List[float]], method='agglomerative') -> np.ndarray:
    """
    对视频特征进行聚类（自动确定聚类数量）

    Args:
        embeddings: 特征向量列表
        method: 聚类方法 ('agglomerative' 层次聚类自动确定簇数)

    Returns:
        聚类标签数组
    """
    print(f"\nStep 2: 使用 {method.upper()} 进行聚类（自动确定聚类数量）...")

    X = np.array(embeddings)

    # 标准化特征
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    if method == 'agglomerative':
        # Agglomerative 层次聚类 - 根据距离阈值自动确定聚类数量
        print(f"  参数: distance_threshold={DISTANCE_THRESHOLD}")

        # 使用 linkage='ward' 最小化方差
        clusterer = AgglomerativeClustering(
            n_clusters=None,  # 让算法自动确定
            distance_threshold=DISTANCE_THRESHOLD,
            linkage='ward'
        )
        labels = clusterer.fit_predict(X_scaled)

        n_clusters = len(set(labels))
        print(f"Agglomerative 聚类完成:")
        print(f"  发现 {n_clusters} 个簇")

        # 打印每个簇的大小并过滤小簇
        cluster_sizes = {}
        for i in range(n_clusters):
            count = np.sum(labels == i)
            cluster_sizes[i] = count
            print(f"  簇 {i}: {count} 个视频")

        # 检查是否有小簇需要处理
        small_clusters = [i for i, size in cluster_sizes.items() if size < MIN_CLUSTER_SIZE]
        if small_clusters:
            print(f"\n  ⚠️  发现 {len(small_clusters)} 个小簇（<{MIN_CLUSTER_SIZE}个视频）")
            print(f"  小簇编号: {small_clusters}")
            print(f"  建议: 调整 DISTANCE_THRESHOLD 参数（当前值: {DISTANCE_THRESHOLD}）")
            print(f"       - 增大阈值 → 更少、更大的簇")
            print(f"       - 减小阈值 → 更多、更小的簇")

    return labels


def split_train_test_by_cluster(
    documents: List[Dict],
    labels: np.ndarray,
    train_ratio: float = TRAIN_RATIO
) -> Tuple[List[Dict], List[Dict]]:
    """
    按簇划分训练集和测试集
    每个簇中的视频按比例分配到训练集和测试集

    Returns:
        (train_docs, test_docs) - 只包含 UUID 和聚类信息
    """
    print(f"\nStep 3: 按簇划分训练集和测试集 (比例: {train_ratio:.0%})...")

    train_docs = []
    test_docs = []

    # 按簇分组
    cluster_groups = {}
    for doc, label in zip(documents, labels):
        if label not in cluster_groups:
            cluster_groups[label] = []
        cluster_groups[label].append(doc)

    # 对每个簇进行划分
    for cluster_id, docs_in_cluster in cluster_groups.items():
        # 跳过噪声点（cluster_id = -1）
        if cluster_id == -1:
            print(f"  噪声点: {len(docs_in_cluster)} 个视频（将分配到训练集）")
            # 噪声点全部放入训练集
            for doc in docs_in_cluster:
                train_docs.append({
                    'uuid': doc['uuid'],
                    'filename': doc['filename'],
                    'cluster': -1,
                    'split': 'train'
                })
            continue

        n_train = int(len(docs_in_cluster) * train_ratio)
        n_train = max(1, n_train)  # 至少保留1个训练样本

        # 随机打乱
        np.random.seed(RANDOM_SEED)
        indices = np.random.permutation(len(docs_in_cluster))

        for i, idx in enumerate(indices):
            doc = docs_in_cluster[idx]
            doc_info = {
                'uuid': doc['uuid'],
                'filename': doc['filename'],
                'cluster': int(cluster_id)
            }
            if i < n_train:
                doc_info['split'] = 'train'
                train_docs.append(doc_info)
            else:
                doc_info['split'] = 'test'
                test_docs.append(doc_info)

        print(f"  簇 {cluster_id}: {n_train} 训练 / {len(docs_in_cluster) - n_train} 测试")

    print(f"\n总计: {len(train_docs)} 训练集, {len(test_docs)} 测试集")
    return train_docs, test_docs


def visualize_clusters(embeddings: List[List[float]], labels: np.ndarray, documents: List[Dict]):
    """
    使用 t-SNE 可视化聚类结果
    """
    print(f"\nStep 4: 生成 t-SNE 可视化...")

    X = np.array(embeddings)

    # 使用 t-SNE 降维到 2D
    print("  计算 t-SNE (这可能需要几分钟)...")
    tsne = TSNE(n_components=2, random_state=RANDOM_SEED, perplexity=min(30, len(X) - 1))
    X_2d = tsne.fit_transform(X)

    # 绘图
    plt.figure(figsize=(12, 8))

    # 为每个簇分配颜色
    unique_labels = set(labels)
    colors = plt.cm.rainbow(np.linspace(0, 1, len(unique_labels)))

    for label, color in zip(unique_labels, colors):
        mask = labels == label
        label_name = f'Cluster {label}' if label >= 0 else 'Noise'
        plt.scatter(X_2d[mask, 0], X_2d[mask, 1],
                   c=[color], label=label_name, alpha=0.7, s=100)

    # 添加视频 UUID 标注（只显示部分）
    for i, doc in enumerate(documents):
        if i % 5 == 0:  # 每5个视频显示一个标签
            uuid_short = doc['uuid'][:8] + '...'
            plt.annotate(uuid_short, (X_2d[i, 0], X_2d[i, 1]),
                        fontsize=6, alpha=0.5)

    plt.title('Video Clusters Visualization (t-SNE)', fontsize=14)
    plt.xlabel('t-SNE Component 1', fontsize=12)
    plt.ylabel('t-SNE Component 2', fontsize=12)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()

    # 保存图像
    output_path = 'cds-data/phaa1000/clusters_visualization.png'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  可视化已保存到: {output_path}")

    # plt.show()  # 取消注释以显示交互式图表


def save_results(train_docs: List[Dict], test_docs: List[Dict]):
    """
    保存划分结果到 JSON 文件（只包含 UUID 和聚类信息）
    """
    print(f"\nStep 5: 保存结果...")

    output_dir = 'cds-data/phaa1000'
    os.makedirs(output_dir, exist_ok=True)

    # 保存训练集（UUID 列表）
    train_uuids = [doc['uuid'] for doc in train_docs]
    train_path = f'{output_dir}/train_uuids.json'
    with open(train_path, 'w') as f:
        json.dump(train_uuids, f, indent=2)
    print(f"  训练集 UUID 已保存到: {train_path}")

    # 保存测试集（UUID 列表）
    test_uuids = [doc['uuid'] for doc in test_docs]
    test_path = f'{output_dir}/test_uuids.json'
    with open(test_path, 'w') as f:
        json.dump(test_uuids, f, indent=2)
    print(f"  测试集 UUID 已保存到: {test_path}")

    # 保存详细信息（包含 cluster 和 split 标签）
    detailed_path = f'{output_dir}/split_details.json'
    all_docs = train_docs + test_docs
    with open(detailed_path, 'w') as f:
        json.dump(all_docs, f, indent=2)
    print(f"  详细划分信息已保存到: {detailed_path}")

    # 保存统计信息
    stats = {
        'total_videos': len(train_docs) + len(test_docs),
        'train_count': len(train_docs),
        'test_count': len(test_docs),
        'train_ratio': len(train_docs) / (len(train_docs) + len(test_docs)),
        'agglo_params': {
            'distance_threshold': DISTANCE_THRESHOLD,
        },
        'clusters': {}
    }

    # 统计每个簇的划分情况
    for doc in all_docs:
        cluster_id = doc['cluster']
        cluster_key = str(cluster_id)
        if cluster_key not in stats['clusters']:
            stats['clusters'][cluster_key] = {'train': 0, 'test': 0, 'uuids': []}
        if doc['split'] == 'train':
            stats['clusters'][cluster_key]['train'] += 1
        else:
            stats['clusters'][cluster_key]['test'] += 1
        stats['clusters'][cluster_key]['uuids'].append(doc['uuid'])

    stats_path = f'{output_dir}/split_stats.json'
    with open(stats_path, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"  统计信息已保存到: {stats_path}")


def main():
    """主流程"""
    print("="*60)
    print("视频聚类和训练/测试集划分")
    print("="*60)

    # Step 1: 获取所有视频及其特征向量
    documents = get_all_documents_with_embeddings()
    if not documents:
        print("错误：无法获取视频数据")
        return

    embeddings = [doc['embedding'] for doc in documents]

    # Step 2: 聚类（使用 Agglomerative 自动确定聚类数量）
    labels = cluster_videos(embeddings, method='agglomerative')

    # Step 3: 按簇划分训练集和测试集
    train_docs, test_docs = split_train_test_by_cluster(documents, labels, TRAIN_RATIO)

    # Step 4: 可视化
    visualize_clusters(embeddings, labels, documents)

    # Step 5: 保存结果
    save_results(train_docs, test_docs)

    print("\n" + "="*60)
    print("完成！")
    print("="*60)


if __name__ == "__main__":
    main()
