"""Bounded LangGraph tool loop for evidence-grounded QA."""

import json
import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from .knowledge import KnowledgeBase
from .hybrid_knowledge import HybridKnowledgeBase
from .validation import incomplete, validate_answer


TOOLS = [
    {"name": "search_documents", "description": "Search synthetic policy/product documents; returns candidates, not quotable source text.",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "read_snippet", "description": "Read the exact source text and metadata for a document snippet before citing it.",
     "parameters": {"type": "object", "properties": {"doc_id": {"type": "string"}, "snippet_id": {"type": "string"}},
                    "required": ["doc_id", "snippet_id"]}},
]

SYSTEM = """You are an enterprise QA agent. Use search_documents and read_snippet to verify facts.
Search again if no relevant result. Read every relevant candidate when sources may conflict.
Never choose between contradictory policies without a stated scope or priority. Never invent source text.
History helps understand the user's follow-up but is not evidence. Tool errors are not empty results.
When finished, output ONLY one JSON object with keys status, answer, citations, gaps,
clarifying_question, error. status is answered, needs_clarification, or incomplete.
Each citation has doc_id, snippet_id, quote; quote must be an exact continuous substring of a snippet you read.
For conflicting sources, cite both, explain the conflict and ask which policy applies.
For no source, use needs_clarification, state the gap and ask for relevant documentation.
Use incomplete only for an execution failure or an unresolved technical limit.
Do not expose internal reasoning."""


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    trace: list[dict]
    candidates: list[dict]
    evidence: dict
    tool_count: int
    failed_once: bool
    done: bool
    final: dict


def _result_summary(name: str, result: dict) -> dict:
    if not result.get("ok"):
        return {"ok": False, "error": result.get("error", "unknown_tool_error")}
    if name == "search_documents":
        return {"ok": True, "hit_count": len(result["hits"]),
                "ids": [f"{hit['doc_id']}/{hit['snippet_id']}" for hit in result["hits"]]}
    return {"ok": True, "doc_id": result["doc_id"], "snippet_id": result["snippet_id"],
            "characters": len(result["text"])}


def _mock_reply(state: AgentState, question: str, history: list) -> AIMessage:
    if not state["trace"]:
        query = question
        if not any(term in question for term in ("报销", "费用", "发票", "远程", "在家办公", "居家办公", "字幕", "导出")):
            query = " ".join([question] + [str(item.get("content", "")) for item in history if isinstance(item, dict)])
        return AIMessage(content="", tool_calls=[{"name": "search_documents", "args": {"query": query}, "id": "mock-search"}])
    last = state["trace"][-1]
    if last.get("result", {}).get("error"):
        return AIMessage(content=json.dumps(incomplete("tool_failed"), ensure_ascii=False))
    if not state["candidates"]:
        out = {"status": "needs_clarification", "answer": "现有资料没有相关规定。", "citations": [],
               "gaps": ["缺少相关制度或产品资料"], "clarifying_question": "请提供适用资料。", "error": None}
        return AIMessage(content=json.dumps(out, ensure_ascii=False))
    unread = [c for c in state["candidates"] if (c["doc_id"], c["snippet_id"]) not in state["evidence"]]
    if unread:
        hit = unread[0]
        return AIMessage(content="", tool_calls=[{"name": "read_snippet", "args":
            {"doc_id": hit["doc_id"], "snippet_id": hit["snippet_id"]}, "id": f"mock-read-{hit['doc_id']}"}])
    sources = list(state["evidence"].values())
    citations = [{"doc_id": x["doc_id"], "snippet_id": x["snippet_id"], "quote": x["text"]} for x in sources]
    conflict = len({x["text"] for x in sources}) > 1
    out = {"status": "needs_clarification" if conflict else "answered",
           "answer": "资料存在冲突，请确认适用制度。" if conflict else sources[0]["text"],
           "citations": citations, "gaps": ["资料冲突"] if conflict else [],
           "clarifying_question": "请确认适用哪份制度？" if conflict else None, "error": None}
    return AIMessage(content=json.dumps(out, ensure_ascii=False))


def run_agent(request: dict, mode: str = "mock", max_steps: int = 8,
              fail_tool: str | None = None, corpus_path: str | None = None,
              index_dir: str | None = None) -> dict:
    question = request.get("question") if isinstance(request, dict) else None
    if not isinstance(question, str) or not question.strip():
        return {**incomplete("question_required"), "trace": []}
    if max_steps < 1:
        return {**incomplete("step_limit"), "trace": []}
    if mode not in {"mock", "online"}:
        return {**incomplete("invalid_mode"), "trace": []}
    if corpus_path and index_dir:
        return {**incomplete("choose_corpus_or_index"), "trace": []}
    history = request.get("history", [])
    if not isinstance(history, list):
        return {**incomplete("history_must_be_list"), "trace": []}
    if mode == "online":
        load_dotenv()
        key = os.getenv("DEEPSEEK_API_KEY")
        if not key:
            return {**incomplete("DEEPSEEK_API_KEY_missing"), "trace": []}
    try:
        kb = HybridKnowledgeBase(index_dir) if index_dir else (
            KnowledgeBase(corpus_path) if corpus_path else KnowledgeBase())
    except (ValueError, OSError) as exc:
        return {**incomplete(f"knowledge_error:{exc}"), "trace": []}
    model = None
    if mode == "online":
        model = ChatOpenAI(model=os.getenv("DEEPSEEK_MODEL", "deepseek-flash"),
                           base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                           api_key=key, extra_body={"thinking": {"type": "disabled"}}).bind_tools(TOOLS)

    user_text = json.dumps({"question": question, "history": history}, ensure_ascii=False)

    def call_model(state: AgentState) -> dict:
        try:
            reply = _mock_reply(state, question, history) if mode == "mock" else model.invoke(state["messages"])
        except Exception as exc:
            return {"done": True, "final": incomplete(f"model_error:{type(exc).__name__}"),
                    "trace": state["trace"] + [{"step": state["tool_count"] + 1, "action": "model_error", "error": type(exc).__name__}]}
        action = ([{"tool": c["name"], "parameters": c["args"]} for c in reply.tool_calls]
                  if reply.tool_calls else "finish")
        last_action = max((i for i, item in enumerate(state["trace"]) if "action" in item), default=-1)
        prior_tools = [item for item in state["trace"][last_action + 1:] if "result" in item]
        observations = [item["result"] for item in prior_tools]
        basis_parts = []
        for item in prior_tools:
            result = item["result"]
            if not result["ok"]:
                basis_parts.append(f"{item['tool']} 失败：{result['error']}")
            elif item["tool"] == "search_documents":
                basis_parts.append(f"检索命中 {result['hit_count']} 条")
            else:
                basis_parts.append(f"已读取 {result['doc_id']}/{result['snippet_id']}")
        basis = "；".join(basis_parts) if basis_parts else "用户提出问题，尚无工具观察"
        event = {"step": state["tool_count"] + 1, "action": action,
                 "previous_observations": observations, "decision_basis": basis}
        if reply.tool_calls:
            return {"messages": [reply], "trace": state["trace"] + [event]}
        try:
            payload = json.loads(reply.content)
        except (ValueError, TypeError):
            payload = incomplete("invalid_model_json")
        return {"messages": [reply], "trace": state["trace"] + [event], "done": True,
                "final": validate_answer(payload, state["evidence"], state["candidates"])}

    def call_tools(state: AgentState) -> dict:
        reply = state["messages"][-1]
        trace = list(state["trace"])
        evidence = dict(state["evidence"])
        candidates = list(state["candidates"])
        tool_messages = []
        count = state["tool_count"]
        failed_once = state["failed_once"]
        for call in reply.tool_calls:
            if count >= max_steps:
                return {"done": True, "final": incomplete("step_limit"), "trace": trace,
                        "tool_count": count}
            name, args = call["name"], call["args"]
            if not isinstance(args, dict):
                result = {"ok": False, "error": "invalid_tool_arguments"}
            elif fail_tool == name and not failed_once:
                result = {"ok": False, "error": "injected_failure"}
                failed_once = True
            elif name == "search_documents" and isinstance(args.get("query"), str):
                hits = kb.search_documents(args["query"])
                result = {"ok": True, "hits": hits}
                seen = {(c["doc_id"], c["snippet_id"]) for c in candidates}
                candidates.extend(h for h in hits if (h["doc_id"], h["snippet_id"]) not in seen)
            elif name == "read_snippet" and isinstance(args.get("doc_id"), str) and isinstance(args.get("snippet_id"), str):
                result = kb.read_snippet(args["doc_id"], args["snippet_id"])
                if result["ok"]:
                    evidence[(result["doc_id"], result["snippet_id"])] = result
            else:
                result = {"ok": False, "error": "invalid_tool_call"}
            count += 1
            trace.append({"step": count, "tool": name, "parameters": args,
                          "result": _result_summary(name, result)})
            tool_messages.append(ToolMessage(content=json.dumps(result, ensure_ascii=False), tool_call_id=call["id"]))
        return {"messages": tool_messages, "trace": trace, "evidence": evidence,
                "candidates": candidates, "tool_count": count, "failed_once": failed_once}

    graph = StateGraph(AgentState)
    graph.add_node("model", call_model)
    graph.add_node("tools", call_tools)
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", lambda s: END if s["done"] else "tools")
    graph.add_conditional_edges("tools", lambda s: END if s["done"] else "model")
    app = graph.compile()
    initial: AgentState = {"messages": [SystemMessage(content=SYSTEM), HumanMessage(content=user_text)],
                           "trace": [], "candidates": [], "evidence": {}, "tool_count": 0,
                           "failed_once": False, "done": False, "final": {}}
    try:
        state = app.invoke(initial, config={"recursion_limit": max_steps * 3 + 5})
    except Exception as exc:
        if hasattr(kb, "close"):
            kb.close()
        return {**incomplete(f"graph_error:{type(exc).__name__}"), "trace": []}
    if hasattr(kb, "close"):
        kb.close()
    return {**state["final"], "trace": state["trace"], "mode": mode,
            "model": os.getenv("DEEPSEEK_MODEL", "deepseek-flash") if mode == "online" else "mock"}
