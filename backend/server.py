"""FastAPI 后端服务器 — 统一封装 KnowSeeker + TripMind + LLM 设置。

启动: uv run uvicorn backend.server:app --host 0.0.0.0 --port 8000
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

# 将项目根目录加入 sys.path，确保导入正确
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import Field, BaseModel

# ── 导入现有模块 ──────────────────────────────────────────

from knowseeker.agent import run_rag_query
from knowseeker.rag_chain import index_document, list_documents, delete_document
from tripmind.orchestrator import (
    adjust_plan,
    run_travel_planner,
    run_travel_planner_stream,
)
from tripmind.types import TravelRequest
from common.context import get_context
from common.mcp_server.server import MCP_HOST, MCP_PORT

# ── MCP Server 生命周期管理 ──────────────────────────────

_mcp_process: subprocess.Popen | None = None


async def _wait_for_mcp_ready(timeout: float = 10.0) -> bool:
    """等待 MCP HTTP Server 就绪（轮询 /mcp endpoint）。"""
    url = f"http://{MCP_HOST}:{MCP_PORT}/mcp"
    deadline = time.time() + timeout
    async with httpx.AsyncClient() as client:
        while time.time() < deadline:
            try:
                resp = await client.get(url, timeout=2)
                if resp.status_code < 500:
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.5)
    return False


def _start_mcp_server():
    """启动 MCP HTTP Server 子进程。"""
    global _mcp_process
    try:
        project_root = Path(__file__).parent.parent
        _mcp_process = subprocess.Popen(
            ["uv", "run", "python", "-m", "common.mcp_server.server"],
            cwd=project_root,
            stdout=subprocess.DEVNULL,
            stderr=None,
        )
        print(f"[MCP] HTTP Server starting (PID: {_mcp_process.pid})")
    except Exception as e:
        print(f"[MCP] Server 启动失败：{e}")
        print("[MCP] Agent 将自动回退到直接调用 tools.py（不影响功能）")


def _stop_mcp_server():
    """关闭 MCP HTTP Server 子进程。"""
    global _mcp_process
    if _mcp_process is None:
        return
    try:
        _mcp_process.terminate()
        _mcp_process.wait(timeout=5)
        print(f"[MCP] HTTP Server stopped (PID: {_mcp_process.pid})")
    except Exception:
        try:
            _mcp_process.kill()
        except Exception:
            pass
    _mcp_process = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期：启动/关闭 MCP Server。"""
    _start_mcp_server()
    # 非阻塞等待 MCP 就绪（不影响 API 启动）
    asyncio.create_task(_wait_and_log_mcp())
    yield
    _stop_mcp_server()


async def _wait_and_log_mcp():
    if _mcp_process and await _wait_for_mcp_ready():
        print(f"[MCP] HTTP Server ready at http://{MCP_HOST}:{MCP_PORT}/mcp")
    else:
        print("[MCP] HTTP Server 启动超时，Agent 将自动回退到直接调用")


# ── 请求 / 响应模型 ──────────────────────────────────────


class ChatRequest(BaseModel):
    question: str


class TravelPlanRequest(BaseModel):
    destination: str
    days: int = Field(ge=1, le=30)
    budget: float = Field(ge=100)
    preferences: list[str] = []
    departure_city: str


class TravelAdjustRequest(BaseModel):
    state: dict
    message: str


class SettingsRequest(BaseModel):
    # 推理层 (LLM)
    backend: str | None = None
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    # 向量化层 (Embedding)
    embedding_model: str | None = None
    embedding_base_url: str | None = None
    # 重排序层 (Reranker)
    reranker_model: str | None = None
    reranker_enabled: bool | None = None


# ── FastAPI 应用 ──────────────────────────────────────────

app = FastAPI(title="AgentForge API", version="0.1.0", lifespan=lifespan)

# CORS — 允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════
# KnowSeeker — RAG 问答与文档管理
# ═══════════════════════════════════════════════════════════

# 异步任务存储
_tasks: dict[str, dict] = {}
_tasks_lock = asyncio.Lock()


async def _run_rag_task(task_id: str, question: str):
    """后台执行 RAG 查询，逐步更新任务状态。"""
    try:
        async with _tasks_lock:
            _tasks[task_id]["status"] = "processing"
            _tasks[task_id]["progress"] = 0.1

        result = await run_rag_query(question)

        async with _tasks_lock:
            _tasks[task_id].update(
                {
                    "status": "completed",
                    "progress": 1.0,
                    "answer": result.get("answer", ""),
                    "thinking_trace": result.get("thinking_trace", []),
                    "llm_thinking": result.get("llm_thinking", []),
                    "citations": result.get("citations", []),
                }
            )
    except Exception as e:
        async with _tasks_lock:
            _tasks[task_id].update({"status": "error", "progress": 1.0, "error": str(e)})


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """RAG 问答：创建异步任务，立即返回 taskId。"""
    task_id = uuid.uuid4().hex[:12]
    async with _tasks_lock:
        _tasks[task_id] = {
            "status": "pending",
            "progress": 0.0,
            "question": request.question,
        }
    # 启动后台任务
    asyncio.create_task(_run_rag_task(task_id, request.question))
    return {"taskId": task_id}


@app.get("/api/chat/{task_id}")
async def get_chat_task(task_id: str):
    """获取异步 RAG 任务状态和结果。"""
    async with _tasks_lock:
        task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """上传文档到知识库。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    tmp_path = None
    try:
        suffix = Path(file.filename).suffix or ".txt"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        result = index_document(tmp_path, file.filename)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.get("/api/documents")
async def get_documents():
    """列出知识库中所有已索引文档。"""
    try:
        return list_documents()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/documents/{doc_id}")
async def remove_document(doc_id: str):
    """从知识库删除指定文档。"""
    try:
        deleted = delete_document(doc_id)
        return {"deleted": deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# TripMind — 旅游规划
# ═══════════════════════════════════════════════════════════


@app.post("/api/travel/plan")
async def travel_plan(request: TravelPlanRequest):
    """一次性旅行规划：返回完整的多 Agent 协作结果。"""
    try:
        tr: TravelRequest = {
            "destination": request.destination,
            "days": request.days,
            "budget": request.budget,
            "preferences": request.preferences,
            "departure_city": request.departure_city,
        }
        result = await run_travel_planner(tr)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/travel/plan/stream")
async def travel_plan_stream(request: TravelPlanRequest):
    """流式旅行规划：通过 SSE 实时推送各 Agent 进度。

    编排器内部使用 graph.astream() 按图拓扑顺序推进节点，
    每个节点完成后 yield 该节点的 Agent 结果。
    最终 yield __full_state__ 供前端追问调整使用。
    """

    async def event_generator():
        tr: TravelRequest = {
            "destination": request.destination,
            "days": request.days,
            "budget": request.budget,
            "preferences": request.preferences,
            "departure_city": request.departure_city,
        }
        try:
            async for step in run_travel_planner_stream(tr):
                yield f"data: {json.dumps(step, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/travel/adjust")
async def travel_adjust(request: TravelAdjustRequest):
    """追问调整：根据用户指令修改已有旅行规划。"""
    try:
        result = await adjust_plan(request.state, request.message)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# LLM 设置
# ═══════════════════════════════════════════════════════════


@app.get("/api/models")
async def get_models(backend: str | None = None):
    """获取 LLM 后端可用模型列表。

    可通过 ?backend=ollama 或 ?backend=deepseek 指定目标后端，
    不传则使用当前 llm.backend 的值。
    """
    try:
        models = await get_context().llm.list_models(backend=backend)
        target = backend or get_context().llm.backend
        return {"backend": target, "models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/settings")
async def get_settings():
    """获取当前全部模型配置（推理层 + 向量化层 + 重排序层）。"""
    try:
        llm_config = get_context().llm.get_config()
        emb_config = get_context().embedding.get_config()
        rerank_config = get_context().reranker.get_config()
        return {
            # 推理层
            "backend": llm_config.get("backend"),
            "model": llm_config.get("model"),
            "api_key": llm_config.get("api_key"),
            "base_url": llm_config.get("base_url"),
            # 向量化层
            "embedding_model": emb_config.get("model"),
            "embedding_base_url": emb_config.get("base_url"),
            # 重排序层
            "reranker_model": rerank_config.get("model"),
            "reranker_enabled": rerank_config.get("enabled"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/settings")
async def update_settings(settings: SettingsRequest):
    """更新模型配置并持久化到 .env。

    三层独立配置：
    - 推理层: DeepSeek / Ollama 热切换
    - 向量化层: Ollama 本地模型
    - 重排序层: sentence-transformers 本地模型，可开关
    """
    try:
        # 推理层
        if settings.backend or settings.model or settings.api_key or settings.base_url:
            get_context().llm.update(
                backend=settings.backend,
                model=settings.model,
                api_key=settings.api_key,
                base_url=settings.base_url,
            )

        # 向量化层
        if settings.embedding_model or settings.embedding_base_url:
            get_context().embedding.update(
                model=settings.embedding_model,
                base_url=settings.embedding_base_url,
            )

        # 重排序层
        if settings.reranker_model or settings.reranker_enabled is not None:
            get_context().reranker.update(
                model=settings.reranker_model,
                enabled=settings.reranker_enabled,
            )

        # 返回最新配置
        return await get_settings()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 健康检查 ──────────────────────────────────────────────


@app.get("/api/health")
async def health():
    return {"status": "ok"}
