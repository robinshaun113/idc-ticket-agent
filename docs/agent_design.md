# Agent 架构设计

## Agent 清单

| Agent | 角色 | 输入 | 输出 | 工具 |
|-------|------|------|------|------|
| **Classifier** | 分类器 | 工单原文 | `{category, priority, confidence}` | 无（纯 LLM 推理） |
| **Diagnoser** | 诊断器 | 工单 + 分类结果 | `{diagnosis, tools_used}` | `get_monitoring`, `get_cmdb`, `get_history_tickets` |
| **KB-Searcher** | 知识检索 | 诊断结论 | `{sop_snippets, sources}` | `search_idc_kb`（调 P1 RAG） |
| **Escalator** | 升级处理 | P0 工单全量信息 | `{escalation_summary, notify_target}` | 无 |
| **Reviewer** | 审核回环 | 诊断结果 + 置信度 | `{approved: bool, retry_instruction}` | 无（Day 29 加入） |

## 分类体系

| 类别 | 示例关键词 | 典型工单 |
|------|-----------|---------|
| 温控 | 温度、空调、冷通道、热通道、湿度 | "机柜 A12 温度 32°C 持续 10 分钟" |
| 电力 | 断电、电压、UPS、配电柜、PDU | "B 区 UPS 告警，电池余量 15%" |
| 网络 | 丢包、延迟、交换机、光模块 | "客户反馈机柜 C03 到阿里云丢包率 5%" |
| 硬件 | 服务器、硬盘、内存、风扇 | "服务器 SRV-1024 硬盘指示灯橙色闪烁" |
| 安防 | 门禁、监控、烟雾、漏水 | "机房东侧漏水传感器告警" |

## 优先级定义

| 优先级 | 标准 | 响应目标 | 路由 |
|--------|------|---------|------|
| P0 | 影响客户业务 / 有安全风险 | 立即升级，5 分钟内响应 | → Escalator |
| P1 | 基础设施告警，暂未影响业务 | 30 分钟内处理 | → Diagnoser |
| P2 | 单一设备异常，有冗余 | 4 小时内处理 | → Diagnoser |
| P3 | 咨询类/计划内维护 | 下一个工作日 | → KB-Searcher 直接回答 |

## StateGraph 流程

```
                    ┌──────────┐
                    │  Triage  │  ← 工单入口
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │Classifier│  ← LLM 输出 category/priority/confidence
                    └────┬─────┘
                         │
              ┌──────────┼──────────┐
              │ P0       │ P1-P3    │ confidence<0.6
              │          │          │  (Day29)
         ┌────▼───┐ ┌───▼────┐ ┌───▼─────┐
         │Escalate│ │Diagnoser│ │Reviewer │
         └────┬───┘ └───┬────┘ └───┬─────┘
              │         │          │ retry
              │    ┌────▼────┐     │
              │    │KB-Search│◄────┘
              │    └────┬────┘
              │         │
              └────┬────┘
                   │
              ┌────▼─────┐
              │  Output   │  ← 生成最终处理方案
              └──────────┘
```

## 状态定义

```python
class TicketState(TypedDict):
    # 输入
    ticket_text: str          # 工单原文
    ticket_id: str            # 工单编号

    # Classifier 输出
    category: str             # 硬件/网络/电力/温控/安防
    priority: str             # P0/P1/P2/P3
    confidence: float         # 0.0-1.0

    # Diagnoser 输出
    tool_calls: list          # 调用了哪些工具
    diagnosis: str            # 诊断结论

    # KB-Searcher 输出
    sop_results: list         # 检索到的 SOP 片段
    sources: list             # 来源文件

    # Reviewer 输出（Day29）
    review_approved: bool
    retry_count: int

    # 最终输出
    final_response: str       # 输出给运维人员的完整方案
```

## 工具定义

| 工具名 | 描述 | 当前阶段 | Mock 返回 |
|--------|------|---------|----------|
| `get_monitoring(asset_id)` | 查询资产实时监控数据 | Day 26 | 假数据（温度/电力/网络指标） |
| `get_cmdb(asset_id)` | 查询资产配置信息 | Day 26 | 假数据（设备型号/位置/维保商） |
| `get_history_tickets(keyword)` | 搜索历史同类工单 | Day 26 | 假数据（5 条历史记录） |
| `search_idc_kb(query)` | 检索 P1 知识库 SOP | Day 25 | 直接调 P1 RAG 或假数据 |
