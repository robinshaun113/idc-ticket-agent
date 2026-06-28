"""
02_routing_agent.py — 带条件分支的 Agent
LangGraph Quick Start 例二：根据 LLM 分类结果走不同路径

跑法：PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python examples/02_routing_agent.py

学到什么：
  1. 条件边（add_conditional_edges）的实际用法
  2. 分类节点 + 多路径模式（跟你的 P2 工单 Agent 结构一样）
  3. 路由函数：state 进 → 节点名字符串出
"""

import os
from dotenv import load_dotenv
load_dotenv(override=True)

from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

llm = ChatOpenAI(
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    model="qwen-max",
)


# ============================================================
# Step 1: 定义 State
# ============================================================
class TicketState(TypedDict):
    ticket_text: str    # 工单原文
    category: str       # 分类结果
    priority: str       # 优先级
    response: str       # 最终回复


# ============================================================
# Step 2: 三个 Node
# ============================================================
def classifier(state: TicketState) -> TicketState:
    """
    分类节点：只做一件事 — 判断工单类型和优先级。
    返回纯 JSON（不用工具）。
    """
    prompt = f"""
    你是一个 IDC 工单分类器。根据工单内容，输出 JSON：
    {{"category": "温控/电力/网络/硬件/安防", "priority": "P0/P1/P2/P3"}}

    优先级标准：
    - P0: 影响客户业务或有安全风险
    - P1: 基础设施告警，暂未影响业务
    - P2: 单一设备异常，有冗余
    - P3: 咨询类/计划内维护

    工单内容：{state["ticket_text"]}
    """
    response = llm.invoke([HumanMessage(content=prompt)])
    import json, re
    raw = response.content.strip()
    # 防御性解析：LLM 可能返回 ```json ... ``` 包裹的内容
    if "```" in raw:
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
        if match:
            raw = match.group(1).strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # 如果仍解析失败，打出来看看（不要默默吞掉异常）
        print(f"⚠️  LLM 返回了非 JSON 内容: {raw[:200]}")
        raise
    return {"category": result["category"], "priority": result["priority"]}


def escalator(state: TicketState) -> TicketState:
    """P0 升级节点：生成紧急升级通知"""
    return {
        "response": (
            f"🚨 P0 紧急升级！\n"
            f"类型：{state['category']}\n"
            f"工单：{state['ticket_text']}\n"
            f"⚠️ 请立即通知值班主管 + 对应团队负责人。"
        )
    }


def handler(state: TicketState) -> TicketState:
    """普通工单处理节点：生成引导式回复"""
    prompt = f"""
    工单类型「{state['category']}」，优先级「{state['priority']}」。
    工单内容：{state['ticket_text']}

    请给出一句话处理建议（只写建议，不要其他内容）。
    """
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"response": response.content}


# ============================================================
# Step 3: 路由函数（条件边的"大脑"）
# ============================================================
def route_by_priority(state: TicketState) -> str:
    """
    这是你最需要理解的函数：
    - 收到当前 state
    - 读 state["priority"]
    - 返回下一个要执行的节点名（字符串！）
    """
    if state["priority"] == "P0":
        return "escalator"   # → 走升级通道
    else:
        return "handler"     # → 走普通处理


# ============================================================
# Step 4: 建图
# ============================================================
graph = StateGraph(TicketState)

graph.add_node("classifier", classifier)
graph.add_node("escalator", escalator)
graph.add_node("handler", handler)

graph.set_entry_point("classifier")
graph.add_conditional_edges(
    "classifier",          # 从 classifier 节点出发
    route_by_priority,     # 用这个函数决定下一站
    {                      # 路由函数可能返回的每个值 → 对应哪个节点
        "escalator": "escalator",
        "handler": "handler",
    }
)
graph.add_edge("escalator", END)
graph.add_edge("handler", END)

app = graph.compile()


# ============================================================
# Step 5: 测试两条不同路径
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("例二：条件分支 Agent（分类 → 路由 → 分别处理）")
    print("=" * 60)

    # 测试 1: P0 工单 → 应走 escalator
    p0_ticket = "客户核心业务服务器宕机，所有虚拟机不可达"
    result = app.invoke({"ticket_text": p0_ticket})
    print(f"\n📋 工单: {p0_ticket}")
    print(f"🏷️  分类: {result['category']} | 优先级: {result['priority']}")
    print(f"📝 回复: {result['response']}")

    # 测试 2: P2 工单 → 应走 handler
    p2_ticket = "巡检发现备用风扇转速偏低，主风扇运行正常"
    result = app.invoke({"ticket_text": p2_ticket})
    print(f"\n📋 工单: {p2_ticket}")
    print(f"🏷️  分类: {result['category']} | 优先级: {result['priority']}")
    print(f"📝 回复: {result['response']}")

    print("\n✅ 看到了吗？同样的图，不同的工单走了不同的路径。这就是 StateGraph 的核心能力。")
