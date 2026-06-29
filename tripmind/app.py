import asyncio
import subprocess
import sys
import tempfile
import warnings
from functools import lru_cache
from pathlib import Path

# 过滤 Gradio 依赖中的 Starlette 弃用警告（Gradio 尚未适配 Starlette 新常量名）
warnings.filterwarnings("ignore", message=".*HTTP_422_UNPROCESSABLE_ENTITY.*")

# 将项目根目录添加到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import gradio as gr

from common.llm_client import llm
from tripmind.orchestrator import (
    adjust_plan,
    run_travel_planner,
    run_travel_planner_stream,
)
from tripmind.types import TravelRequest


def update_settings(backend, model, api_key, base_url):
    if backend == "deepseek" and not api_key:
        gr.Warning("DeepSeek 后端必须填写 API Key")
        return "请填写 API Key"
    llm.update(backend=backend, model=model, api_key=api_key, base_url=base_url)
    return f"已切换到 {backend} / {model}"


@lru_cache(maxsize=1)
def fetch_deepseek_models():
    """从 DeepSeek 官网获取模型列表，失败时返回默认列表"""
    try:
        import os

        import httpx
        from dotenv import load_dotenv

        load_dotenv()
        api_key = os.getenv("DEEPSEEK_API_KEY", "")

        if api_key:
            headers = {"Authorization": f"Bearer {api_key}"}
            resp = httpx.get(
                "https://api.deepseek.com/models", headers=headers, timeout=5
            )
            if resp.status_code == 200:
                models = [m["id"] for m in resp.json().get("data", [])]
                if models:
                    return models

        return ["deepseek-chat", "deepseek-reasoner", "deepseek-coder"]
    except Exception:
        return ["deepseek-chat", "deepseek-reasoner", "deepseek-coder"]


def fetch_ollama_models():
    """从本地 Ollama 获取模型列表"""
    try:
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            models = []
            for line in result.stdout.strip().split("\n")[1:]:
                name = line.split()[0] if line.strip() else None
                if name:
                    models.append(name)
            return models if models else ["gemma4:latest"]
        return ["gemma4:latest"]
    except Exception:
        return ["gemma4:latest"]


def _ensure_model_in_list(models: list[str], saved_model: str) -> list[str]:
    """确保保存的模型在列表中，且排在第一位"""
    if saved_model and saved_model not in models:
        models.insert(0, saved_model)
    elif saved_model and models and models[0] != saved_model:
        models.remove(saved_model)
        models.insert(0, saved_model)
    return models


def on_backend_change(backend):
    """后端切换：瞬间返回默认值（不联网拉模型，避免 UI 卡 loading）。"""
    cfg = llm.get_config()
    if backend == "ollama":
        saved = cfg["model"] if cfg["backend"] == "ollama" else None
        default_model = saved or "gemma4:latest"
        return (
            gr.update(
                value=default_model, choices=[default_model], allow_custom_value=True
            ),
            gr.update(value="", visible=False),
            gr.update(value="http://localhost:11434/v1", visible=True),
        )
    else:
        saved = cfg["model"] if cfg["backend"] == "deepseek" else None
        default_model = saved or "deepseek-chat"
        return (
            gr.update(
                value=default_model, choices=[default_model], allow_custom_value=True
            ),
            gr.update(value="", visible=True),
            gr.update(value="https://api.deepseek.com", visible=True),
        )


def refresh_model_list(backend):
    """后台异步拉取模型列表并更新下拉框（被 .then() 触发，不阻塞 UI）。"""
    cfg = llm.get_config()
    if backend == "ollama":
        models = fetch_ollama_models()
        saved = cfg["model"] if cfg["backend"] == "ollama" else None
    else:
        models = fetch_deepseek_models()
        saved = cfg["model"] if cfg["backend"] == "deepseek" else None
    models = _ensure_model_in_list(models, saved)
    return gr.update(choices=models)


def get_config():
    """页面加载时回显当前配置（快速返回，不触发网络请求）。"""
    cfg = llm.get_config()
    is_ollama = cfg["backend"] == "ollama"
    # 只显示已保存的模型，不联网拉取
    saved_model = cfg["model"]
    choices = (
        [saved_model]
        if saved_model
        else (["deepseek-chat"] if not is_ollama else ["gemma4:latest"])
    )
    return (
        cfg["backend"],
        gr.update(value=saved_model, choices=choices, allow_custom_value=True),
        gr.update(value=cfg["api_key"], visible=not is_ollama),
        cfg["base_url"],
        f"当前: {cfg['backend']} / {cfg['model']}",
    )


def _format_agent_status(state: dict) -> str:
    """将 state 中的 Agent 结果格式化为状态面板文本。"""
    agents = [
        ("🌤️ 天气", "weather_result"),
        ("✈️ 交通", "transport_result"),
        ("🏨 住宿", "hotel_result"),
        ("🗺️ 行程", "itinerary_result"),
        ("💰 预算", "budget_result"),
    ]
    lines = []
    for label, key in agents:
        val = state.get(key)
        if val is None:
            lines.append(f"{label}: ⏳ 等待")
        elif val.get("error"):
            lines.append(f"{label}: ❌ 失败")
        else:
            lines.append(f"{label}: ✅ 完成")
    lines.append(f"💡 调整: {'⚠️ 已调整' if state.get('budget_adjusted') else '—'}")
    return "\n".join(lines)


def _get_default_status() -> str:
    """初始状态面板文本。"""
    agents = ["🌤️ 天气", "✈️ 交通", "🏨 住宿", "🗺️ 行程", "💰 预算"]
    return "\n".join(f"{a}: ⏳ 等待" for a in agents) + "\n💡 调整: —"


async def plan_travel(
    destination, days, budget, departure, preferences, progress=gr.Progress()
):
    """运行多 Agent 旅游规划（流式输出，逐节点更新 UI）。"""
    if not destination or not days or not budget or not departure:
        gr.Warning("请填写所有必填字段")
        yield (
            "请填写所有必填字段",
            "",
            _get_default_status(),
            None,
            gr.update(visible=False),
        )
        return

    request = TravelRequest(
        destination=destination,
        days=int(days),
        budget=float(budget),
        preferences=[p.strip() for p in preferences.split(",") if p.strip()]
        if preferences
        else [],
        departure_city=departure,
    )

    # 初始状态
    progress(0.02, "需求分析完成，准备调度")
    yield (
        "",
        "[🎯调度] 需求分析完成，准备调度 6 个子任务\n",
        _get_default_status(),
        None,
        gr.update(visible=False),
    )

    try:
        async for state in run_travel_planner_stream(request, progress=progress):
            logs = "\n".join(
                f"[{log['step']}] {log['message']}"
                for log in state.get("agent_logs", [])
            )
            final_plan = state.get("final_plan", "")
            status = _format_agent_status(state)

            # 方案生成完毕后创建下载文件
            download_update = gr.update(visible=False)
            if state.get("final_plan"):
                try:
                    tmp = tempfile.NamedTemporaryFile(
                        mode="w", suffix=".md", delete=False, encoding="utf-8"
                    )
                    tmp.write(state["final_plan"])
                    tmp.close()
                    download_update = gr.update(value=tmp.name, visible=True)
                except Exception:
                    pass

            yield final_plan, logs, status, state, download_update
    except Exception as e:
        yield (
            f"规划失败: {str(e)}",
            "",
            _get_default_status(),
            None,
            gr.update(visible=False),
        )


async def handle_adjustment(instruction, previous_state):
    """处理用户调整指令，重新运行受影响 Agent。"""
    if not instruction or not previous_state:
        return (
            "请输入调整指令",
            "",
            _get_default_status(),
            None,
            gr.update(visible=False),
        )

    try:
        result = await adjust_plan(previous_state, instruction)

        logs = "\n".join(
            f"[{log['step']}] {log['message']}" for log in result.get("agent_logs", [])
        )
        final_plan = result.get("final_plan", "调整失败")
        status = _format_agent_status(result)

        # 创建下载文件
        download_update = gr.update(visible=False)
        if result.get("final_plan"):
            try:
                tmp = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".md", delete=False, encoding="utf-8"
                )
                tmp.write(result["final_plan"])
                tmp.close()
                download_update = gr.update(value=tmp.name, visible=True)
            except Exception:
                pass

        return final_plan, logs, status, result, download_update
    except Exception as e:
        return (
            f"调整失败: {str(e)}",
            "",
            _get_default_status(),
            None,
            gr.update(visible=False),
        )


async def chat(message, history):
    """对话 Tab：消息历史格式 [{role, content}]"""
    messages = [{"role": "system", "content": "你是一个旅行规划助手。"}]
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    reply = await llm.chat_completion(messages)

    # 返回完整历史（Gradio Chatbot 要求 list[dict] 格式）
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})
    return history


with gr.Blocks(title="TripMind - 多Agent旅行规划") as app:
    gr.Markdown("# TripMind - 多Agent协同旅行规划")

    with gr.Tabs():
        with gr.Tab("旅行规划"):
            gr.Markdown("### 📝 告诉我你的旅行需求")
            with gr.Row():
                destination = gr.Textbox(label="目的地", placeholder="成都")
                days = gr.Number(label="天数", value=3, minimum=1, maximum=30)
                budget = gr.Number(label="预算(元)", value=3000, minimum=100)
            with gr.Row():
                departure = gr.Textbox(label="出发地", placeholder="北京")
                preferences = gr.Textbox(
                    label="偏好(逗号分隔)", placeholder="美食,历史文化"
                )

            plan_btn = gr.Button("🚀 开始规划", variant="primary")

            # 存储上一次规划的状态（供调整使用）
            plan_state = gr.State()

            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 📊 Agent 执行状态")
                    agent_status = gr.Textbox(label="状态", interactive=False)
                with gr.Column():
                    gr.Markdown("### 📨 Agent 通信日志")
                    agent_logs = gr.Textbox(label="日志", interactive=False, lines=8)

            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📄 旅行方案")
                with gr.Column(scale=1, min_width=160):
                    download_btn = gr.DownloadButton(
                        "📥 下载方案",
                        variant="secondary",
                        visible=False,
                    )
            final_plan = gr.Markdown()

            # ── 追问调整区域 ──
            with gr.Accordion("🔄 追问调整方案", open=False):
                gr.Markdown("对生成的方案不满意？输入调整指令，仅重算受影响 Agent。")
                with gr.Row():
                    adjustment_input = gr.Textbox(
                        label="调整指令",
                        placeholder='例如："预算提高到 5000"、"换便宜的酒店"、"偏好美食、自然风光"、"改成去西安"',
                        scale=5,
                    )
                    adjust_btn = gr.Button("📋 应用调整", variant="secondary", scale=1)

            # 规划按钮 — 流式输出（5 个输出组件）
            plan_btn.click(
                plan_travel,
                [destination, days, budget, departure, preferences],
                [final_plan, agent_logs, agent_status, plan_state, download_btn],
            )

            # 调整按钮
            adjust_btn.click(
                handle_adjustment,
                [adjustment_input, plan_state],
                [final_plan, agent_logs, agent_status, plan_state, download_btn],
            )

        with gr.Tab("对话"):
            chatbot = gr.Chatbot()
            msg = gr.Textbox(placeholder="输入你的旅行需求...", label="消息")
            msg.submit(chat, [msg, chatbot], [chatbot]).then(lambda: "", None, msg)

        with gr.Tab("设置"):
            gr.Markdown("### LLM 配置")
            with gr.Row():
                backend = gr.Radio(
                    ["deepseek", "ollama"], label="后端", value="deepseek"
                )
            with gr.Row():
                model = gr.Dropdown(
                    label="模型",
                    value="deepseek-chat",
                    choices=[],
                    allow_custom_value=True,
                )
                api_key = gr.Textbox(
                    label="API Key", type="password", value="", visible=True
                )
            with gr.Row():
                base_url = gr.Textbox(
                    label="Base URL", value="https://api.deepseek.com"
                )
            save_btn = gr.Button("保存设置", variant="primary")
            status = gr.Textbox(label="状态", interactive=False)
            save_btn.click(
                update_settings,
                [backend, model, api_key, base_url],
                status,
            )

            # 后端切换：瞬间返回默认值（无 loading），再后台拉模型列表
            backend.change(
                on_backend_change,
                [backend],
                [model, api_key, base_url],
                show_progress="hidden",
            ).then(
                refresh_model_list,
                [backend],
                [model],
                show_progress="hidden",
            )

            # 页面加载时回显当前配置，然后后台拉取模型列表
            app.load(
                get_config,
                None,
                [backend, model, api_key, base_url, status],
                show_progress="hidden",
            ).then(
                refresh_model_list,
                [backend],
                [model],
                show_progress="hidden",
            )


# ─── MCP Server 生命周期管理 ──────────────────────────────

_mcp_process: subprocess.Popen | None = None

from common.mcp_server.server import MCP_HOST, MCP_PORT


def _wait_for_mcp_ready(timeout: float = 10.0) -> bool:
    """等待 MCP HTTP Server 就绪（轮询 health endpoint）。"""
    import time

    import httpx

    url = f"http://{MCP_HOST}:{MCP_PORT}/mcp"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = httpx.get(url, timeout=2.0)
            if resp.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def start_mcp_server():
    """启动 MCP HTTP Server 子进程（后台常驻）。"""
    global _mcp_process
    if _mcp_process is not None and _mcp_process.poll() is None:
        return
    try:
        project_root = Path(__file__).parent.parent
        _mcp_process = subprocess.Popen(
            ["uv", "run", "python", "-m", "common.mcp_server.server"],
            cwd=project_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"[MCP] HTTP Server starting (PID: {_mcp_process.pid})")
        if _wait_for_mcp_ready():
            print(
                f"[MCP] HTTP Server ready at http://{MCP_HOST}:{MCP_PORT}/mcp"
            )
        else:
            print("[MCP] HTTP Server 启动超时，Agent 将自动回退到直接调用")
    except Exception as e:
        print(f"[MCP] Server 启动失败：{e}")
        print("[MCP] Agent 将直接调用 tools.py（不影响功能）")


def stop_mcp_server():
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


if __name__ == "__main__":
    # Gradio 热重载模式下，reload 线程不应管理 MCP 生命周期
    if not app._is_running_in_reload_thread:
        start_mcp_server()

    try:
        app.launch(server_name="0.0.0.0", server_port=7861, theme=gr.themes.Soft())
    finally:
        stop_mcp_server()
