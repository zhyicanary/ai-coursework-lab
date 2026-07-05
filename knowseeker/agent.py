"""KnowSeeker Agentic RAG 状态机 — LangGraph 编排。

状态流转：
  analyze_question → retrieve → evaluate_results
       ↑                          │
       └──── reformulate ←────────┘  (need_more_search=True)
                          │
                          └→ generate_answer → END
"""

import json
import re
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from common.context import get_context
from knowseeker.rag_chain import search_with_rerank


def _extract_json(text: str) -> str:
    """从 LLM 回复中提取 JSON 字符串，支持常见包装格式。

    处理情况：
    - ```json\n{...}\n```
    - ```\n{...}\n```
    - 前置/后置文字 + {...}
    - 纯 JSON 文本

    Raises:
        ValueError: 无法从文本中提取合法 JSON。
    """
    text = text.strip()

    # 1. 优先提取 ```json 或 ``` 代码块中的内容
    for pattern in [r'```json\s*([\s\S]*?)```', r'```\s*([\s\S]*?)```']:
        match = re.search(pattern, text)
        if match:
            candidate = match.group(1).strip()
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                continue

    # 2. 尝试直接解析全文本
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    # 3. 兜底：找到第一个 { 和最后一个 } 截取
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    raise ValueError(f"无法从 LLM 回复中提取 JSON:\n{text[:500]}")

# ── Agent 状态定义 ────────────────────────────────────────


class AgentState(TypedDict):
    """LangGraph 节点间流转的 Agent 状态。"""

    question: str  # 用户问题
    search_plan: dict  # 检索计划 {keywords, strategy, num_rounds}
    search_history: list  # 每轮检索记录 [{round, query, results_count, top_chunks}]
    need_more_search: bool  # 是否需要继续检索
    final_context: str  # 最终用于生成的上下文（多轮合并）
    answer: str  # 最终回答
    citations: list  # 引用来源 [{chunk_text, doc_name}]
    thinking_trace: list  # 推理过程（供前端可视化）
    llm_thinking: list  # 模型思考过程（供前端展示）
    _round: int  # 当前检索轮次（内部使用）


def init_state(question: str) -> AgentState:
    return {
        "question": question,
        "search_plan": {},
        "search_history": [],
        "need_more_search": False,
        "final_context": "",
        "answer": "",
        "citations": [],
        "thinking_trace": [],
        "llm_thinking": [],
        "_round": 0,
    }


SYSTEM_PROMPT = """你是一个智能知识检索助手。你的任务是分析用户问题并制定检索策略。

请分析用户问题并输出 JSON（不要包含 markdown 代码块标记）：

{{
  "keywords": ["关键词1", "关键词2", ...],
  "strategy": "single" | "multi",
  "num_rounds": 1 | 2 | 3,
  "reasoning": "简短的分析说明"
}}

规则：
- 简单事实性问题 → strategy="single", num_rounds=1
- 需要对比/多角度 → strategy="multi", num_rounds=2
- 复杂分析问题 → strategy="multi", num_rounds=3"""

EVALUATE_PROMPT = """你是一个检索结果评估专家。请判断当前的检索结果是否足够回答用户问题。

用户问题：{question}

本轮检索结果：
{results}

请输出 JSON（不要包含 markdown 代码块标记）：

{{
  "sufficient": true | false,
  "reasoning": "判断理由",
  "missing_info": "如果不够，缺少什么信息？"
}}

规则：
- 结果中包含直接回答问题的关键信息 → sufficient=true
- 结果部分相关但不够全面 → sufficient=false
- 结果完全不相关 → sufficient=false"""

REFORMULATE_PROMPT = """你是一个查询重构专家。上一轮检索结果不够充分，请从不同角度生成新的搜索关键词。

用户问题：{question}
上一轮关键词：{previous_keywords}
上一轮结果摘要：{results_summary}
当前轮次：{current_round}/{max_rounds}

请输出 JSON（不要包含 markdown 代码块标记）：

{{
  "keywords": ["新关键词1", "新关键词2", ...],
  "reasoning": "为什么这些新关键词能补充缺失信息"
}}

要求：新关键词必须与上一轮不同，覆盖缺失的信息角度。"""

GENERATE_PROMPT = """你是一个知识问答助手。请基于以下检索到的文档内容回答用户问题。

用户问题：{question}

检索到的相关文档片段：
{context}

要求：
1. 用中文清晰、准确、有条理地回答
2. 回答中引用具体的文档内容作为依据
3. 如果检索到的信息不足以回答问题，请如实告知
4. 在引用处标注 [来源：文档名称]
5. 如果多个文档有相关信息，进行综合对比

请直接输出回答内容（不需要 JSON）。"""


# ── LangGraph 节点 ───────────────────────────────────────


async def analyze_question(state: AgentState) -> AgentState:
    """分析问题，生成检索计划。"""
    state = dict(state)
    trace = state.get("thinking_trace", [])

    try:
        resp, thinking = await get_context().llm.chat_completion_thinking(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"用户问题：{state['question']}"},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        # 从 LLM 回复中提取 JSON（兼容代码块包装、前后缀文字等）
        cleaned = _extract_json(resp)
        plan = json.loads(cleaned)

        state["search_plan"] = plan
        trace.append({
            "step": "analyze",
            "content": f"📋 分析问题：{plan.get('reasoning', '')}",
            "detail": f"关键词：{', '.join(plan.get('keywords', []))}  策略：{plan.get('strategy', 'single')}  最大轮次：{plan.get('num_rounds', 1)}",
        })
        if thinking:
            state.setdefault("llm_thinking", []).append(f"[分析问题] {thinking}")
    except Exception as e:
        # LLM 失败时的兜底计划
        state["search_plan"] = {
            "keywords": [state["question"]],
            "strategy": "single",
            "num_rounds": 1,
            "reasoning": f"LLM 分析异常({e})，使用默认单轮检索",
        }
        trace.append({
            "step": "analyze",
            "content": f"⚠️ 分析异常，使用默认策略：单轮检索",
            "detail": "",
        })

    state["thinking_trace"] = trace
    return state


async def retrieve(state: AgentState) -> AgentState:
    """执行两阶段检索：向量粗召回 → Cross-Encoder 精排序。"""
    state = dict(state)
    trace = list(state.get("thinking_trace", []))
    history = list(state.get("search_history", []))
    plan = state.get("search_plan", {})
    current_round = state.get("_round", 0) + 1
    state["_round"] = current_round

    # 确定本轮关键词（首次使用原始 question，后续用 reformulate 生成的）
    keywords = plan.get("keywords", [state["question"]])

    query = " ".join(keywords) if isinstance(keywords, list) else keywords

    try:
        # 两阶段检索：粗召回 20 条 → 重排序取 5 条
        results, rerank_info = search_with_rerank(
            query=query, top_k=5, recall_k=20
        )

        if not results:
            trace.append({
                "step": "retrieve",
                "content": f"🔍 第 {current_round} 轮检索：没有找到相关结果",
                "detail": f"查询：「{query}」",
            })
        elif rerank_info.get("reranked", False):
            # 两阶段检索成功
            recall_count = rerank_info["recall_count"]
            best_rerank = rerank_info["score_changes"][0]["rerank_score"] if rerank_info.get("score_changes") else 0
            trace.append({
                "step": "retrieve",
                "content": f"🔍 第 {current_round} 轮检索：粗召回 {recall_count} 条 → 重排序取 {len(results)} 条",
                "detail": f"查询：「{query}」  Cross-Encoder 最佳得分：{best_rerank:.3f}",
            })
        else:
            # Reranker 降级，仅向量检索
            trace.append({
                "step": "retrieve",
                "content": f"🔍 第 {current_round} 轮检索：找到 {len(results)} 条结果（重排序降级，仅向量检索）",
                "detail": f"查询：「{query}」  最佳得分：{results[0].get('score', 0):.3f}",
            })
    except Exception as e:
        results = []
        rerank_info = {"reranked": False}
        trace.append({
            "step": "retrieve",
            "content": f"⚠️ 检索异常：{e}",
            "detail": "",
        })

    # 记录本轮检索
    round_record = {
        "round": current_round,
        "query": query,
        "results_count": len(results),
        "top_chunks": results[:3],  # 只保留前 3 条给 LLM
        "reranked": rerank_info.get("reranked", False),
        "recall_count": rerank_info.get("recall_count", 0),
    }
    history.append(round_record)
    state["search_history"] = history

    # 合并到 final_context
    existing = state.get("final_context", "") or ""
    new_contexts = []
    for r in results:
        content = r.get("content", "")
        doc_name = r.get("doc_id", "unknown")
        new_contexts.append(f"[来源：{doc_name}]\n{content}")
    if new_contexts:
        if existing:
            existing += "\n\n---\n\n"
        existing += "\n\n".join(new_contexts)
    state["final_context"] = existing

    state["thinking_trace"] = trace
    return state


async def evaluate_results(state: AgentState) -> AgentState:
    """评估检索结果是否足够，决定是否需要继续检索。"""
    state = dict(state)
    trace = list(state.get("thinking_trace", []))
    history = state.get("search_history", [])
    plan = state.get("search_plan", {})
    current_round = state.get("_round", 0)
    max_rounds = plan.get("num_rounds", 1)

    # 没有检索到结果 → 需要重试
    if not history or not history[-1].get("top_chunks"):
        state["need_more_search"] = current_round < max_rounds
        if state["need_more_search"]:
            trace.append({
                "step": "evaluate",
                "content": "📊 评估：本轮未找到结果，需要重新搜索",
                "detail": "",
            })
        else:
            trace.append({
                "step": "evaluate",
                "content": "📊 评估：已达最大检索轮次，进入生成阶段",
                "detail": "",
            })
        state["thinking_trace"] = trace
        return state

    # 已达最大轮次 → 不再检索
    if current_round >= max_rounds:
        state["need_more_search"] = False
        trace.append({
            "step": "evaluate",
            "content": f"📊 评估：已达最大检索轮次（{max_rounds}），进入生成阶段",
            "detail": "",
        })
        state["thinking_trace"] = trace
        return state

    # 让 LLM 评估结果质量
    results_text = ""
    for r in history[-1].get("top_chunks", []):
        results_text += f"- {r.get('content', '')[:200]}...\n"

    try:
        resp = await get_context().llm.chat_completion(
            messages=[
                {"role": "system", "content": EVALUATE_PROMPT.format(
                    question=state["question"],
                    results=results_text,
                )},
                {"role": "user", "content": "请评估这些检索结果是否足够回答用户问题。"},
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        cleaned = _extract_json(resp)
        evaluation = json.loads(cleaned)

        state["need_more_search"] = not evaluation.get("sufficient", True)

        if state["need_more_search"]:
            trace.append({
                "step": "evaluate",
                "content": f"📊 评估：结果不够充分，需继续检索 — {evaluation.get('reasoning', '')}",
                "detail": f"缺失信息：{evaluation.get('missing_info', '未说明')}",
            })
        else:
            trace.append({
                "step": "evaluate",
                "content": f"📊 评估：结果足够，进入生成阶段 — {evaluation.get('reasoning', '')}",
                "detail": "",
            })
    except Exception as e:
        # 评估失败时保守处理：继续搜索
        state["need_more_search"] = current_round < max_rounds
        trace.append({
            "step": "evaluate",
            "content": f"⚠️ 评估异常({e})，{'继续检索' if state['need_more_search'] else '进入生成阶段'}",
            "detail": "",
        })

    state["thinking_trace"] = trace
    return state


async def reformulate(state: AgentState) -> AgentState:
    """重新组织查询关键词。"""
    state = dict(state)
    trace = list(state.get("thinking_trace", []))
    history = state.get("search_history", [])
    plan = state.get("search_plan", {})
    current_round = state.get("_round", 0)
    max_rounds = plan.get("num_rounds", 1)

    previous_keywords = plan.get("keywords", [state["question"]])
    results_summary = ""
    if history and history[-1].get("top_chunks"):
        for r in history[-1]["top_chunks"][:2]:
            results_summary += f"- {r.get('content', '')[:150]}...\n"

    try:
        resp = await get_context().llm.chat_completion(
            messages=[
                {"role": "system", "content": REFORMULATE_PROMPT.format(
                    question=state["question"],
                    previous_keywords=", ".join(previous_keywords) if isinstance(previous_keywords, list) else previous_keywords,
                    results_summary=results_summary or "无结果",
                    current_round=current_round,
                    max_rounds=max_rounds,
                )},
                {"role": "user", "content": "请从不同角度生成新的搜索关键词。"},
            ],
            temperature=0.5,
            max_tokens=1024,
        )
        cleaned = _extract_json(resp)
        new_plan = json.loads(cleaned)

        # 更新 search_plan 中的关键词
        state["search_plan"] = dict(plan)
        state["search_plan"]["keywords"] = new_plan.get("keywords", previous_keywords)

        trace.append({
            "step": "reformulate",
            "content": f"🔄 重构检索：{new_plan.get('reasoning', '')}",
            "detail": f"新关键词：{', '.join(new_plan.get('keywords', []))}",
        })
    except Exception as e:
        # 重构失败时添加通用后缀
        old_kw = previous_keywords if isinstance(previous_keywords, list) else [previous_keywords]
        new_keywords = old_kw + ["详细说明", "具体信息"]
        state["search_plan"] = dict(plan)
        state["search_plan"]["keywords"] = new_keywords
        trace.append({
            "step": "reformulate",
            "content": f"⚠️ 重构异常({e})，扩展关键词",
            "detail": f"新关键词：{', '.join(new_keywords)}",
        })

    state["thinking_trace"] = trace
    return state


async def generate_answer(state: AgentState) -> AgentState:
    """综合上下文生成最终回答。"""
    state = dict(state)
    trace = list(state.get("thinking_trace", []))
    context = state.get("final_context", "")
    citations_list = []

    if not context.strip():
        state["answer"] = "未在已上传的文档中找到与您问题相关的信息。请尝试换个问法，或上传更多相关文档。"
        state["citations"] = []
        trace.append({
            "step": "generate",
            "content": "📝 生成回答：未找到相关信息",
            "detail": "知识库中没有匹配的文档内容。",
        })
        state["thinking_trace"] = trace
        return state

    thinking = ""
    try:
        resp, thinking = await get_context().llm.chat_completion_thinking(
            messages=[
                {"role": "system", "content": GENERATE_PROMPT.format(
                    question=state["question"],
                    context=context,
                )},
                {"role": "user", "content": "请基于以上检索结果回答用户问题。"},
            ],
            temperature=0.5,
            max_tokens=4096,
        )
        answer = resp.strip()
        state["answer"] = answer

        # 从 final_context 中提取引用来源
        seen_sources = set()
        for line in context.split("\n"):
            if line.startswith("[来源："):
                src = line.removeprefix("[来源：").removesuffix("]").strip()
                if src and src not in seen_sources:
                    seen_sources.add(src)
                    citations_list.append({"doc_name": src, "chunk_text": ""})

        trace.append({
            "step": "generate",
            "content": f"📝 生成回答完成（引用 {len(citations_list)} 个来源）",
            "detail": "",
        })
    except Exception as e:
        state["answer"] = f"生成回答时出现异常：{e}\n\n请稍后重试。"
        trace.append({
            "step": "generate",
            "content": f"⚠️ 生成异常：{e}",
            "detail": "",
        })

    if thinking:
        state.setdefault("llm_thinking", []).append(f"[生成回答] {thinking}")
    state["citations"] = citations_list
    state["thinking_trace"] = trace
    return state


def route_after_evaluate(state: AgentState) -> Literal["generate_answer", "reformulate"]:
    """条件边：评估结果后决定下一步。"""
    if state.get("need_more_search", False):
        return "reformulate"
    return "generate_answer"


# ── 编译图 ───────────────────────────────────────────────


def build_rag_graph() -> StateGraph:
    """构建并编译 Agentic RAG 状态图。"""
    builder = StateGraph(AgentState)

    builder.add_node("analyze_question", analyze_question)
    builder.add_node("retrieve", retrieve)
    builder.add_node("evaluate_results", evaluate_results)
    builder.add_node("reformulate", reformulate)
    builder.add_node("generate_answer", generate_answer)

    builder.add_edge(START, "analyze_question")
    builder.add_edge("analyze_question", "retrieve")
    builder.add_edge("retrieve", "evaluate_results")
    builder.add_conditional_edges(
        "evaluate_results",
        route_after_evaluate,
        {"generate_answer": "generate_answer", "reformulate": "reformulate"},
    )
    builder.add_edge("reformulate", "retrieve")
    builder.add_edge("generate_answer", END)

    return builder.compile()


# ── 对外入口 ─────────────────────────────────────────────


async def run_rag_query(question: str) -> AgentState:
    """运行一次完整的 RAG 问答流程。

    Args:
        question: 用户问题。

    Returns:
        最终 AgentState（含 answer、citations、thinking_trace）。
    """
    graph = build_rag_graph()
    state = init_state(question)
    result = await graph.ainvoke(state)
    return result
