# TripMind — 基于多智能体协同的旅游规划系统

> 范式二：多 Agent 协同编排 | [返回合集首页](../README.md)

---

## 项目简介

用户输入目的地、天数、预算，7 个 AI Agent 自动分工协作（查交通、比住宿、排行程、看天气、算预算），实时展示 Agent 协作过程，最终生成完整旅行方案。

**核心创新点：** 不是单个 AI 完成所有工作，而是多个专业 Agent 像团队一样协同——有分工、有依赖、有通信。

---

## Agent 团队

| Agent | 职责 | 依赖 |
| --- | --- | --- |
| 调度 Agent | 理解需求、拆解任务、调度执行 | 无 |
| 交通 Agent | 查询航班/高铁 | 无 |
| 住宿 Agent | 推荐酒店 | 无 |
| 天气 Agent | 查询天气预报 | 无 |
| 行程 Agent | 规划每日行程 | 天气 + 交通 |
| 预算 Agent | 汇总费用、预算检查 | 交通 + 住宿 + 行程 |
| 汇总 Agent | 生成最终方案 | 全部 |

---

## 快速开始

```bash
# 在项目根目录
uv sync
cp .env.example .env  # 编辑填入 DeepSeek API Key
uv run python tripmind/app.py
```

---

## 技术栈

| 层次 | 选型 | 说明 |
| --- | --- | --- |
| 大模型 | DeepSeek API | 驱动所有 Agent |
| 编排框架 | LangChain + LangGraph | DAG 依赖调度 |
| 协议 | MCP (Python SDK) | 工具调用标准化 |
| 向量数据库 | ChromaDB | 景点知识库 |
| 前端 | Gradio | 多组件复杂布局 |
| 包管理 | uv | Python 包管理 |

---

## 设计文档

- [需求分析与软件设计](../design/03-tripmind.md)
- [技术栈选型](../design/01-tech-stack.md)
