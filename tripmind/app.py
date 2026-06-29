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
    gr.Info(f"✅ 配置已保存 — {backend} / {model}")
    return f"当前: {backend} / {model}"


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
    """将 state 中的 Agent 结果格式化为漂亮的 HTML 状态面板。"""
    agents = [
        ("🌤️", "天气", "weather_result"),
        ("✈️", "交通", "transport_result"),
        ("🏨", "住宿", "hotel_result"),
        ("🗺️", "行程", "itinerary_result"),
        ("💰", "预算", "budget_result"),
    ]
    items = []
    for icon, label, key in agents:
        val = state.get(key)
        if val is None:
            cls, badge = "waiting", "⏳"
        elif val.get("error"):
            cls, badge = "error", "❌"
        else:
            cls, badge = "done", "✅"
        items.append(
            f'<div class="agent-item {cls}">'
            f'<span class="agent-icon">{icon}</span>'
            f'<span class="agent-name">{label}</span>'
            f'<span class="agent-badge">{badge}</span>'
            f"</div>"
        )

    # 调整指示器
    adjusted = state.get("budget_adjusted", False)
    adj_cls = "done" if adjusted else "waiting"
    adj_badge = "⚠️ 已调整" if adjusted else "—"
    items.append(
        f'<div class="agent-item {adj_cls}">'
        f'<span class="agent-icon">💡</span>'
        f'<span class="agent-name">调整</span>'
        f'<span class="agent-badge">{adj_badge}</span>'
        f"</div>"
    )

    return f'<div class="agent-status-grid">{"".join(items)}</div>'


def _get_default_status() -> str:
    """初始状态面板 HTML — 所有 Agent 等待中。"""
    agents = [
        ("🌤️", "天气"),
        ("✈️", "交通"),
        ("🏨", "住宿"),
        ("🗺️", "行程"),
        ("💰", "预算"),
        ("💡", "调整"),
    ]
    items = "".join(
        f'<div class="agent-item waiting">'
        f'<span class="agent-icon">{icon}</span>'
        f'<span class="agent-name">{label}</span>'
        f'<span class="agent-badge">⏳</span>'
        f"</div>"
        for icon, label in agents
    )
    return f'<div class="agent-status-grid">{items}</div>'


def _get_cancelled_status() -> str:
    """中断状态面板 HTML — 所有 Agent 标记为取消。"""
    agents = [
        ("🌤️", "天气"),
        ("✈️", "交通"),
        ("🏨", "住宿"),
        ("🗺️", "行程"),
        ("💰", "预算"),
        ("💡", "调整"),
    ]
    items = "".join(
        f'<div class="agent-item cancelled">'
        f'<span class="agent-icon">{icon}</span>'
        f'<span class="agent-name">{label}</span>'
        f'<span class="agent-badge">⏹️</span>'
        f"</div>"
        for icon, label in agents
    )
    return f'<div class="agent-status-grid">{items}</div>'


def handle_cancel():
    """中断规划时的回调 — 重置 UI 到干净状态。"""
    return (
        "❌ **规划已中断** — 你可以修改需求后重新开始。",
        "⚠️ 用户中断了规划流程\n",
        _get_cancelled_status(),
        None,
        gr.update(visible=False),
        gr.update(interactive=False),
    )


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
            gr.update(interactive=False),
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

    # 初始状态：启用停止按钮
    progress(0.02, "需求分析完成，准备调度")
    yield (
        "",
        "[🎯调度] 需求分析完成，准备调度 6 个子任务\n",
        _get_default_status(),
        None,
        gr.update(visible=False),
        gr.update(interactive=True),
    )

    needs_cleanup = True
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

            is_final = bool(state.get("final_plan"))
            if is_final:
                needs_cleanup = False
            yield final_plan, logs, status, state, download_update, gr.update(
                interactive=not is_final
            )

        # 流结束后：若未正常完成（无 final_plan），停用停止按钮
        if needs_cleanup:
            yield (
                "",
                "",
                _get_default_status(),
                None,
                gr.update(visible=False),
                gr.update(interactive=False),
            )
    except Exception as e:
        yield (
            f"规划失败: {str(e)}",
            "",
            _get_default_status(),
            None,
            gr.update(visible=False),
            gr.update(interactive=False),
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


# ─── 自定义 CSS ─────────────────────────────────────────────

CUSTOM_CSS = """
/* Agent 状态面板：三列响应式网格 */
.agent-status-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin: 4px 0;
}

.agent-item {
    display: flex;
    align-items: center;
    padding: 14px 18px;
    background: var(--background-fill-primary, #ffffff);
    border: 1px solid var(--border-color-primary, #e5e7eb);
    border-radius: 12px;
    gap: 12px;
    transition: all 0.3s ease;
    min-height: 48px;
}

.agent-item.waiting {
    border-left: 4px solid #d1d5db;
    opacity: 0.75;
}

.agent-item.done {
    border-left: 4px solid #10b981;
    background: #f0fdf4;
}

.agent-item.error {
    border-left: 4px solid #ef4444;
    background: #fef2f2;
}

.agent-item.cancelled {
    border-left: 4px solid #f59e0b;
    background: #fffbeb;
    opacity: 0.85;
}

.agent-icon {
    font-size: 1.5em;
    width: 36px;
    text-align: center;
    flex-shrink: 0;
}

.agent-name {
    flex: 1;
    font-weight: 600;
    font-size: 0.95em;
    color: #374151;
}

.agent-badge {
    font-size: 1.2em;
    flex-shrink: 0;
}

/* 日志框：终端风格 */
.log-box textarea {
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Courier New', monospace !important;
    font-size: 13px !important;
    line-height: 1.6 !important;
    background: #1e293b !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
    padding: 12px !important;
    resize: vertical !important;
}

/* Chatbot 气泡美化 */
.chat-container {
    border-radius: 12px;
    overflow: hidden;
}

/* 表单卡片区域 */
.form-section {
    margin-bottom: 4px;
}

/* 方案输出区域 */
.plan-output {
    min-height: 120px;
}

/* 更好的按钮间距 */
.action-row {
    gap: 12px;
}

/* 针对小屏幕的适应 */
@media (max-width: 768px) {
    .agent-status-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}
@media (max-width: 480px) {
    .agent-status-grid {
        grid-template-columns: 1fr;
    }
}
"""

# ─── UI ─────────────────────────────────────────────────────

with gr.Blocks(
    title="TripMind - 多Agent旅行规划",
) as app:
    # ── 页头 ──
    with gr.Row():
        gr.Markdown(
            "# 🧠 TripMind — 多Agent协同旅行规划\n"
            "*智能旅行规划系统 · 多智能体协作 · AI 驱动*"
        )

    with gr.Tabs():
        # ════════════════════════════════════════════════════
        # Tab 1: 旅行规划
        # ════════════════════════════════════════════════════
        with gr.Tab("🗺️ 旅行规划"):
            # ── 输入表单 ──
            with gr.Group():
                gr.Markdown("### 📝 旅行需求")
                with gr.Row():
                    destination = gr.Textbox(
                        label="目的地",
                        placeholder="成都",
                        elem_classes="form-section",
                    )
                    days = gr.Number(
                        label="天数",
                        value=3,
                        minimum=1,
                        maximum=30,
                        elem_classes="form-section",
                    )
                    budget = gr.Number(
                        label="预算 (元)",
                        value=3000,
                        minimum=100,
                        elem_classes="form-section",
                    )
                with gr.Row():
                    departure = gr.Textbox(
                        label="出发地",
                        placeholder="北京",
                        elem_classes="form-section",
                    )
                    preferences = gr.Textbox(
                        label="偏好 (逗号分隔)",
                        placeholder="美食, 历史文化, 自然风光",
                        elem_classes="form-section",
                    )

            # ── 操作按钮 ──
            with gr.Row(elem_classes="action-row"):
                plan_btn = gr.Button(
                    "🚀 开始规划",
                    variant="primary",
                    scale=3,
                    elem_classes="action-row",
                )
                stop_btn = gr.Button(
                    "⏹️ 停止",
                    variant="stop",
                    scale=1,
                    min_width=100,
                    interactive=False,
                )

            # 存储上一次规划的状态（供调整使用）
            plan_state = gr.State()

            # ── Agent 状态面板 ──
            gr.Markdown("### 🤖 Agent 执行状态")
            agent_status = gr.HTML(value=_get_default_status())

            # ── Agent 通信日志（可折叠）──
            with gr.Accordion("📨 Agent 通信日志", open=False):
                agent_logs = gr.Textbox(
                    label="日志",
                    lines=10,
                    max_lines=20,
                    interactive=False,
                    elem_classes="log-box",
                )

            # ── 旅行方案输出 ──
            with gr.Group():
                with gr.Row():
                    gr.Markdown("### 📄 旅行方案")
                    download_btn = gr.DownloadButton(
                        "📥 下载方案",
                        variant="secondary",
                        visible=False,
                        min_width=140,
                    )
                final_plan = gr.Markdown(elem_classes="plan-output")

            # ── 追问调整区域 ──
            with gr.Accordion("🔄 追问调整方案", open=False):
                gr.Markdown(
                    "对生成的方案不满意？输入调整指令，仅重算受影响 Agent。"
                )
                with gr.Row():
                    adjustment_input = gr.Textbox(
                        label="调整指令",
                        placeholder='例如："预算提高到 5000"、"换便宜的酒店"、"偏好美食、自然风光"、"改成去西安"',
                        scale=5,
                    )
                    adjust_btn = gr.Button(
                        "📋 应用调整", variant="secondary", scale=1, min_width=120
                    )

            # ── 事件绑定 ──

            # 规划按钮 — 流式输出（6 个输出组件，含 stop_btn 状态管理）
            plan_event = plan_btn.click(
                plan_travel,
                [destination, days, budget, departure, preferences],
                [
                    final_plan,
                    agent_logs,
                    agent_status,
                    plan_state,
                    download_btn,
                    stop_btn,
                ],
            )

            # 调整按钮（5 个输出，不含 stop_btn）
            adjust_btn.click(
                handle_adjustment,
                [adjustment_input, plan_state],
                [final_plan, agent_logs, agent_status, plan_state, download_btn],
            )

            # 停止按钮 — 中断规划并重置 UI
            stop_btn.click(
                handle_cancel,
                None,
                [final_plan, agent_logs, agent_status, plan_state, download_btn, stop_btn],
                cancels=[plan_event],
            )

        # ════════════════════════════════════════════════════
        # Tab 2: 对话
        # ════════════════════════════════════════════════════
        with gr.Tab("💬 对话"):
            chatbot = gr.Chatbot(
                label="旅行助手",
                height=460,
                elem_classes="chat-container",
            )
            with gr.Row():
                msg = gr.Textbox(
                    placeholder="输入你的旅行需求...",
                    label="消息",
                    scale=9,
                    container=True,
                )
                send_btn = gr.Button(
                    "发送",
                    variant="primary",
                    scale=1,
                    min_width=90,
                )
            # 回车发送 / 点击发送
            msg.submit(chat, [msg, chatbot], [chatbot]).then(
                lambda: "", None, msg
            )
            send_btn.click(chat, [msg, chatbot], [chatbot]).then(
                lambda: "", None, msg
            )

        # ════════════════════════════════════════════════════
        # Tab 3: 设置
        # ════════════════════════════════════════════════════
        with gr.Tab("⚙️ 设置"):
            with gr.Group():
                gr.Markdown("### ⚙️ LLM 配置")
                with gr.Row():
                    backend = gr.Radio(
                        ["deepseek", "ollama"],
                        label="后端",
                        value="deepseek",
                    )
                with gr.Row():
                    model = gr.Dropdown(
                        label="模型",
                        value="deepseek-chat",
                        choices=[],
                        allow_custom_value=True,
                        scale=2,
                    )
                    api_key = gr.Textbox(
                        label="API Key",
                        type="password",
                        value="",
                        visible=True,
                        scale=3,
                    )
                with gr.Row():
                    base_url = gr.Textbox(
                        label="Base URL",
                        value="https://api.deepseek.com",
                    )
                with gr.Row():
                    save_btn = gr.Button("💾 保存设置", variant="primary")
                status = gr.Textbox(
                    label="状态",
                    interactive=False,
                    elem_classes="form-section",
                )

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
        app.launch(
            server_name="0.0.0.0",
            server_port=7861,
            theme=gr.themes.Soft(),
            css=CUSTOM_CSS,
        )
    finally:
        stop_mcp_server()
