"""
01_simple_agent.py — 最简 StateGraph：三个核心概念一次搞懂
LangGraph Quick Start 例一

跑法：PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python examples/01_simple_agent.py

学到什么：
  1. State  = 共享笔记本，每个 Node 都能读、都能写
  2. Node   = 图中的执行单元（一个 Python 函数）
  3. Edge   = 确定"A 之后一定走 B"，不分支
  4. compile() + invoke() = 编译图 → 灌入初始状态 → 拿到最终状态
"""

import os
from dotenv import load_dotenv
load_dotenv(override=True)

from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

llm = ChatOpenAI(
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    model="qwen-max",
)


# ============================================================
# Step 1: 定义 State — 这是所有节点共享的"笔记本"
# ============================================================
class WorkState(TypedDict):
    topic: str       # 输入：话题
    draft: str       # 节点1产出：草稿
    final: str       # 节点2产出：终稿


# ============================================================
# Step 2: 定义两个 Node — 图中的两个"执行单元"
# ============================================================
def writer(state: WorkState) -> dict:
    """
    节点1：写一段草稿。
    拿到 state，读 state["topic"]，写出 draft，返回更新。
    注意返回值是 dict，不是完整 state——LangGraph 自动合并。
    """
    prompt = f'请用两句话介绍"{state["topic"]}"，语言简洁。'
    response = llm.invoke([HumanMessage(content=prompt)])
    print(f"  ✍️  [writer] 草稿完成: {response.content[:80]}...")
    return {"draft": response.content}


def reviewer(state: WorkState) -> dict:
    """
    节点2：审查草稿并优化。
    拿到 state，读 state["draft"]，写出 final。
    """
    prompt = f'原文：{state["draft"]}\n\n请优化这段文字，让它更有吸引力、更专业。只输出优化后的版本。'
    response = llm.invoke([HumanMessage(content=prompt)])
    print(f"  🔍 [reviewer] 终稿完成: {response.content[:80]}...")
    return {"final": response.content}


# ============================================================
# Step 3: 建图 — 加节点 + 加边 + 编译
# ============================================================
graph = StateGraph(WorkState)

graph.add_node("writer", writer)       # 注册节点
graph.add_node("reviewer", reviewer)

graph.set_entry_point("writer")        # 入口：从 writer 开始
graph.add_edge("writer", "reviewer")   # 直线：writer → reviewer
graph.add_edge("reviewer", END)        # 结束：reviewer 之后结束

app = graph.compile()


# ============================================================
# Step 4: 运行
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("例一：最简 StateGraph（写稿 → 审稿 → 输出）")
    print("=" * 60)
    print()

    result = app.invoke({"topic": "AI 解决方案工程师"})

    print(f"\n📝 初始话题: {result['topic']}")
    print(f"📝 草稿: {result['draft']}")
    print(f"📝 终稿: {result['final']}")

    print("\n" + "=" * 60)
    print("三个核心概念总结：")
    print("  1. State  = 整个图共享的字典，每个节点返回的部分会自动合并")
    print("  2. Node   = 一个函数，入参 state，返回 dict（部分更新）")
    print("  3. Edge   = A → B 直线连接，不分支")
    print("=" * 60)
    print("\n✅ 跑通了！去看看 02_routing_agent.py 学条件分支。")
