import sys
import subprocess
from pathlib import Path
from functools import lru_cache

# 将项目根目录添加到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import gradio as gr
from common.llm_client import llm


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


async def chat(message, history):
    messages = [{"role": "system", "content": "你是一个旅行规划助手。"}]
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})
    return await llm.chat_completion(messages)


with gr.Blocks(title="TripMind - 多Agent旅行规划") as app:
    gr.Markdown("# TripMind - 多Agent协同旅行规划")

    with gr.Tabs():
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


if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7861, theme=gr.themes.Soft())
