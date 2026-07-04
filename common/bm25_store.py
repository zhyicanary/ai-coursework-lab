"""BM25 稀疏检索 — 与稠密向量检索互补，提升专有名词/缩写的召回率。

工作方式：
  1. 启动时从 ChromaDB 加载所有文档构建 BM25 索引
  2. 新文档索引时同步更新 BM25
  3. 搜索时与稠密向量结果通过 RRF 合并

BM25 擅长精确关键词匹配（专有名词、缩写、代码），
稠密向量擅长语义匹配（同义改写、泛化表达），两者互补。
"""

import math
from collections import Counter
from typing import Optional


# ── 中文分词 ────────────────────────────────────────────

def tokenize(text: str) -> list[str]:
    """BM25 分词。

    中文按单字切分（避免依赖 jieba 等外部分词器），
    英文/数字保留完整词，大小写归一化。

    >>> tokenize("BERT模型训练")
    ["BERT", "模", "型", "训", "练"]

    >>> tokenize("召回率 Recall")
    ["召", "回", "率", "recall"]
    """
    tokens: list[str] = []
    buf: list[str] = []

    for ch in text:
        # CJK 统一表意文字区间
        if "\u4e00" <= ch <= "\u9fff" or "\u3000" <= ch <= "\u303f":
            if buf:
                tokens.append("".join(buf).lower())
                buf.clear()
            tokens.append(ch)  # 单字成 token
        elif ch.isalnum() or ch in "-_":
            buf.append(ch)
        else:
            if buf:
                tokens.append("".join(buf).lower())
                buf.clear()
    if buf:
        tokens.append("".join(buf).lower())

    return tokens


# ── BM25 Okapi ──────────────────────────────────────────

class BM25Okapi:
    """BM25 Okapi 实现。

    参数（通常不需要调）：
      k1: 词频饱和度（1.2~2.0），越大词频影响越大
      b:  长度归一化（0~1），0=不归一化，1=完全归一化
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size: int = 0
        self.avgdl: float = 0.0
        self.doc_freqs: list[Counter] = []
        self.idf: dict[str, float] = {}
        self.doc_ids: list[str] = []
        self.doc_texts: list[str] = []

    def fit(self, texts: list[str], doc_ids: Optional[list[str]] = None):
        """构建 BM25 索引。"""
        self.corpus_size = len(texts)
        self.doc_texts = texts
        self.doc_ids = doc_ids or [str(i) for i in range(len(texts))]
        self.doc_freqs = [Counter(tokenize(t)) for t in texts]

        # 文档频率：每个词出现在多少篇文档中
        df: dict[str, int] = {}
        for freqs in self.doc_freqs:
            for term in freqs:
                df[term] = df.get(term, 0) + 1

        # IDF：稀有词权重高
        self.idf = {}
        for term, freq in df.items():
            self.idf[term] = math.log(
                1 + (self.corpus_size - freq + 0.5) / (freq + 0.5)
            )

        # 平均文档长度
        total_len = sum(sum(c.values()) for c in self.doc_freqs)
        self.avgdl = total_len / self.corpus_size if self.corpus_size else 0.0

    def get_scores(self, query: str) -> list[float]:
        """为 corpus 中每篇文档计算 BM25 分数。"""
        query_tokens = tokenize(query)
        if not query_tokens or not self.corpus_size:
            return [0.0] * self.corpus_size

        scores = [0.0] * self.corpus_size
        for i, freqs in enumerate(self.doc_freqs):
            doc_len = sum(freqs.values())
            score = 0.0
            for term in query_tokens:
                if term in self.idf and term in freqs:
                    tf = freqs[term]
                    idf = self.idf[term]
                    # BM25 Okapi 公式
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (
                        1 - self.b + self.b * doc_len / self.avgdl
                    )
                    score += idf * numerator / denominator
            scores[i] = score

        return scores

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """搜索 BM25 索引。返回 [{index, doc_id, content, score}]。"""
        scores = self.get_scores(query)

        # 按分数降序排列
        indexed = list(enumerate(scores))
        indexed.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in indexed:
            if score <= 0:
                continue
            results.append(
                {
                    "index": idx,
                    "doc_id": self.doc_ids[idx],
                    "content": self.doc_texts[idx],
                    "score": round(float(score), 4),
                }
            )
            if len(results) >= top_k:
                break

        return results


# ── BM25 存储（全局单例，与 ChromaDB 同步） ────────────

class BM25Store:
    """BM25 索引管理器，保持与 ChromaDB 的数据一致。"""

    def __init__(self):
        self.bm25 = BM25Okapi()
        # key = f"{doc_id_fname}_{chunk_index}" → 元信息
        self.chunk_map: dict[str, dict] = {}
        self._ready = False

    # ── 内部方法 ────────────────────────────────────

    def _rebuild(self):
        """从 ChromaDB 重建完整 BM25 索引。"""
        from common.vector_store import get_all_documents

        all_docs = get_all_documents(collection_name="documents")
        self.chunk_map.clear()

        if not all_docs:
            self._ready = True
            return

        texts: list[str] = []
        for doc in all_docs:
            key = f"{doc['doc_id']}_{doc['chunk_index']}"
            self.chunk_map[key] = {
                "content": doc["content"],
                "doc_id_fname": doc["doc_id"],
                "chunk_index": doc["chunk_index"],
            }
            texts.append(doc["content"])

        self.bm25.fit(texts, list(self.chunk_map.keys()))
        self._ready = True

    def ensure_loaded(self):
        if not self._ready:
            self._rebuild()

    # ── 公开方法 ────────────────────────────────────

    def add_texts(self, texts: list[str], metadatas: list[dict]):
        """添加新文档到 BM25 索引。"""
        if not texts:
            return

        self.ensure_loaded()

        # 追加新文档
        for i, text in enumerate(texts):
            meta = metadatas[i] if i < len(metadatas) else {}
            key = f"{meta.get('doc_id', 'unknown')}_{meta.get('chunk_index', i)}"
            self.chunk_map[key] = {
                "content": text,
                "doc_id_fname": meta.get("doc_id", "unknown"),
                "chunk_index": meta.get("chunk_index", i),
            }

        # 重新 fit
        all_texts = [v["content"] for v in self.chunk_map.values()]
        self.bm25.fit(all_texts, list(self.chunk_map.keys()))

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """搜索 BM25 索引，返回与 vector_store.search_documents() 相同格式。

        返回: [{content, doc_id, chunk_index, score}, ...]
        """
        self.ensure_loaded()
        raw_results = self.bm25.search(query, top_k)

        formatted = []
        for r in raw_results:
            info = self.chunk_map.get(r["doc_id"], {})
            formatted.append(
                {
                    "content": info.get("content", r["content"]),
                    "doc_id": info.get("doc_id_fname", ""),
                    "chunk_index": info.get("chunk_index", 0),
                    "score": r["score"],
                }
            )

        return formatted

    def mark_dirty(self):
        """标记索引为脏，下次 search 时自动从 ChromaDB 重建。"""
        self._ready = False


# 实例通过 common.context.get_context().bm25_store 获取，不再提供模块级单例
