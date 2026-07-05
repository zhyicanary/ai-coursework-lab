"""基础 RAG 管道 — 文档加载 → 分块 → 向量化 → ChromaDB 索引 / 检索。

与 common/ 层的关系：
  - common/document_loader.py  → 解析和分块
  - common/vector_store.py     → ChromaDB CRUD（add_documents / search_documents）
  - common/embedding_client.py → embedding 向量化（由 vector_store 内部调用）
  - common/reranker.py         → Cross-Encoder 重排序（两阶段检索第二阶段）
"""

import hashlib
import time
from pathlib import Path
from typing import IO

from common.context import get_context
from common.document_loader import Document, chunk_documents, load
from common.vector_store import add_documents, init_collection, search_documents


def index_document(
    file: str | Path | IO,
    filename: str | None = None,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> dict:
    """加载、分块、向量化并索引单个文档到 ChromaDB。

    Args:
        file: 文件路径或文件对象。
        filename: 文件名（当 file 是 IO 对象时需要）。
        chunk_size: 分块字符数。
        chunk_overlap: 块间重叠。

    Returns:
        {doc_id, chunks_count, file_name, success}
    """
    # 1. 加载
    raw_docs = load(file, filename)

    # 2. 分块
    chunks = chunk_documents(raw_docs, chunk_size, chunk_overlap)

    # 3. 生成 doc_id（基于文件名 + 时间戳）
    fname = filename or (
        Path(file).name if isinstance(file, (str, Path)) else "unknown"
    )
    doc_id = f"{fname}_{int(time.time())}"

    # 4. 准备 documents 和 texts
    docs_for_store = [
        {
            "content": c.content,
            "metadata": c.metadata,
        }
        for c in chunks
    ]
    texts = [c.content for c in chunks]

    # 5. 索引到 ChromaDB
    add_documents(doc_id=doc_id, documents=docs_for_store, texts=texts)

    # 6. 同步到 BM25 索引
    get_context().bm25_store.add_texts(texts, [d["metadata"] for d in docs_for_store])

    return {
        "doc_id": doc_id,
        "file_name": fname,
        "chunks_count": len(chunks),
        "success": True,
    }


def _hybrid_merge(
    dense_results: list[dict],
    sparse_results: list[dict],
    top_k: int,
    rrf_k: int = 60,
) -> list[dict]:
    """用 Reciprocal Rank Fusion（RRF）合并稠密和稀疏检索结果。

    RRF 公式：score(d) = Σ 1/(k + rank(d))
    出现在两种结果中的文档获得双方排名贡献，排名越靠前得分越高。

    Args:
        dense_results: 稠密向量检索结果。
        sparse_results: BM25 稀疏检索结果。
        top_k: 合并后返回数量。
        rrf_k: RRF 常数（通常 60），越大排名差异影响越小。

    Returns:
        合并后的文档列表。
    """

    def _key(d):
        return f"{d.get('doc_id', '')}_{d.get('chunk_index', 0)}"

    rrf_scores: dict[str, float] = {}
    doc_map: dict[str, dict] = {}

    for rank, doc in enumerate(dense_results):
        k = _key(doc)
        rrf_scores[k] = rrf_scores.get(k, 0) + 1.0 / (rrf_k + rank + 1)
        if k not in doc_map:
            doc_map[k] = doc

    for rank, doc in enumerate(sparse_results):
        k = _key(doc)
        rrf_scores[k] = rrf_scores.get(k, 0) + 1.0 / (rrf_k + rank + 1)
        if k not in doc_map:
            doc_map[k] = doc

    sorted_keys = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)
    return [doc_map[k] for k in sorted_keys[:top_k]]


def search_with_rerank(
    query: str,
    top_k: int = 5,
    recall_k: int = 20,
) -> tuple[list[dict], dict]:
    """两阶段检索：向量粗召回 → Cross-Encoder 精排序。

    第一阶段：ChromaDB 向量检索 recall_k 条（快，但精度一般）
    第二阶段：Cross-Encoder 逐对打分重排，取 top_k（慢，但精度高）

    Args:
        query: 用户查询。
        top_k: 最终返回结果数。
        recall_k: 第一阶段粗召回数量（应 > top_k）。

    Returns:
        (reranked_results, rerank_info)
        - reranked_results: 重排后的文档列表
        - rerank_info: 重排序元信息（供 trace 可视化）
    """
    # 第一阶段：稠密向量粗召回 + BM25 稀疏检索
    dense_candidates = search_documents(query=query, top_k=recall_k)
    sparse_candidates = get_context().bm25_store.search(query=query, top_k=recall_k)

    if not dense_candidates and not sparse_candidates:
        return [], {"recall_count": 0, "rerank_count": 0, "reranked": False}

    # 合并两路结果
    candidates = _hybrid_merge(dense_candidates, sparse_candidates, top_k=recall_k)

    # 记录召回信息
    recall_scores = [
        {"doc_id": c.get("doc_id", ""), "recall_score": c.get("score", 0)}
        for c in candidates
    ]

    # 第二阶段：Cross-Encoder 精排序
    try:
        reranked = get_context().reranker.rerank(query=query, documents=candidates, top_k=top_k)
        reranked_flag = True
    except Exception:
        # Reranker 失败时降级：直接用向量检索结果
        reranked = candidates[:top_k]
        reranked_flag = False

    # 记录重排序信息
    rerank_scores = [
        {
            "doc_id": r.get("doc_id", ""),
            "recall_score": r.get("score", 0),
            "rerank_score": r.get("rerank_score", 0),
        }
        for r in reranked
    ]

    info = {
        "recall_count": len(candidates),
        "rerank_count": len(reranked),
        "reranked": reranked_flag,
        "score_changes": rerank_scores,
    }

    return reranked, info


def list_documents() -> list[dict]:
    """列出知识库中所有文档（含分块统计）。"""
    col = init_collection("documents")
    all_data = col.get(include=["metadatas"])

    doc_map: dict[str, dict] = {}
    if all_data["ids"]:
        for i, doc_id in enumerate(all_data["ids"]):
            meta = all_data["metadatas"][i]
            did = meta.get("doc_id", "unknown")
            if did not in doc_map:
                doc_map[did] = {"doc_id": did, "chunks_count": 0}
            doc_map[did]["chunks_count"] += 1

    return list(doc_map.values())


def delete_document(doc_id: str) -> bool:
    """从知识库删除指定文档的所有分块。"""
    col = init_collection("documents")
    all_data = col.get(include=["metadatas"])

    ids_to_delete = []
    if all_data["ids"]:
        for i, id_ in enumerate(all_data["ids"]):
            meta = all_data["metadatas"][i]
            if meta.get("doc_id") == doc_id:
                ids_to_delete.append(id_)

    if ids_to_delete:
        col.delete(ids=ids_to_delete)
        get_context().bm25_store.mark_dirty()
    return len(ids_to_delete) > 0
