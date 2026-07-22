# MCP：工具接入的标准化协议

**范围说明**：本文基于 `tools.py`（工具层独立）、`mcp_server.py`（手写最小 Server）、`mcp_client_demo.py`（协议演示）与 `tests/test_mcp.py`。前置阅读：[../04-agent/agent-loop.md](../04-agent/agent-loop.md) 第 5 节。

## 1. MCP 解决什么问题

没有标准时，M 个 Agent 应用接 N 个工具源，需要 M×N 份定制接入代码。MCP（Model Context Protocol，Anthropic 2024 年开源）把「工具如何被发现、如何被调用」定成协议后，工具方写一个 Server、应用方写一个 Client，M+N 份代码解决 M×N 问题——与 USB、HTTP 的标准化逻辑相同。

对本项目的直接意义：`mcp_server.py` 暴露的 NOC 工具，不加一行定制代码即可被 Claude Code、Cursor 等任何 MCP 客户端发现和调用，而不只服务于我们自己的 Agent。

## 2. 与手写 tool calling 的关系：同一份契约，两种消费方式

对比 `tools.py` 中的工具定义与两种暴露格式：

| 内容 | OpenAI tools 格式（agent.py 用） | MCP tools/list（mcp_server.py 用） |
|------|--------------------------------|-----------------------------------|
| 工具名 | `function.name` | `name` |
| 说明 | `function.description` | `description` |
| 参数 | `function.parameters`（JSON Schema） | `inputSchema`（JSON Schema） |

**三要素完全一致，只是字段名和信封不同。**MCP 并没有发明新概念，它把 [agent-loop.md](../04-agent/agent-loop.md) 里"LLM 只看得见说明书"的那份说明书，从各家私有格式升格为公共协议。理解了手写 tool calling，MCP 只是换个信封。

本次配套重构：工具定义从 `agent.py` 移入独立的 `tools.py`——一份工具表，两个消费方（Agent 循环、MCP Server）。工具与消费方之间的这条边界，正是 MCP 标准化的对象。

## 3. 协议本体：JSON-RPC 2.0 的三个方法

MCP 消息体是 JSON-RPC 2.0（`jsonrpc/id/method/params` 请求，`result` 或 `error` 应答）。核心只有三步：

| 步骤 | 方法 | 作用 |
|------|------|------|
| ① 握手 | `initialize` | 交换协议版本、能力声明、双方身份 |
| ② 发现 | `tools/list` | Server 返回全部工具的 name/description/inputSchema |
| ③ 调用 | `tools/call` | 按名调用，应答为 `content` 数组（本项目返回 text 类型） |

细节：`notifications/initialized` 是通知（无 `id`），不需要应答；未实现的方法应答标准错误码 `-32601`；工具执行失败不走协议错误，而是 `isError: true` 的正常应答——与我们"错误是数据"的原则一致（见 [../04-agent/tool-parameters.md](../04-agent/tool-parameters.md) 第 2 节）。

## 4. 传输方式：stdio

本实现用 stdio 传输：客户端把 Server 作为**子进程**拉起，每行一个 JSON 消息，stdin 进、stdout 出。这是本地 MCP Server 的标准形态（远程场景用 Streamable HTTP，本项目未实现）。`mcp_client_demo.py` 展示了完整生命周期：拉起子进程 → 握手 → 发现 → 调用 → 终止。

## 5. 手写与官方 SDK

生产中用官方 Python SDK（`pip install mcp`，FastMCP 装饰器风格）几行即可建 Server；本项目手写有两个原因：官方 SDK 要求 Python ≥ 3.10（本机 3.9），以及——协议只有三个方法，手写不到百行，正好把"MCP 到底是什么"看得一清二楚。日后升级 Python 后，可用 SDK 重写并对比。

接入真实客户端的配置形如（以支持 MCP 的应用为例）：

```json
{ "mcpServers": { "telecom-noc": {
    "command": "python3",
    "args": ["/path/to/telecom-noc-agent/mcp_server.py"] } } }
```

## 6. 本项目未实现的协议能力

- `resources`（可读资源，如把知识库文档直接暴露为资源）与 `prompts`（提示词模板）两类原语；
- Streamable HTTP 传输与鉴权；
- 能力协商的细粒度声明。

## 7. 验证

```bash
python3 mcp_client_demo.py        # 协议全流程（真实调用需 8001/8002 在运行）
python3 -m pytest tests/test_mcp.py -v   # 握手/发现/未知方法，零网络依赖
```

---

## 自测

1. MCP 的 `inputSchema` 与 OpenAI tools 的 `parameters` 是什么关系？为什么两者都用 JSON Schema？
2. 工具执行失败时，为什么用 `isError: true` 的正常应答而不是 JSON-RPC 的 `error`？（提示：谁需要看到这个错误——协议层还是模型？）
3. 给 `mcp_server.py` 增加一个新工具需要改几个文件？这说明工具层独立的价值是什么？

建议实际修改验证，验证后 `git checkout -- <文件名>` 恢复。
