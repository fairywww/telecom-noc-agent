# 常用操作入口。用法：make <目标>
.PHONY: install run-noc run-adapter test eval up down

install:            ## 安装运行与开发依赖
	pip install -r requirements.txt -r requirements-dev.txt

run-noc:            ## 启动模拟 NOC 数据源（终端 1）
	python3 -m uvicorn noc_agent.server.noc_mock:app --port 8001

run-adapter:        ## 启动大屏后端（终端 2）
	python3 -m uvicorn noc_agent.server.adapter:app --port 8002

test:               ## 单元测试（零网络依赖，秒级）
	python3 -m pytest tests/ -v

eval:               ## Agent 评测集（需两个服务在运行）
	python3 eval.py

up:                 ## Docker 一键启动全部服务
	docker compose up --build

down:               ## 停止并移除容器
	docker compose down
