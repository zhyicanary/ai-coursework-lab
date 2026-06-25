"""基础 RAG 管道 — 文档加载 → 分块 → 向量化 → ChromaDB 索引 / 检索。

与 common/ 层的关系：
  - common/document_loader.py  → 解析和分块
  - common/vector_store.py     → ChromaDB CRUD（add_documents / search_documents）
  - common/embedding_client.py → embedding 向量化（由 vector_store 内部调用）
"""

import hashlib
import time
from pathlib import Path
from typing import IO

from common.document_loader import Document, load, chunk_documents
from common.vector_store import add_documents, search_documents, init_collection, client


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
    """在知识库中语义搜索文档片段。

    Args:
        query: 用户查询。
        top_k: 返回结果数。

    Returns:
        [{content, doc_id, chunk_index, score}, ...]
    """
    return search_documents(query=query, top_k=top_k)


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
