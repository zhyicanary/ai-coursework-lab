"""KnowSeeker — Agentic RAG 知识助手（Streamlit 前端）。

运行方式：
  uv run streamlit run knowseeker/app.py

侧边栏：文档上传 / 文档列表 / 删除
主区域：对话面板 + Agent 思维链可视化
"""

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中，否则无法 import common 模块
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import asyncio
import os
import tempfile

import streamlit as st

from common.document_loader import list_supported_extensions
from knowseeker.rag_chain import index_document, list_documents, delete_document
from knowseeker.agent import run_rag_query

# ── 页面配置 ─────────────────────────────────────────────

st.set_page_config(
    page_title="KnowSeeker — Agentic RAG 知识助手",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session State 初始化 ────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []  # [{"role": "user"|"assistant", "content": ..., "thinking_trace": ..., "citations": ...}]

if "thinking_expanded" not in st.session_state:
    st.session_state.thinking_expanded = True


# ── 辅助函数 ─────────────────────────────────────────────


def refresh_doc_list():
    """刷新文档列表（存入 session_state 缓存）。"""
    try:
        st.session_state.doc_list = list_documents()
    except Exception as e:
        st.session_state.doc_list = []
        st.warning(f"获取文档列表失败：{e}")


def run_agent_sync(question: str) -> dict:
    """同步包装异步 agent 调用。"""
    return asyncio.run(run_rag_query(question))


# ── 侧边栏：文档管理 ─────────────────────────────────────

with st.sidebar:
    st.title("📁 文档管理")
    st.caption("上传文档后即可提问")

    # 上传区域
    uploaded_file = st.file_uploader(
        "上传文档",
        type=list_supported_extensions(),
        help=f"支持格式：{', '.join(list_supported_extensions())}",
    )

    if uploaded_file is not None:
        with st.spinner("正在解析并索引文档..."):
            try:
                # 保存到临时文件
                suffix = Path(uploaded_file.name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name

                result = index_document(tmp_path, filename=uploaded_file.name)
                os.unlink(tmp_path)  # 清理临时文件

                st.success(f"✅ 入库完成：{result['file_name']}（{result['chunks_count']} 个片段）")
                refresh_doc_list()
            except Exception as e:
                err_msg = str(e)
                if "Connection error" in err_msg or "Connection refused" in err_msg:
                    st.error("❌ Ollama 服务未运行，无法完成向量化。请先启动：`ollama serve`")
                else:
                    st.error(f"❌ 索引失败：{err_msg}")

    st.divider()

    # 文档列表
    st.subheader("📄 已入库文档")

    if "doc_list" not in st.session_state:
        refresh_doc_list()

    doc_list = st.session_state.get("doc_list", [])

    if not doc_list:
        st.caption("暂无文档，请上传")
    else:
        for doc in doc_list:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(f"📄 {doc['doc_id'].rsplit('_', 1)[0]}")
                st.caption(f"{doc['chunks_count']} 个片段")
            with col2:
                if st.button("🗑️", key=f"del_{doc['doc_id']}", help="删除此文档"):
                    delete_document(doc["doc_id"])
                    refresh_doc_list()
                    st.rerun()

    st.divider()
    st.caption("💡 Agentic RAG 机制")
    st.markdown(
        """
    与传统一次性检索不同，本系统的 AI Agent 会：
    1. **分析**问题复杂度
    2. **制定**检索策略
    3. **评估**结果充分性
    4. **自主决定**是否需要多轮检索
    5. **综合**生成带引用的回答
    """
    )


# ── 主区域：对话 ────────────────────────────────────────

st.title("🤖 KnowSeeker — Agentic RAG 知识助手")

# 显示聊天历史
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # Agent 消息显示思维链
        if msg["role"] == "assistant" and msg.get("thinking_trace"):
            with st.expander("🧠 思考过程", expanded=st.session_state.thinking_expanded):
                for step in msg["thinking_trace"]:
                    icon = "📋" if step["step"] == "analyze" else "🔍" if step["step"] == "retrieve" else "📊" if step["step"] == "evaluate" else "🔄" if step["step"] == "reformulate" else "📝"
                    st.markdown(f"**{icon} {step['content']}**")
                    if step.get("detail"):
                        st.caption(step["detail"])
                    st.divider()

        # 引用来源
        if msg["role"] == "assistant" and msg.get("citations"):
            with st.expander("📎 引用来源", expanded=False):
                for c in msg["citations"]:
                    st.code(f"来源：{c['doc_name']}")

# 聊天输入框
if prompt := st.chat_input("请输入您的问题..."):
    # 添加用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 检查是否有文档
    doc_list = st.session_state.get("doc_list", [])
    if not doc_list and "doc_list" in st.session_state:
        doc_list = list_documents()
        st.session_state.doc_list = doc_list

    if not doc_list:
        with st.chat_message("assistant"):
            st.warning("⚠️ 知识库为空，请先在左侧上传文档后再提问。")
        st.session_state.messages.append({
            "role": "assistant",
            "content": "⚠️ 知识库为空，请先在左侧上传文档后再提问。",
            "thinking_trace": [],
            "citations": [],
        })
    else:
        # Agent 处理
        with st.chat_message("assistant"):
            with st.spinner("🤔 Agent 正在思考..."):
                try:
                    result = run_agent_sync(prompt)

                    answer = result.get("answer", "（未能生成回答）")
                    thinking_trace = result.get("thinking_trace", [])
                    citations = result.get("citations", [])

                    st.markdown(answer)

                    # 显示思维链
                    if thinking_trace:
                        with st.expander("🧠 思考过程", expanded=True):
                            for step in thinking_trace:
                                icon_map = {
                                    "analyze": "📋",
                                    "retrieve": "🔍",
                                    "evaluate": "📊",
                                    "reformulate": "🔄",
                                    "generate": "📝",
                                }
                                icon = icon_map.get(step["step"], "🤖")
                                st.markdown(f"**{icon} {step['content']}**")
                                if step.get("detail"):
                                    st.caption(step["detail"])
                                st.divider()

                    # 引用来源
                    if citations:
                        with st.expander("📎 引用来源", expanded=False):
                            for c in citations:
                                st.code(f"来源：{c['doc_name']}")

                    # 存入历史
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "thinking_trace": thinking_trace,
                        "citations": citations,
                    })

                except Exception as e:
                    err_msg = str(e)
                    if "Connection error" in err_msg or "Connection refused" in err_msg:
                        hint = "Ollama 服务未运行，请先启动：`ollama serve`"
                    else:
                        hint = err_msg
                    st.error(f"❌ Agent 执行异常：{hint}")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"❌ 处理问题时出现异常：{hint}",
                        "thinking_trace": [],
                        "citations": [],
                    })
