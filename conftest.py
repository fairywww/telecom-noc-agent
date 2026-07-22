"""pytest 根配置：让测试能 import 仓库根目录的模块；
无密钥环境（如 CI）下给个假 key，保证不调 LLM 的测试照常运行。"""
import os

os.environ.setdefault("LLM_API_KEY", "test-key-not-used")
