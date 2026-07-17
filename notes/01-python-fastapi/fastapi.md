# FastAPI：这个项目里用到的每一个知识点

> 约定：只记本仓库真实出现过的用法，每条都指到代码位置。

## 1. FastAPI 是什么

一个 Python Web 框架，把「收到 HTTP 请求 → 调用你的函数 → 把返回值变成 JSON 发回去」这整件事包掉。本项目两个后端（`noc_backend.py`、`adapter.py`）都是它写的。

## 2. 三行就是一个服务

```python
from fastapi import FastAPI
app = FastAPI()                      # 创建应用对象

@app.get("/api/statistics/all")      # 把「GET 这个路径」绑定到下面的函数
def statistics_all():
    return {"code": 0, "data": ...}  # 返回 dict，FastAPI 自动转成 JSON
```

出处：`noc_backend.py`。三个要点：

- `@app.get("/路径")` 是装饰器：请求路径和处理函数的"绑定登记"
- 函数**直接返回 dict**，FastAPI 自动序列化成 JSON、自动加 `Content-Type: application/json`
- 一个 `app` 上可以登记任意多个路径

## 3. uvicorn 是什么，启动命令为什么长那样

FastAPI 只定义「怎么处理请求」，**不负责监听端口**。真正开门迎客的是 uvicorn（一个 ASGI 服务器）。

```bash
python3 -m uvicorn noc_backend:app --port 8001
#                  ^^^^^^^^^^^ ^^^        ^^^^
#                  模块名(文件名) 变量名     监听端口
```

读法：「去 `noc_backend.py` 里找那个叫 `app` 的对象，架在 8001 端口上」。
类比：FastAPI 是厨师（做菜），uvicorn 是前台+服务员（迎客、传菜）。

## 4. 客户端和服务端可以是同一个程序

`adapter.py` 同时扮演两个角色：

- 对浏览器它是**服务端**：`@app.get("/api/kpi")` 收请求
- 对 NOC 后端它是**客户端**：`requests.get(...)` 发请求（`adapter.py` 第 27 行）

`requests.get` 和 `@app.get` 名字像，方向相反：一个主动出去要数据，一个等着别人来要数据。

## 5. 静态文件托管，以及一个顺序陷阱

`adapter.py` 最后一行：

```python
app.mount("/", StaticFiles(directory=..., html=True))
```

把整个目录挂到根路径，浏览器访问 `http://localhost:8002/` 时送出 `index.html`。

**陷阱**：这行必须写在所有 `@app.get` 路由**之后**。FastAPI 按登记顺序匹配路径，`mount("/")` 会兜住所有请求——如果放在最前面，`/api/kpi` 也会被它拦下变成 404。

## 6. 白送的功能：自动接口文档

服务跑着的时候，浏览器打开：

```
http://localhost:8001/docs
```

会看到 Swagger UI——所有接口自动列出，还能点 "Try it out" 直接调。这不是我们写的，是 FastAPI 从路由定义自动生成的。对接前后端时把这个页面甩给对方，比口头说接口格式靠谱。

## 7. 本项目还没用到、下一步会遇到的

- POST 请求体 + Pydantic 参数校验 —— v0.3 接真实数据源、带鉴权参数时会用到
- 异常处理 —— 真实 NOC 接口会超时、会返回非 0 的 code，适配层得兜住

用到那天再回来补，不提前学。

---

## 自测三问

1. 把 `noc_backend.py` 里的 `@app.get` 改成 `@app.post`，浏览器直接访问那个地址会发生什么？为什么？
2. `requests.get` 和 `@app.get` 的区别是什么？各自站在通信的哪一端？
3. 把 `app.mount("/", ...)` 挪到 `@app.get("/api/kpi")` 前面，大屏页面和接口各自会怎样？

（答不上来就去改代码试一次——试完记得 `git checkout -- 文件名` 恢复。）
