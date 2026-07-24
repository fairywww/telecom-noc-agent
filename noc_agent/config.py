"""统一配置：项目路径与环境变量加载。

密钥与环境相关配置一律来自环境变量（.env 仅本地开发用，已被
.gitignore 忽略）；模块导入即完成 .env 加载，全包共享。
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"
KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"
WEB_DIR = PROJECT_ROOT / "web"
TICKET_DB = PROJECT_ROOT / "data" / "tickets.db"


def load_env_file():
    """把 .env 的 KEY=VALUE 写入环境变量；真实环境变量优先（setdefault）"""
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


load_env_file()


def prompt(name):
    """读取 prompts/ 下的提示词文件"""
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")
