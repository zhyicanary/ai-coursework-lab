import os
import re
from pathlib import Path

from dotenv import load_dotenv, set_key
from openai import AsyncOpenAI

# 项目根目录的 .env 文件路径
ENV_FILE = Path(__file__).parent.parent / ".env"

load_dotenv(override=True)


def _parse_thinking(content: str) -> tuple[str, str]:
    """从 LLM 输出中拆分思考过程与最终回答。

    支持的格式：
    - Thinking...\\n...\\n...done thinking.\\n\\n回答
    - <think>...</think>回答
    - <think>...</think>（无回答时只返回思考）
    """
    content = content.strip()

    # 格式1: Thinking... ...done thinking.
    m = re.match(
        r"Thinking\.\.\.\s*\n(.*?)\n\.\.\.done thinking\.\s*\n*(.*)",
        content,
        re.DOTALL,
    )
    if m:
        return (m.group(2).strip(), m.group(1).strip())

    # 格式2: <think>...</think>answer
    m = re.match(r"<think>(.*?)</think>(.*)", content, re.DOTALL)
    if m:
        return (m.group(2).strip(), m.group(1).strip())

    # 无思考块，原样返回
    return (content, "")


class LLMClient:
    """可热切换的 LLM 客户端，支持运行时修改配置。"""

    def __init__(self):
        self.backend: str = os.getenv("LLM_BACKEND", "deepseek")
        self.model: str = ""
        self.api_key: str = ""
        self.base_url: str = ""
        self.client: AsyncOpenAI | None = None
        self._refresh()

    def _refresh(self):
        """根据当前属性重新创建 client，并从 .env 读取最新配置。"""
        load_dotenv(override=True)

        if self.backend == "ollama":
            self.base_url = self.base_url or os.getenv(
                "OLLAMA_BASE_URL", "http://localhost:11434/v1"
            )
            self.api_key = "ollama"
            self.model = self.model or os.getenv("OLLAMA_MODEL", "gemma3:latest")
        else:
            self.base_url = self.base_url or os.getenv(
                "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
            )
            self.api_key = self.api_key or os.getenv("DEEPSEEK_API_KEY", "")
            self.model = self.model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

        if not self.api_key:
            self.api_key = "sk-placeholder"

        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    def update(
        self,
        backend: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        """更新配置并重建 client，同时持久化到 .env 文件。"""
        if backend is not None and backend != self.backend:
            # 切换后端时清空旧配置，避免残留导致请求发到错误地址
            self.backend = backend
            self.model = ""
            self.api_key = ""
            self.base_url = ""
            set_key(str(ENV_FILE), "LLM_BACKEND", backend)
        if model is not None:
            self.model = model
            if self.backend == "ollama":
                set_key(str(ENV_FILE), "OLLAMA_MODEL", model)
            else:
                set_key(str(ENV_FILE), "DEEPSEEK_MODEL", model)
        if api_key is not None and api_key != "":
            self.api_key = api_key
            if self.backend != "ollama":
                set_key(str(ENV_FILE), "DEEPSEEK_API_KEY", api_key)
        if base_url is not None:
            self.base_url = base_url
            if self.backend == "ollama":
                set_key(str(ENV_FILE), "OLLAMA_BASE_URL", base_url)
            else:
                set_key(str(ENV_FILE), "DEEPSEEK_BASE_URL", base_url)
        self._refresh()

    def get_config(self) -> dict:
        """返回当前配置，供 UI 回显。"""
        return {
            "backend": self.backend,
            "model": self.model,
            "api_key": self.api_key,
            "base_url": self.base_url,
        }

    async def list_models(self, backend: str | None = None) -> list[str]:
        """获取可用模型列表。

        Args:
            backend: 目标后端（"deepseek" / "ollama"），
                    不传则使用 self.backend 当前值。
        """
        target = backend or self.backend
        try:
            if target == "ollama":
                client = AsyncOpenAI(
                    api_key="ollama",
                    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
                )
            else:
                # 查询 DeepSeek 模型时，用 DeepSeek 专属的 key 和 url，
                # 而非 self.api_key/self.base_url（它们可能是 Ollama 的值）
                client = AsyncOpenAI(
                    api_key=os.getenv("DEEPSEEK_API_KEY", self.api_key or ""),
                    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                )
            response = await client.models.list()
            models = [m.id for m in response.data]
            return models if models else self._default_models(target)
        except Exception:
            return self._default_models(target)

    def _default_models(self, backend: str | None = None) -> list[str]:
        """兜底默认模型列表（当 API 不可用时使用）。

        官方模型列表参考：https://api-docs.deepseek.com/zh-cn/api/list-models
        """
        if (backend or self.backend) == "ollama":
            return ["gemma3:latest"]
        return ["deepseek-chat", "deepseek-reasoner"]

    async def chat_completion(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        response = await self.client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    async def chat_completion_thinking(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> tuple[str, str]:
        """调用 LLM 并拆分思考过程与最终回答。

        返回 (answer, thinking):
          - answer: 模型最终输出（去掉思考块）
          - thinking: 模型思考过程文本（无思考块时为空字符串）
        """
        response = await self.client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        msg = response.choices[0].message
        content = msg.content or ""
        reasoning = getattr(msg, "reasoning_content", None) or ""

        if content:
            # 模型把回答放在 content，思考放在 reasoning_content
            answer, thinking = _parse_thinking(content)
            if not thinking and reasoning:
                thinking = reasoning
            return (answer, thinking)
        elif reasoning:
            # 模型把所有内容放在 reasoning_content（如 qwen3.5 开启 thinking 时）
            return _parse_thinking(reasoning)
        else:
            return ("", "")


# 实例通过 common.context.get_context().llm 获取，不再提供模块级单例
