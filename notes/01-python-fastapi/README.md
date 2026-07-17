# 阶段 1 · Python + FastAPI 工程基础

目标：能独立写出一个规范的 AI 服务接口，别人一条命令就能启动。

## 知识清单

### Python 工程基础

- [ ] 虚拟环境与 pip（venv / conda，requirements.txt 的作用）
- [ ] 项目结构组织（代码、配置、文档怎么摆）
- [ ] 类与异常处理
- [ ] JSON 的读写与解析

### FastAPI

- [x] 路由与 GET 请求 → [fastapi.md](fastapi.md)
- [x] 返回 dict 自动转 JSON → [fastapi.md](fastapi.md)
- [x] uvicorn 与启动命令 → [fastapi.md](fastapi.md)
- [x] 静态文件托管与 mount 顺序陷阱 → [fastapi.md](fastapi.md)
- [x] Swagger 自动接口文档（/docs） → [fastapi.md](fastapi.md)
- [ ] POST 请求体与 Pydantic 参数校验（v0.3 接真数据时）
- [ ] 异常处理与超时兜底（v0.3 接真数据时）

### 工程化

- [ ] logging 日志
- [ ] 配置管理（地址、密钥不写死在代码里）
- [ ] Docker 与 docker-compose 一键启动（v0.7）
- [ ] Linux 部署基础（v0.7）
