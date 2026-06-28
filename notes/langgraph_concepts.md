# LangGraph 核心概念 · 白话笔记

> Day 23 · 2026/6/28

## 1. State（状态）

State 是整个图共用的字典。每个 Node 都能读、都能写。
Node 返回的 dict 自动和原 state 合并——只写改了的字段就行，不用返回整份 state。

## 2. Node（节点）

Node 是图里的执行单元，本质就是一个 Python 函数。
- 入参：当前 state（字典）
- 返回：dict（部分状态更新，自动合并进 state）

⚠️ Node 不负责"指路"——它只管干活、写状态。

## 3. Conditional Edge（条件边）

和普通 Edge（A→B 固定路线）不同，Conditional Edge 多一个路由函数：
- 路由函数接收当前 state
- 返回**节点名字符串**（如 "escalator" 或 "handler"）
- LangGraph 根据这个字符串决定下一站去哪

⚠️ 路由函数 ≠ Node。Node 改状态，路由函数只负责认路。

## 4. StateGraph vs Chain

- Chain：一条直线，步骤顺序写死的
- StateGraph：一张图，流程根据状态动态分支
