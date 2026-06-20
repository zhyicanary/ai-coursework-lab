import sys
import subprocess
import asyncio
import warnings
from pathlib import Path
from functools import lru_cache

# 过滤 Gradio 依赖中的 Starlette 弃用警告（Gradio 尚未适配 Starlette 新常量名）
warnings.filterwarnings("ignore", message=".*HTTP_422_UNPROCESSABLE_ENTITY.*")

# 将项目根目录添加到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import gradio as gr
from common.llm_client import llm
from tripmind.orchestrator import TravelRequest, run_travel_planner, adjust_plan


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
        import httpx
        from dotenv import load_dotenv
        import os
        
        load_dotenv()
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        
        if api_key:
            headers = {"Authorization": f"Bearer {api_key}"}
            resp = httpx.get("https://api.deepseek.com/models", headers=headers, timeout=5)
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
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            models = []
            for line in result.stdout.strip().split("\n")[1:]:
                name = line.split()[0] if line.strip() else None
                if name:
                    models.append(name)
            return models if models else ["qwen3.5:4b"]
        return ["qwen3.5:4b"]
    except Exception:
        return ["qwen3.5:4b"]


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
        default_model = saved or "qwen3.5:4b"
        return (
            gr.update(value=default_model, choices=[default_model], allow_custom_value=True),
            gr.update(value="", visible=False),
            gr.update(value="http://localhost:11434/v1", visible=True),
        )
    else:
        saved = cfg["model"] if cfg["backend"] == "deepseek" else None
        default_model = saved or "deepseek-chat"
        return (
            gr.update(value=default_model, choices=[default_model], allow_custom_value=True),
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
    choices = [saved_model] if saved_model else (["deepseek-chat"] if not is_ollama else ["qwen3.5:4b"])
    return (
        cfg["backend"],
        gr.update(value=saved_model, choices=choices, allow_custom_value=True),
        gr.update(value=cfg["api_key"], visible=not is_ollama),
        cfg["base_url"],
        f"当前: {cfg['backend']} / {cfg['model']}",
    )


async def plan_travel(destination, days, budget, departure, preferences):
    """运行多 Agent 旅游规划"""
    if not destination or not days or not budget or not departure:
        gr.Warning("请填写所有必填字段")
        return "请填写所有必填字段", "", "", None
    
    request = TravelRequest(
        destination=destination,
        days=int(days),
        budget=float(budget),
        preferences=[p.strip() for p in preferences.split(",") if p.strip()] if preferences else [],
        departure_city=departure
    )
    
    try:
        result = await run_travel_planner(request)
        
        logs = "\n".join([f"[{log['step']}] {log['message']}" for log in result.get("agent_logs", [])])
        final_plan = result.get("final_plan", "规划失败")
        
        agent_status = f"天气: {'✅' if result.get('weather_result') else '❌'}\n"
        agent_status += f"交通: {'✅' if result.get('transport_result') else '❌'}\n"
        agent_status += f"住宿: {'✅' if result.get('hotel_result') else '❌'}\n"
        agent_status += f"行程: {'✅' if result.get('itinerary_result') else '❌'}\n"
        agent_status += f"预算: {'✅' if result.get('budget_result') else '❌'}\n"
        agent_status += f"超预算调整: {'⚠️已调整' if result.get('budget_adjusted') else '—'}"
        
        return final_plan, logs, agent_status, result
    except Exception as e:
        return f"规划失败: {str(e)}", "", "", None


async def handle_adjustment(instruction, previous_state):
    """处理用户调整指令，重新运行受影响 Agent。"""
    if not instruction or not previous_state:
        return "请输入调整指令", "", "", None
    
    try:
        result = await adjust_plan(previous_state, instruction)
        
        logs = "\n".join([f"[{log['step']}] {log['message']}" for log in result.get("agent_logs", [])])
        final_plan = result.get("final_plan", "调整失败")
        
        agent_status = f"天气: {'✅' if result.get('weather_result') else '❌'}\n"
        agent_status += f"交通: {'✅' if result.get('transport_result') else '❌'}\n"
        agent_status += f"住宿: {'✅' if result.get('hotel_result') else '❌'}\n"
        agent_status += f"行程: {'✅' if result.get('itinerary_result') else '❌'}\n"
        agent_status += f"预算: {'✅' if result.get('budget_result') else '❌'}\n"
        agent_status += f"超预算调整: {'⚠️已调整' if result.get('budget_adjusted') else '—'}"
        
        return final_plan, logs, agent_status, result
    except Exception as e:
        return f"调整失败: {str(e)}", "", "", None


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
                preferences = gr.Textbox(label="偏好(逗号分隔)", placeholder="美食,历史文化")

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

            gr.Markdown("### 📄 旅行方案")
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

            # 规划按钮
            plan_btn.click(
                plan_travel,
                [destination, days, budget, departure, preferences],
                [final_plan, agent_logs, agent_status, plan_state]
            )

            # 调整按钮
            adjust_btn.click(
                handle_adjustment,
                [adjustment_input, plan_state],
                [final_plan, agent_logs, agent_status, plan_state]
            )

        with gr.Tab("对话"):
            chatbot = gr.Chatbot()
            msg = gr.Textbox(placeholder="输入你的旅行需求...", label="消息")
            msg.submit(chat, [msg, chatbot], [chatbot]).then(
                lambda: "", None, msg
            )

        with gr.Tab("设置"):
            gr.Markdown("### LLM 配置")
            with gr.Row():
                backend = gr.Radio(
                    ["deepseek", "ollama"], label="后端", value="deepseek"
                )
            with gr.Row():
                model = gr.Dropdown(label="模型", value="deepseek-chat", choices=[], allow_custom_value=True)
                api_key = gr.Textbox(label="API Key", type="password", value="", visible=True)
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
            ).then(
                refresh_model_list,
                [backend],
                [model],
            )

            # 页面加载时回显当前配置，然后后台拉取模型列表
            app.load(
                get_config, None, [backend, model, api_key, base_url, status]
            ).then(
                refresh_model_list,
                [backend],
                [model],
            )


# ─── MCP Server 生命周期管理 ──────────────────────────────

_mcp_process: subprocess.Popen | None = None


def start_mcp_server():
    """启动 MCP Server 子进程（后台运行）。"""
    global _mcp_process
    try:
        project_root = Path(__file__).parent.parent
        _mcp_process = subprocess.Popen(
            ["uv", "run", "python", "-m", "common.mcp_server.server"],
            cwd=project_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"[MCP] Server started (PID: {_mcp_process.pid})")
    except Exception as e:
        print(f"[MCP] Server 启动失败：{e}")
        print("[MCP] Agent 将直接调用 tools.py（不影响功能）")


def stop_mcp_server():
    """关闭 MCP Server 子进程。"""
    global _mcp_process
    if _mcp_process is not None:
        try:
            _mcp_process.terminate()
            _mcp_process.wait(timeout=5)
            print(f"[MCP] Server stopped")
        except Exception:
            _mcp_process.kill()
        _mcp_process = None


# 启动 MCP Server（非阻塞）
try:
    start_mcp_server()
except Exception:
    pass

if __name__ == "__main__":
    try:
        app.launch(server_name="0.0.0.0", server_port=7861, theme=gr.themes.Soft())
    finally:
        stop_mcp_server()
