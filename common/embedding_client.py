import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class EmbeddingClient:
    """Embedding 客户端，支持 Ollama 本地模型。"""

    def __init__(self):
        self.model: str = os.getenv("EMBEDDING_MODEL", "qwen3-embedding:8b")
        self.base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        self.client = OpenAI(api_key="ollama", base_url=self.base_url)

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


# 全局单例
embedding = EmbeddingClient()
