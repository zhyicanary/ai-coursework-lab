"""Cross-Encoder 重排序客户端 — 基于 sentence-transformers。

两阶段检索的第二阶段：
  1. 向量检索（粗召回）：ChromaDB cosine 相似度，快速取 top-N
  2. Cross-Encoder（精排序）：逐对计算 query-document 相关性，重排取 top-K

Cross-Encoder 比向量检索精度高，因为它是把 [query, document] 拼在一起
送入模型做完整 attention，而不是分别编码后算余弦。

支持运行时热切换模型和开关，通过 update() 方法持久化到 .env。
"""

import os
from pathlib import Path

from dotenv import load_dotenv, set_key
from sentence_transformers import CrossEncoder

ENV_FILE = Path(__file__).parent.parent / ".env"
load_dotenv()


class RerankerClient:
    """Cross-Encoder 重排序客户端，懒加载模型。

    首次调用 rerank() 时才加载模型，避免启动时卡顿。
    模型首次加载会从 HuggingFace 下载（约 560MB），后续从本地缓存读取。

    支持通过 enabled 开关关闭重排序（降级为纯向量检索）。
    """

    def __init__(self):
        self.model_name: str = os.getenv(
            "RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"
        )
        self.enabled: bool = os.getenv("RERANKER_ENABLED", "true").lower() == "true"
        self._model: CrossEncoder | None = None

    @property
    def model(self) -> CrossEncoder:
        """懒加载 Cross-Encoder 模型。"""
        if self._model is None:
            self._model = CrossEncoder(self.model_name)
        return self._model

    def update(self, model: str | None = None, enabled: bool | None = None):
        """运行时切换模型或开关，持久化到 .env。

        Args:
            model: 新的 Reranker 模型名。
            enabled: 是否启用重排序。
        """
        load_dotenv(override=True)
        if model:
            self.model_name = model
            self._model = None  # 清缓存，下次重新加载
            set_key(str(ENV_FILE), "RERANKER_MODEL", model)
        if enabled is not None:
            self.enabled = enabled
            set_key(str(ENV_FILE), "RERANKER_ENABLED", "true" if enabled else "false")

    def get_config(self) -> dict:
        """返回当前配置，供 UI 回显。"""
        return {
            "model": self.model_name,
            "enabled": self.enabled,
        }

    def rerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int = 5,
        content_key: str = "content",
    ) -> list[dict]:
        """对检索结果重排序。

        Args:
            query: 用户查询文本。
            documents: 粗召回的文档列表，每项含 content 等字段。
            top_k: 重排后返回的数量。
            content_key: 文档内容字段名。

        Returns:
            重排后的文档列表（按相关性降序），每项新增 rerank_score 字段。
        """
        if not self.enabled:
            return documents

        if not documents:
            return []

        # 如果文档数已经 <= top_k，不需要重排
        if len(documents) <= top_k:
            return documents

        # 构造 [query, doc] 对
        pairs = [[query, doc.get(content_key, "")] for doc in documents]

        # Cross-Encoder 打分
        scores = self.model.predict(pairs)

        # 按 rerank_score 降序排列
        scored = []
        for doc, score in zip(documents, scores):
            doc_copy = dict(doc)
            doc_copy["rerank_score"] = round(float(score), 4)
            scored.append(doc_copy)

        scored.sort(key=lambda x: x["rerank_score"], reverse=True)

        return scored[:top_k]


# 实例通过 common.context.get_context().reranker 获取，不再提供模块级单例
