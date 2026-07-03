from pathlib import Path

import chromadb

from common.embedding_client import embedding

# 持久化目录
DATA_DIR = Path(__file__).parent.parent / "data" / "chromadb"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 全局单例
client = chromadb.PersistentClient(path=str(DATA_DIR))


def init_collection(collection_name: str = "default"):
    """初始化/获取 collection

    Args:
        collection_name: collection 名称，不同项目使用不同名称避免冲突
    """
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def add_attractions(
    city: str,
    attractions: list[dict],
    texts: list[str],
    collection_name: str = "attractions",
):
    """批量添加景点

    Args:
        city: 城市名
        attractions: 景点列表，每项包含 name, category, ticket_price, duration, description
        texts: 用于向量化的文本列表（与 attractions 一一对应）
        collection_name: collection 名称，默认 "attractions"
    """
    collection = init_collection(collection_name)

    ids = [f"{city}_{a['name']}" for a in attractions]
    metadatas = [
        {
            "city": city,
            "name": a["name"],
            "category": a.get("category", ""),
            "ticket_price": a.get("ticket_price", 0),
            "duration": a.get("duration", ""),
        }
        for a in attractions
    ]

    # 使用 embedding 客户端生成向量
    embeddings = embedding.embed_texts(texts)

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )


def search_attractions(
    city: str,
    query: str,
    top_k: int = 10,
    preferences: list[str] = [],
    collection_name: str = "attractions",
) -> list[dict]:
    """向量检索景点

    Args:
        city: 城市名
        query: 查询文本
        top_k: 返回数量
        preferences: 偏好关键词列表
        collection_name: collection 名称，默认 "attractions"

    Returns:
        [{name, category, ticket_price, duration, description, score}]
    """
    collection = init_collection(collection_name)

    # 构建过滤条件
    where = {"city": city}

    # 生成查询向量
    query_embedding = embedding.embed_query(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    attractions = []
    if results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i]
            distance = results["distances"][0][i]
            # cosine distance 转 similarity score
            score = 1 - distance

            attractions.append(
                {
                    "name": meta["name"],
                    "category": meta["category"],
                    "ticket_price": meta["ticket_price"],
                    "duration": meta["duration"],
                    "description": results["documents"][0][i],
                    "score": round(score, 4),
                }
            )

    # 如果有偏好关键词，按匹配度排序
    if preferences:
        attractions.sort(
            key=lambda x: sum(
                1 for p in preferences if p in x["description"] or p in x["category"]
            ),
            reverse=True,
        )

    return attractions


def add_documents(
    doc_id: str,
    documents: list[dict],
    texts: list[str],
    collection_name: str = "documents",
):
    """添加文档到知识库（KnowSeeker 专用）

    Args:
        doc_id: 文档 ID
        documents: 文档列表，每项包含 content, metadata 等
        texts: 用于向量化的文本列表
        collection_name: collection 名称，默认 "documents"
    """
    collection = init_collection(collection_name)

    ids = [f"{doc_id}_{i}" for i in range(len(texts))]
    metadatas = [
        {"doc_id": doc_id, "chunk_index": i, **doc.get("metadata", {})}
        for i, doc in enumerate(documents)
    ]

    embeddings = embedding.embed_texts(texts)

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )


def search_documents(
    query: str,
    top_k: int = 5,
    collection_name: str = "documents",
) -> list[dict]:
    """搜索文档知识库（KnowSeeker 专用）

    Args:
        query: 查询文本
        top_k: 返回数量
        collection_name: collection 名称，默认 "documents"

    Returns:
        [{content, doc_id, chunk_index, score}]
    """
    collection = init_collection(collection_name)

    query_embedding = embedding.embed_query(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = []
    if results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i]
            distance = results["distances"][0][i]
            score = 1 - distance

            documents.append(
                {
                    "content": results["documents"][0][i],
                    "doc_id": meta.get("doc_id", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                    "score": round(score, 4),
                }
            )

    return documents


def get_all_documents(collection_name: str = "documents") -> list[dict]:
    """获取集合中所有文档（用于 BM25 索引重建）。

    Args:
        collection_name: collection 名称，默认 "documents"

    Returns:
        [{id, content, doc_id, chunk_index}, ...]
    """
    collection = init_collection(collection_name)
    results = collection.get(include=["documents", "metadatas"])
    docs = []
    if results["ids"]:
        for i in range(len(results["ids"])):
            meta = results["metadatas"][i]
            docs.append(
                {
                    "id": results["ids"][i],
                    "content": results["documents"][i],
                    "doc_id": meta.get("doc_id", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                }
            )
    return docs
