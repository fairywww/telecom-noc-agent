# 工程化：环境隔离、容器化与自动化测试

**范围说明**：本文基于 v0.7 的改动：`requirements.txt` 版本锁定、`Dockerfile`、`docker-compose.yml`、`.dockerignore`、`tests/`。核心问题：**别人（以及三个月后的自己）如何在另一台机器上得到完全一致、可验证的运行结果。**

## 1. 可复现的三个层次

| 层次 | 手段 | 隔离/固定了什么 |
|------|------|---------------|
| 依赖版本 | `requirements.txt` 用 `==` 锁定 | 包的版本 |
| Python 环境 | `python3 -m venv .venv` | 本项目的包不与系统/其他项目混装 |
| 完整运行环境 | Docker 镜像 | 操作系统 + Python 版本 + 依赖 + 启动方式 |

`fastapi` 不写版本号时，今天与一年后装到的可能是接口不兼容的两个版本——"在我机器上能跑"的问题多半源于此。

## 2. 代码与配置分离

因环境而异的值一律走环境变量，代码只写默认值：

| 配置 | 本机 | Docker | 生产 |
|------|------|--------|------|
| `NOC_URL` | `http://localhost:8001`（默认） | `http://noc-backend:8001` | 真实 NOC 地址 |
| `LLM_API_KEY` | `.env` 文件 | compose 的 `env_file` | 密钥管理服务 |

同一份代码，三个环境，零修改——这是十二要素应用（12-Factor App）的核心原则之一。

## 3. Docker 与 compose

- `Dockerfile` 是镜像配方：基础系统（`python:3.11-slim`）→ 装依赖 → 拷代码 → 启动命令。**先拷 `requirements.txt` 单独安装再拷代码**：改代码不触发依赖层重建，构建缓存生效；
- `docker-compose.yml` 编排两个服务共用一个镜像，仅启动命令不同；**容器间用服务名互访**（`noc-backend`），不是 `localhost`——每个容器是一台独立"小机器"；
- `.dockerignore` 把密钥（`.env`）、版本库、虚拟环境挡在镜像外——镜像会被分发，进了镜像等于公开。

一键启动：`docker compose up --build`。

## 4. 自动化测试（tests/test_core.py）

8 个测试覆盖四层，共同特点：**不碰网络、不调 LLM**，1.6 秒跑完，随手可跑：

| 测试对象 | 手法 |
|---------|------|
| NOC 后端信封格式 | FastAPI `TestClient`——不起服务直接测接口 |
| `全网汇总` 聚合逻辑 | 纯函数直接断言 |
| `/api/kpi` 契约、未知地市错误 | `monkeypatch` 替换 `requests.get`，切断对下游的依赖 |
| RAG 切分、工具清单格式、防御式执行 | 纯函数直接断言 |

原则：**优先把逻辑写成纯函数，测试就便宜**。`全网汇总` 当初从路由函数里抽出来（见 [data-pipeline.md](data-pipeline.md)），此刻兑现了第二份红利。

慢而不稳定的部分（真实调 LLM）不放在 pytest 里，由评测脚本单独覆盖（见 [../05-agent-platform/agent-eval.md](../05-agent-platform/agent-eval.md)）。

---

## 自测

1. `Dockerfile` 里为什么先 `COPY requirements.txt` 单独安装，而不是一次 `COPY . .` 后再装？
2. compose 里 adapter 访问 NOC 用 `http://noc-backend:8001`，在本机直接运行时这个地址为什么不通？
3. `test_kpi契约` 为什么要 monkeypatch 掉 `requests.get`？不 mock 会带来什么问题？

建议实际修改验证，验证后 `git checkout -- <文件名>` 恢复。
