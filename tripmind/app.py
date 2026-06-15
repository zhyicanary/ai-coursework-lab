import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import gradio as gr
from common.llm_client import llm


def update_settings(backend, model, api_key, base_url):
    llm.update(backend=backend, model=model, api_key=api_key, base_url=base_url)
    return f"已切换到 {backend} / {model}"


def get_config():
    cfg = llm.get_config()
    return cfg["backend"], cfg["model"], cfg["api_key"], cfg["base_url"]


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
                model = gr.Textbox(label="模型", value="deepseek-chat")
                api_key = gr.Textbox(label="API Key", type="password", value="")
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

            # 页面加载时回显当前配置
            app.load(get_config, None, [backend, model, api_key, base_url])


if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7861, theme=gr.themes.Soft())
