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

from common.document_loader import Document, load, chunk_documents
from common.vector_store import add_documents, search_documents, init_collection, client
from common.reranker import reranker


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
    fname = filename or (Path(file).name if isinstance(file, (str, Path)) else "unknown")
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

    return {
        "doc_id": doc_id,
        "file_name": fname,
        "chunks_count": len(chunks),
        "success": True,
    }


def search(query: str, top_k: int = 5) -> list[dict]:
    """在知识库中语义搜索文档片段（单阶段向量检索）。

    Args:
        query: 用户查询。
        top_k: 返回结果数。

    Returns:
        [{content, doc_id, chunk_index, score}, ...]
    """
    return search_documents(query=query, top_k=top_k)


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
    # 第一阶段：向量粗召回
    candidates = search_documents(query=query, top_k=recall_k)

    if not candidates:
        return [], {"recall_count": 0, "rerank_count": 0, "reranked": False}

    # 记录粗召回分数（用于对比）
    recall_scores = [
        {"doc_id": c.get("doc_id", ""), "recall_score": c.get("score", 0)}
        for c in candidates
    ]

    # 第二阶段：Cross-Encoder 精排序
    try:
        reranked = reranker.rerank(query=query, documents=candidates, top_k=top_k)
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
    return len(ids_to_delete) > 0
