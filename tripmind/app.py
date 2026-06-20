import sys
import subprocess
import asyncio
from pathlib import Path
from functools import lru_cache

# 将项目根目录添加到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import gradio as gr
from common.llm_client import llm
from tripmind.orchestrator import TravelRequest, run_travel_planner


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
    """根据后端选择更新模型列表和 API Key 显示，使用该后端已保存的模型。"""
    cfg = llm.get_config()
    if backend == "ollama":
        models = fetch_ollama_models()
        saved = cfg["model"] if cfg["backend"] == "ollama" else None
        models = _ensure_model_in_list(models, saved)
        return (
            gr.update(value=models[0], choices=models),
            gr.update(value="", visible=False),
            gr.update(value="http://localhost:11434/v1", visible=True),
        )
    else:
        models = fetch_deepseek_models()
        saved = cfg["model"] if cfg["backend"] == "deepseek" else None
        models = _ensure_model_in_list(models, saved)
        return (
            gr.update(value=models[0], choices=models),
            gr.update(value="", visible=True),
            gr.update(value="https://api.deepseek.com", visible=True),
        )


def get_config():
    cfg = llm.get_config()
    is_ollama = cfg["backend"] == "ollama"
    if is_ollama:
        models = fetch_ollama_models()
    else:
        models = fetch_deepseek_models()
    models = _ensure_model_in_list(models, cfg["model"])
    status_msg = f"当前: {cfg['backend']} / {cfg['model']}"
    return (
        cfg["backend"],
        gr.update(value=cfg["model"], choices=models),
        gr.update(value=cfg["api_key"], visible=not is_ollama),
        cfg["base_url"],
        status_msg,
    )


async def plan_travel(destination, days, budget, departure, preferences):
    """运行多 Agent 旅游规划"""
    if not destination or not days or not budget or not departure:
        return "请填写所有必填字段", "", ""
    
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
        agent_status += f"预算: {'✅' if result.get('budget_result') else '❌'}"
        
        return final_plan, logs, agent_status
    except Exception as e:
        return f"规划失败: {str(e)}", "", ""


async def chat(message, history):
    messages = [{"role": "system", "content": "你是一个旅行规划助手。"}]
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})
    return await llm.chat_completion(messages)


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
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 📊 Agent 执行状态")
                    agent_status = gr.Textbox(label="状态", interactive=False)
                with gr.Column():
                    gr.Markdown("### 📨 Agent 通信日志")
                    agent_logs = gr.Textbox(label="日志", interactive=False, lines=8)
            
            gr.Markdown("### 📄 旅行方案")
            final_plan = gr.Markdown()
            
            plan_btn.click(
                plan_travel,
                [destination, days, budget, departure, preferences],
                [final_plan, agent_logs, agent_status]
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

            # 后端切换时更新默认值并控制 API Key 显示
            backend.change(
                on_backend_change,
                [backend],
                [model, api_key, base_url],
            )

            # 页面加载时回显当前配置
            app.load(get_config, None, [backend, model, api_key, base_url, status])


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
