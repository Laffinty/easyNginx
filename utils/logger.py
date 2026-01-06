"""Loguru logger configuration."""

import sys
from pathlib import Path
from loguru import logger


def init_logger(log_dir: str = "logs"):
    """
    初始化日志配置
    
    Args:
        log_dir: 日志目录
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # 清空默认处理器
    logger.remove()
    
    # 控制台输出（INFO级别）
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        colorize=True
    )
    
    # 文件输出（DEBUG级别）
    logger.add(
        log_path / "easynginx_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
        rotation="00:00",  # 每天午夜轮转
        retention="10 days",  # 保留10天
        encoding="utf-8"
    )
    
    # 错误日志（单独文件）
    logger.add(
        log_path / "easynginx_errors_{time:YYYY-MM-DD}.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}\n{exception}",
        rotation="00:00",
        retention="10 days",
        encoding="utf-8",
        backtrace=True,
        diagnose=True
    )
    
    logger.info("Logger initialized successfully")


def get_logger():
    """获取日志记录器."""
    return logger