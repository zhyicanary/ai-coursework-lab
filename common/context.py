"""应用上下文容器 — 统一管理所有共享服务实例的生命周期。

替代原来的模块级全局单例（`common.llm_client.llm`、`common.embedding_client.embedding` 等），
将所有服务实例集中管理，支持依赖注入和测试替换。

解决的问题：
  1. 全局单例难以单元测试（只能 monkey-patch）→ 注入自定义 context
  2. LLM 热切换时并发请求的竞态条件 → 单 context 单状态
  3. MCP 连接状态永久降级不恢复 → reset_mcp_state() 可重置
  4. ChromaDB 客户端竞态（多进程竞争文件锁）→ 单 context 管理
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import chromadb
    from common.llm_client import LLMClient
    from common.embedding_client import EmbeddingClient
    from common.reranker import RerankerClient
    from common.bm25_store import BM25Store

# ChromaDB 持久化目录
CHROMA_DATA_DIR = Path(__file__).parent.parent / "data" / "chromadb"
CHROMA_DATA_DIR.mkdir(parents=True, exist_ok=True)


class AppContext:
    """应用上下文 — 持有所有共享服务实例。

    使用方式::

        from common.context import get_context

        ctx = get_context()
        result = await ctx.llm.chat_completion(messages=[...])
        ctx.embedding.embed_texts([...])

    测试注入::

        from common.context import set_context
        mock_ctx = AppContext()
        mock_ctx._llm = MockLLMClient()
        set_context(mock_ctx)
    """

    def __init__(self):
        # ── 懒加载的服务实例 ──
        self._llm: LLMClient | None = None
        self._embedding: EmbeddingClient | None = None
        self._reranker: RerankerClient | None = None
        self._bm25_store: BM25Store | None = None
        self._chroma_client: chromadb.PersistentClient | None = None

        # ── MCP 客户端连接状态 ──
        # None = 未探测，True = HTTP 可用，False = 已降级
        self._mcp_available: bool | None = None
        self._mcp_http_fail_count: int = 0
        self._mcp_max_fails: int = 3

    # ── 服务访问器（懒加载） ────────────────────────────

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            from common.llm_client import LLMClient

            self._llm = LLMClient()
        return self._llm

    @property
    def embedding(self) -> EmbeddingClient:
        if self._embedding is None:
            from common.embedding_client import EmbeddingClient

            self._embedding = EmbeddingClient()
        return self._embedding

    @property
    def reranker(self) -> RerankerClient:
        if self._reranker is None:
            from common.reranker import RerankerClient

            self._reranker = RerankerClient()
        return self._reranker

    @property
    def bm25_store(self) -> BM25Store:
        if self._bm25_store is None:
            from common.bm25_store import BM25Store

            self._bm25_store = BM25Store()
        return self._bm25_store

    @property
    def chroma_client(self) -> chromadb.PersistentClient:
        if self._chroma_client is None:
            import chromadb

            self._chroma_client = chromadb.PersistentClient(
                path=str(CHROMA_DATA_DIR)
            )
        return self._chroma_client

    # ── MCP 连接状态管理 ──────────────────────────────

    @property
    def mcp_available(self) -> bool | None:
        """MCP HTTP Server 可用状态缓存。
        None=未探测, True=可用, False=已降级到直接调用。
        """
        return self._mcp_available

    def mark_mcp_failure(self) -> bool:
        """记录一次 MCP HTTP 调用失败。

        Returns:
            True 如果连续失败达到阈值，应永久降级。
        """
        self._mcp_http_fail_count += 1
        if self._mcp_http_fail_count >= self._mcp_max_fails:
            self._mcp_available = False
            return True
        return False

    def mark_mcp_success(self):
        """标记 MCP HTTP 调用成功，重置失败计数。"""
        self._mcp_available = True
        self._mcp_http_fail_count = 0

    def reset_mcp_state(self):
        """重置 MCP 连接状态，重新探测 HTTP Server。

        用于 MCP Server 重启后恢复 HTTP 调用路径。
        """
        self._mcp_available = None
        self._mcp_http_fail_count = 0


# ── 默认全局上下文（向后兼容） ─────────────────────────────

_default_context: AppContext | None = None


def get_context() -> AppContext:
    """获取当前应用上下文。

    首次调用时懒惰创建默认实例，后续调用返回同一实例。
    线程安全依赖 GIL，多进程下每个进程有独立实例。
    """
    global _default_context
    if _default_context is None:
        _default_context = AppContext()
    return _default_context


def set_context(ctx: AppContext):
    """设置自定义上下文（用于测试注入或自定义配置）。

    在测试中调用此函数注入 mock 实例::

        from common.context import set_context, AppContext
        mock_ctx = AppContext()
        mock_ctx._llm = MockLLMClient()
        set_context(mock_ctx)
    """
    global _default_context
    _default_context = ctx
