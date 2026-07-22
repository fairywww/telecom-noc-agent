# 阶段 1 · Python + FastAPI 工程基础

目标：能独立写出一个规范的 AI 服务接口，别人一条命令就能启动。

## 知识清单

### Python 工程基础

- [x] 虚拟环境与 pip（venv、requirements.txt 版本锁定） → [engineering.md](engineering.md)
- [ ] 项目结构组织（代码、配置、文档怎么摆）
- [ ] 类与异常处理
- [x] JSON 的读写与解析 → [data-pipeline.md](data-pipeline.md)
- [x] 函数抽取与复用（DRY）、生成器表达式 → [data-pipeline.md](data-pipeline.md)
- [x] 列表/字典推导式与排序 → [api-shapes.md](api-shapes.md)

### FastAPI

- [x] 路由与 GET 请求 → [fastapi.md](fastapi.md)
- [x] 返回 dict 自动转 JSON → [fastapi.md](fastapi.md)
- [x] uvicorn 与启动命令 → [fastapi.md](fastapi.md)
- [x] 静态文件托管与路由匹配顺序 → [fastapi.md](fastapi.md)
- [x] 自动接口文档（/docs、/redoc） → [fastapi.md](fastapi.md)
- [x] 前后端接口契约与向后兼容 → [data-pipeline.md](data-pipeline.md)
- [x] 聚合接口与明细接口的设计取舍 → [api-shapes.md](api-shapes.md)
- [x] POST 请求体与 Pydantic 参数校验 → [../04-agent/tool-parameters.md](../04-agent/tool-parameters.md)
- [x] 异常处理与超时兜底（错误回填、防御式执行） → [../04-agent/tool-parameters.md](../04-agent/tool-parameters.md)

### 工程化

- [ ] logging 日志
- [x] 配置管理（代码与配置分离、环境变量注入） → [engineering.md](engineering.md)
- [x] Docker 与 docker-compose 一键启动（详解版，含待完成的实践清单） → [docker.md](docker.md)
- [x] pytest 自动化测试（TestClient、monkeypatch、纯函数优先） → [engineering.md](engineering.md)
- [ ] Linux 部署基础
