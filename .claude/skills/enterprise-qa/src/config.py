"""
配置管理模块

从环境变量或配置文件加载配置
"""

import os
import yaml
from pathlib import Path
from typing import Optional


class Config:
    """配置类"""

    def __init__(self):
        # config.py is at: .claude/skills/enterprise-qa/src/config.py
        # Need to go up 5 levels to reach project root
        project_root = Path(__file__).parent.parent.parent.parent.parent
        default_db = project_root / "enterprise-qa-data" / "enterprise.db"
        default_kb = project_root / "enterprise-qa-data" / "knowledge"

        self.db_path: str = os.environ.get("ENTERPRISE_QA_DB_PATH", str(default_db))
        self.kb_path: str = os.environ.get("ENTERPRISE_QA_KB_PATH", str(default_kb))
        self.config_file: Optional[str] = os.environ.get("ENTERPRISE_QA_CONFIG", None)
        self.timezone: str = "Asia/Shanghai"

        if self.config_file and os.path.exists(self.config_file):
            self._load_from_file(self.config_file)

    def _load_from_file(self, config_path: str):
        """从YAML文件加载配置"""
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data:
            if "database" in data and "path" in data["database"]:
                self.db_path = data["database"]["path"]
            if "knowledge_base" in data and "root_path" in data["knowledge_base"]:
                self.kb_path = data["knowledge_base"]["root_path"]
            if "timezone" in data:
                self.timezone = data["timezone"]

    def get_db_path(self) -> str:
        """获取数据库路径"""
        return self.db_path

    def get_kb_path(self) -> str:
        """获取知识库路径"""
        return self.kb_path

    def get_timezone(self) -> str:
        """获取时区"""
        return self.timezone


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config():
    """重新加载配置"""
    global _config
    _config = Config()
    return _config
