import os
from pathlib import Path

from dotenv import load_dotenv, set_key
from openai import OpenAI

# 项目根目录的 .env 文件路径
ENV_FILE = Path(__file__).parent.parent / ".env"

load_dotenv()


class EmbeddingClient:
    """Embedding 客户端，支持 Ollama 本地模型。

    支持运行时热切换模型和 Base URL，通过 update() 方法持久化到 .env。
    """

    def __init__(self):
        self.model: str = os.getenv("EMBEDDING_MODEL", "qwen3-embedding:8b")
        self.base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        self.client = OpenAI(api_key="ollama", base_url=self.base_url)

    def update(self, model: str | None = None, base_url: str | None = None):
        """运行时切换模型和/或 Base URL，持久化到 .env。

        Args:
            model: 新的 Embedding 模型名（如 "qwen3-embedding:8b"）。
            base_url: 新的 Ollama 服务地址。
        """
        load_dotenv(override=True)
        if model:
            self.model = model
            set_key(str(ENV_FILE), "EMBEDDING_MODEL", model)
        if base_url:
            self.base_url = base_url
            set_key(str(ENV_FILE), "OLLAMA_BASE_URL", base_url)
            self.client = OpenAI(api_key="ollama", base_url=self.base_url)

    def get_config(self) -> dict:
        """返回当前配置，供 UI 回显。"""
        return {
            "model": self.model,
            "base_url": self.base_url,
        }

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """将文本列表转换为向量。"""
        response = self.client.embeddings.create(
            model=self.model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        """将单条查询文本转换为向量。"""
        return self.embed_texts([text])[0]


# 实例通过 common.context.get_context().embedding 获取，不再提供模块级单例
