import sys
from pathlib import Path

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


DEEPSEEK_MODELS = ["deepseek-chat", "deepseek-reasoner", "deepseek-coder"]
OLLAMA_MODELS = ["qwen3.5:4b", "llama3.2", "gemma2"]


def on_backend_change(backend):
    """根据后端选择更新默认值并控制 API Key 显示。"""
    if backend == "ollama":
        return (
            gr.update(value="qwen3.5:4b", choices=OLLAMA_MODELS),  # model
            gr.update(value="", visible=False),  # api_key 隐藏
            gr.update(value="http://localhost:11434/v1", visible=True),  # base_url
        )
    else:
        return (
            gr.update(value="deepseek-chat", choices=DEEPSEEK_MODELS),  # model
            gr.update(value="", visible=True),  # api_key 显示
            gr.update(value="https://api.deepseek.com", visible=True),  # base_url
        )


def get_config():
    cfg = llm.get_config()
    is_ollama = cfg["backend"] == "ollama"
    model_choices = OLLAMA_MODELS if is_ollama else DEEPSEEK_MODELS
    status_msg = f"当前: {cfg['backend']} / {cfg['model']}"
    return (
        cfg["backend"],
        gr.update(value=cfg["model"], choices=model_choices),
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
                model = gr.Dropdown(label="模型", value="deepseek-chat", choices=DEEPSEEK_MODELS)
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
