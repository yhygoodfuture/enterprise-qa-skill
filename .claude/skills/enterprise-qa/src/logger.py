"""
日志模块

提供结构化日志记录功能
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from enum import Enum


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Logger:
    """日志记录器"""

    def __init__(self, name: str = "enterprise-qa", log_dir: Optional[str] = None):
        """
        Args:
            name: 日志记录器名称
            log_dir: 日志目录，None 则不写入文件
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # 避免重复添加 handler
        if not self.logger.handlers:
            # 控制台 handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%H:%M:%S'
            ))
            # Windows 下强制 UTF-8 输出
            if sys.platform == 'win32':
                try:
                    import io
                    console_handler.stream = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
                except Exception:
                    pass
            self.logger.addHandler(console_handler)

            # 文件 handler（如果指定了目录）
            if log_dir:
                self._setup_file_handler(log_dir)

    def _setup_file_handler(self, log_dir: str):
        """设置文件 handler"""
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # 每日一个日志文件
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = log_path / f"enterprise-qa-{today}.log"

        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        # 详细格式（包含文件名和行号）
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s:%(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

    def _log(self, level: LogLevel, message: str, **kwargs):
        """记录日志"""
        extra_info = " | ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
        full_message = f"{message} | {extra_info}" if extra_info else message

        getattr(self.logger, level.value.lower())(full_message)

    def debug(self, message: str, **kwargs):
        """记录调试信息"""
        self._log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """记录一般信息"""
        self._log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """记录警告信息"""
        self._log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """记录错误信息"""
        self._log(LogLevel.ERROR, message, **kwargs)

    def log_query(self, question: str, intent: str, duration_ms: float, result_count: int = 0):
        """记录查询日志"""
        self.info(
            f"Query processed",
            question=question[:50],
            intent=intent,
            duration_ms=round(duration_ms, 2),
            result_count=result_count
        )

    def log_cache(self, operation: str, hit: bool, key: str):
        """记录缓存操作"""
        self.debug(
            f"Cache {operation}",
            operation=operation,
            hit=hit,
            key=key[:20]
        )

    def log_error(self, error_type: str, error_message: str, question: str = ""):
        """记录错误日志"""
        self.error(
            f"Error: {error_type}",
            error_type=error_type,
            error_message=error_message,
            question=question[:50] if question else ""
        )


# 全局日志实例
_logger: Optional[Logger] = None


def get_logger(log_dir: Optional[str] = None) -> Logger:
    """获取全局日志实例"""
    global _logger
    if _logger is None:
        _logger = Logger(log_dir=log_dir)
    return _logger


def init_logger(log_dir: str):
    """初始化日志系统"""
    global _logger
    _logger = Logger(log_dir=log_dir)
    return _logger