"""
日誌工具
"""
import sys
from pathlib import Path
from loguru import logger
from config.settings import LOGS_DIR

# 移除預設 handler
logger.remove()

# 添加控制台輸出
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

# 添加檔案輸出 - 一般日誌
logger.add(
    LOGS_DIR / "qqquest_{time:YYYY-MM-DD}.log",
    rotation="00:00",  # 每天午夜輪替
    retention="30 days",  # 保留 30 天
    encoding="utf-8",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

# 添加檔案輸出 - 錯誤日誌
logger.add(
    LOGS_DIR / "errors_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="90 days",  # 錯誤日誌保留更久
    encoding="utf-8",
    level="ERROR",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}\n{exception}"
)


def get_logger(name: str):
    """取得指定名稱的 logger"""
    return logger.bind(name=name)


# 匯出
__all__ = ['logger', 'get_logger']




