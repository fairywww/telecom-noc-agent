# 流式输出：从 LLM 到浏览器的完整链路

**范围说明**：本文基于 v0.8 的改动：`noc_agent/agent/loop.py` 重构为流式生成器、`noc_agent/server/adapter.py` 的 `/api/agent/stream` SSE 接口、`web/index.html` 的流式渲染。前置阅读：[llm-basics.md](llm-basics.md) 第 4 节。

## 1. 为什么要流式

Agent 一次诊断耗时数十秒。非流式下用户面对空白等待全部完成；流式下每个事件即时可见：工具调用逐条出现、答案逐字打出。总耗时不变，**首次反馈时间**从几十秒降到一两秒——流式优化的是体感，不是速度。

## 2. 链路总览：三段流的接力

```
LLM 流式应答          Python 生成器            SSE                浏览器
chunk/delta   ──▶   run_agent_stream() 产出事件  ──▶  data: {...}\n\n ──▶ ReadableStream 解析渲染
（上游）             （加工与转发）             （传输协议）          （消费）
```

三段用的是同一种思想——**边产生边传递**，只是载体不同：SDK 的迭代器、Python 生成器（`yield`）、HTTP 长连接。

## 3. 核心重构：单一生成器架构

`run_agent_stream()` 是一个生成器：执行循环的同时 `yield` 事件字典（`文字` / `工具` / `完成` / `错误`）。三个消费方共用它：

| 消费方 | 用法 |
|--------|------|
| 命令行 / 评测 | `run_agent()` 封装：攒齐事件后返回完整结果 |
| SSE 接口 | 每个事件包成一条 `data:` 消息即时下发 |

**一份循环逻辑，多种消费方式**——此前非流式与流式各写一份循环的话，任何修改都要同步两处，必然漂移。

## 4. 技术要点

### 4.1 流式模式下的 tool_calls 组装

流式应答中，工具调用请求也是碎片化到达的：函数名一片、参数 JSON 被切成多片，各碎片带 `index` 标识归属。必须按 `index` 分组、逐片拼接 `arguments`，流结束后才能得到完整调用请求（`noc_agent/agent/loop.py` 的 `组装中` 字典）。这是流式 Agent 与非流式的最大实现差异。

### 4.2 流式下的用量统计

流式默认不返回 token 用量；需在请求中加 `stream_options={"include_usage": True}`，服务端会在流末尾追加一个含 `usage` 的块（已实测 ModelScope 支持）。评测的词元指标因此得以保留。

### 4.3 SSE 协议与 FastAPI 实现

SSE（Server-Sent Events）约定：应答头 `Content-Type: text/event-stream`，每条消息为 `data: <内容>\n\n`（空行分隔）。FastAPI 用 `StreamingResponse` 包一个生成器即可，无需额外依赖。

与 WebSocket 的取舍：SSE 是单向下行、纯 HTTP，实现与穿透都简单；本场景（服务端推、客户端只在开头发一次问题）单向足够，无需 WebSocket 的双向能力。

### 4.4 浏览器端：fetch + ReadableStream

标准 `EventSource` 只支持 GET，而本接口需要 POST 请求体，故改用 fetch 流式读取：`应答.body.getReader()` 逐块读、`TextDecoder` 解码、按 `\n\n` 切分消息、`JSON.parse` 后按事件类型渲染。注意跨块边界：一条 SSE 消息可能被网络分块截断，必须用缓冲区攒够完整消息再解析。

## 5. 验证

```bash
# 命令行直接观察 SSE 事件流
curl -N -X POST http://localhost:8002/api/agent/stream \
  -H "Content-Type: application/json" -d '{"question":"现在全网退服多少个？"}'
```

预期：先出现 `{"事件":"工具",...}`，随后一连串 `{"事件":"文字","文本":"..."}` 小片段。浏览器端：提问后工具轨迹逐条实时出现，答案逐字增长（本次实测中途快照：4 条轨迹已显示、答案 103 字且持续增长、按钮仍为"诊断中"）。

---

## 自测

1. 三段流（LLM→生成器→SSE→浏览器）中任何一段改成"攒齐再发"，用户体验会退化成什么样？哪一段最容易被无意写成攒齐再发？
2. 流式模式下为什么不能在收到第一个 tool_calls 碎片时就execute_tool？
3. 前端为什么需要缓冲区？如果直接对每个网络分块做 `JSON.parse` 会发生什么？

建议实际修改验证，验证后 `git checkout -- <文件名>` 恢复。
