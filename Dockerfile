# 镜像配方：操作系统 + Python + 依赖 + 代码，一次打包，处处运行
FROM python:3.11-slim

WORKDIR /app

# 先只拷依赖清单再安装——代码改动时这一层缓存不失效，重建更快
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001 8002

# 默认启动大屏后端；noc-backend 服务在 compose 里覆盖此命令
CMD ["python3", "-m", "uvicorn", "noc_agent.server.adapter:app", "--host", "0.0.0.0", "--port", "8002"]
