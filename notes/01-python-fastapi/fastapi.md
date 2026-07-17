# FastAPI 基础

**范围说明**：本文只涵盖本仓库 v0.1 代码（`noc_backend.py`、`adapter.py`）实际使用到的 FastAPI 特性。每节先给出定义，再对照仓库中的代码进行说明。未使用的特性统一列于第 7 节，待项目用到时补充。

## 1. 概述

FastAPI 是基于 Python 类型注解的 Web 框架，核心职责有三项：

1. **路由分发**：将 URL 路径映射到处理函数；
2. **请求解析与校验**：从请求中提取参数并验证格式；
3. **响应序列化**：将函数返回值转换为 HTTP 响应。

本项目的两个后端服务均由 FastAPI 实现：

| 文件 | 职责 | 端口 |
|------|------|------|
| `noc_backend.py` | 模拟 NOC 系统，提供原始数据接口 | 8001 |
| `adapter.py` | 适配层：聚合数据、托管前端页面 | 8002 |

## 2. 应用对象与路由注册

### 2.1 创建应用对象

```python
from fastapi import FastAPI
app = FastAPI()
```

`FastAPI()` 实例是服务的核心对象，后续所有路由均注册在该对象上。

### 2.2 使用装饰器注册路由

`noc_backend.py` 第 25–28 行：

```python
@app.get("/api/statistics/all")
def statistics_all():
    return {"code": 0, "message": "success", "data": 数据库里的行}
```

`@app.get(path)` 是装饰器，作用是将「HTTP GET 方法 + 指定路径」的请求绑定到其下方的函数。除 `get` 外，还有 `post`、`put`、`delete` 等方法，分别对应同名的 HTTP 方法。一个应用对象上可注册任意数量的路由。

### 2.3 响应的自动序列化

路由函数可以直接返回 `dict`。FastAPI 会自动完成两件事：

1. 将 `dict` 序列化为 JSON 字符串（无需手动调用 `json.dumps`）；
2. 设置响应头 `Content-Type: application/json`。

## 3. 运行方式：uvicorn 与 ASGI

FastAPI 本身不包含网络服务器，只定义请求的处理逻辑。监听端口、接收连接、并发调度由 ASGI 服务器完成；本项目使用 uvicorn。

启动命令及其构成：

```bash
python3 -m uvicorn noc_backend:app --port 8001
```

| 片段 | 含义 |
|------|------|
| `python3 -m uvicorn` | 以模块方式运行 uvicorn |
| `noc_backend` | 模块名，即文件 `noc_backend.py` |
| `app` | 该模块中 FastAPI 实例的变量名 |
| `--port 8001` | 监听端口 |

两者的分工：**uvicorn 负责网络层**（监听端口、接收请求、并发调度），**FastAPI 负责应用层**（路由分发、参数校验、响应序列化）。

## 4. 同一程序中的服务端与客户端角色

`adapter.py` 在通信中同时处于两种角色：

- **服务端**：通过 `@app.get("/api/kpi")` 接收来自浏览器的请求（`adapter.py` 第 24 行）；
- **客户端**：通过 `requests.get()` 向 NOC 后端发起请求（`adapter.py` 第 27 行）。

`requests` 是 HTTP 客户端库，用于主动发起请求；FastAPI 是服务端框架，用于接收并处理请求。二者方向相反，在同一程序中并存互不冲突。

## 5. 静态文件托管与路由匹配顺序

`adapter.py` 第 42 行：

```python
app.mount("/", StaticFiles(directory=str(Path(__file__).parent), html=True))
```

作用：将指定目录挂载到根路径 `/`，使其中的文件可通过 HTTP 直接访问。参数 `html=True` 表示访问目录路径时返回该目录下的 `index.html`。

**注意事项**：FastAPI 按注册顺序匹配请求路径。`mount("/")` 会匹配所有未被更早规则处理的路径，因此该语句必须置于全部 API 路由注册**之后**。若将其置于 `@app.get("/api/kpi")` 之前，对 `/api/kpi` 的请求将被静态文件处理器先行拦截，因目录中不存在名为 `api/kpi` 的文件而返回 404。

## 6. 自动接口文档

FastAPI 根据已注册的路由自动生成 OpenAPI 规范，并内置两个文档页面，服务运行期间可直接访问：

| 地址 | 说明 |
|------|------|
| `http://localhost:8001/docs` | Swagger UI，支持在页面内直接调用接口 |
| `http://localhost:8001/redoc` | ReDoc，适合阅读 |

接口文档与代码同源：路由变更后文档自动更新，无需手工维护。前后端联调时，该页面可作为接口契约的权威参考。

## 7. 本项目尚未使用的特性

以下特性计划在后续版本用到时补充到本文：

- POST 请求体与 Pydantic 模型校验 —— 计划于 v0.3（对接真实数据源，涉及鉴权参数）；
- 异常处理与超时控制 —— 计划于 v0.3（真实接口存在超时与非零返回码的情况）。

---

## 自测

1. 将 `noc_backend.py` 中的 `@app.get` 改为 `@app.post` 后，用浏览器直接访问该地址，会得到什么结果？原因是什么？
2. `requests.get` 与 `@app.get` 分别工作在通信的哪一端？各自的职责是什么？
3. 将 `app.mount("/", ...)` 移到 `@app.get("/api/kpi")` 之前，前端页面与 KPI 接口分别会出现什么现象？

建议实际修改代码验证，验证后执行 `git checkout -- <文件名>` 恢复。
