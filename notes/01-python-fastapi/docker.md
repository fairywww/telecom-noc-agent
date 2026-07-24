# Docker 详解：镜像、容器与 compose

**范围说明**：本文基于本仓库的 `Dockerfile`、`docker-compose.yml`、`.dockerignore` 三个文件，面向零基础详细展开。**状态：配置已完成并提交，本机实测待进行**（安装 Docker 后按第 6 节操作，实测结论回填本文）。

## 1. 三个核心概念

| 概念 | 是什么 | 对应本仓库 |
|------|--------|-----------|
| Dockerfile | 构建说明书：逐步描述如何组装运行环境 | `Dockerfile` |
| 镜像（image） | 按说明书构建出的成品：操作系统 + Python + 依赖 + 代码，冻结封装，可复制分发 | `docker compose build` 的产物 |
| 容器（container） | 镜像的一次运行实例；一个镜像可同时运行多个容器 | noc-backend 与 adapter 两个容器共用一个镜像 |

与 venv 的关系：venv 只隔离"本项目安装了哪些 Python 包"；Docker 将**操作系统与 Python 解释器本身**一并打包。宿主机是 macOS + Python 3.9，容器内是 Linux + Python 3.11；将来部署到 Linux 服务器，运行的是同一个镜像——环境差异被彻底消除。

## 2. Dockerfile 逐行解读

```dockerfile
FROM python:3.11-slim        # 基础镜像：官方预装 Python 3.11 的精简 Linux
WORKDIR /app                 # 容器内工作目录，后续指令均在此执行
COPY requirements.txt .      # 先只复制依赖清单
RUN pip install --no-cache-dir -r requirements.txt
COPY . .                     # 再复制全部代码
EXPOSE 8001 8002             # 声明监听端口（说明性质）
CMD ["python3", "-m", "uvicorn", "adapter:app", "--host", "0.0.0.0", "--port", "8002"]
```

### 2.1 分层缓存——指令顺序的原理

每条指令生成一个**层**；重建时，输入未变化的层直接复用缓存。因此把"变化少的放前面、变化频繁的放后面"：

- 依赖清单极少变 → `COPY requirements.txt` + `RUN pip install` 放前面，日常重建时这两层命中缓存，跳过数分钟的安装；
- 代码天天变 → `COPY . .` 放后面，只有这层及之后重建，秒级完成。

若一开始就 `COPY . .`，任何一行代码改动都会使后续所有层缓存失效，每次重建都重新安装全部依赖。

### 2.2 两个必要细节

- `--host 0.0.0.0`：容器内若只监听 127.0.0.1，宿主机与其他容器均无法访问。容器内的服务必须监听 0.0.0.0；
- `CMD` 是**默认**启动命令，运行时可被覆盖——compose 中 noc-backend 服务正是用 `command:` 覆盖它来运行另一个应用。

## 3. docker-compose.yml 逐段解读

Dockerfile 解决"单个环境如何构建"，compose 解决"多个服务如何一起运行"。

```yaml
services:
  noc-backend:
    build: .                                     # 用本目录 Dockerfile 构建
    command: python3 -m uvicorn noc_agent.server.noc_mock:app --host 0.0.0.0 --port 8001
    ports: ["8001:8001"]
  adapter:
    build: .
    environment:
      - NOC_URL=http://noc-backend:8001          # 服务名互访（见 3.1）
    env_file:
      - path: .env
        required: false                          # 无密钥也可启动（仅 Agent 功能不可用）
    ports: ["8002:8002"]
    depends_on: [noc-backend]                    # 启动顺序：先数据源
```

### 3.1 容器间网络：服务名即主机名

`docker compose up` 自动创建一个虚拟网络，每个容器在网络内的主机名即服务名。因此 adapter 访问数据源写 `http://noc-backend:8001`。

**关键认知：容器内的 localhost 指容器自身**，不是宿主机，也不是别的容器。这是初学 Docker 最常见的错误来源。本仓库的对应改造：`noc_agent/server/adapter.py` 的 NOC 地址改为环境变量 `NOC_URL` 注入——本机直跑时默认 `localhost:8001`，容器内注入服务名，同一份代码适配两种环境。

### 3.2 端口映射

`"8002:8002"` 读作 `宿主机端口:容器端口`。容器网络与宿主机隔离，映射即在边界上开一条通道：浏览器访问的 `localhost:8002` 是宿主机端口，被转发到容器的 8002。若写 `"9999:8002"`，则浏览器需访问 9999。

### 3.3 密钥的完整路径

- **构建期**：`.dockerignore` 排除 `.env`——镜像会被分发，密钥一旦进入镜像即视为泄露；
- **运行期**：`env_file` 在容器启动时把 `.env` 内容注入为环境变量。

一挡一注，与 [llm-basics.md](../02-llm-api/llm-basics.md) 第 2 节的"密钥三件套"是同一原则在容器场景的延伸。

## 4. 常用命令

| 命令 | 作用 |
|------|------|
| `docker compose up --build` | 构建并前台启动全部服务 |
| `docker compose up -d` | 后台启动 |
| `docker compose logs -f adapter` | 跟踪某服务日志 |
| `docker compose ps` | 查看运行状态 |
| `docker compose exec adapter bash` | 进入运行中的容器 |
| `docker compose down` | 停止并移除全部容器 |

## 5. 本仓库未涉及、下一步会遇到的

- **volumes（数据卷）**：容器删除后其内部文件即消失；需要持久化的数据（数据库文件、上传内容）须挂载数据卷。本项目数据为内存模拟，暂不需要；
- **镜像仓库（registry）**：`docker push` 把镜像发布到仓库供服务器拉取，与 git push 代码同理。

## 6. 实践步骤（待完成后回填结论）

```bash
# ① 安装（macOS 推荐 OrbStack，兼容全部 docker 命令）：
brew install --cask orbstack      # 或从 orbstack.dev 下载

# ② 一键启动
cd ~/CMJS-2024/wksp/telecom-noc-agent
docker compose up --build         # 首次构建约 1–3 分钟

# ③ 浏览器打开 http://localhost:8002 ，应与本机直跑完全一致
```

三个验证实验，各对应一个核心概念：

1. **分层缓存**：build 一次后修改一行 `web/index.html` 再 build，观察 pip install 层显示 `CACHED`；
2. **密钥路径**：`docker compose exec adapter ls -la /app` 应看不到 `.env`（构建期被挡）；`docker compose exec adapter env | grep LLM` 应看到密钥（运行期注入）；
3. **环境隔离**：`docker compose exec adapter python3 --version` 输出 3.11，宿主机为 3.9。

---

## 自测

1. Dockerfile 中把 `COPY . .` 移到 `RUN pip install` 之前，对日常开发的重建速度有什么影响？为什么？
2. adapter 容器内执行 `curl http://localhost:8001` 会得到什么结果？正确地址应是什么？
3. `.env` 分别被哪两个机制处理？各自发生在什么阶段，防的是什么？

学习本文时先读第 1–3 节理解概念，实践步骤可与阅读分开进行。
