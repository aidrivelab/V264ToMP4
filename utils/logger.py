#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志模块
提供统一的日志记录功能
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def setup_logger(log_level=logging.INFO):
    """
    设置应用程序日志系统
    
    Args:
        log_level: 日志级别
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 创建根日志记录器
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # 清除现有的处理器，避免重复添加
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 确定日志文件路径
    if hasattr(sys, '_MEIPASS'):
        # 打包后的环境
        base_dir = os.path.dirname(sys.executable)
    else:
        # 开发环境
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    log_dir = os.path.join(base_dir, "logs")
    log_file = os.path.join(log_dir, "app.log")
    
    # 创建日志目录（如果不存在）
    os.makedirs(log_dir, exist_ok=True)
    
    # 添加文件处理器（带轮转）
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    logger.info("日志系统初始化完成")
    return logger


def get_logger(name):
    """
    获取指定名称的日志记录器
    
    Args:
        name: 日志记录器名称，通常使用 __name__
        
    Returns:
        logging.Logger: 日志记录器实例
    """
    return logging.getLogger(name)


def get_log_file_path():
    """
    获取日志文件路径
    
    Returns:
        str: 日志文件的完整路径
    """
    # 确定日志文件路径
    if hasattr(sys, '_MEIPASS'):
        # 打包后的环境
        base_dir = os.path.dirname(sys.executable)
    else:
        # 开发环境
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    log_dir = os.path.join(base_dir, "logs")
    log_file = os.path.join(log_dir, "app.log")
    
    return log_file


def configure_logger_from_config():
    """
    从配置文件配置日志系统
    
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    try:
        # 延迟导入以避免循环依赖
        from core.config_manager import ConfigManager
        
        # 创建配置管理器
        config_manager = ConfigManager()
        
        # 获取日志配置
        log_level_str = config_manager.get_config("log_level", "INFO")
        log_file = config_manager.get_config("log_file")
        
        # 转换日志级别
        log_level = getattr(logging, log_level_str.upper(), logging.INFO)
        
        # 设置日志系统
        logger = setup_logger(log_level)
        
        logger.info(f"从配置文件加载日志设置: 级别={log_level_str}, 文件={log_file}")
        return logger
        
    except Exception as e:
        # 如果配置失败，使用默认设置
        logger = setup_logger()
        logger.warning(f"从配置文件加载日志设置失败: {str(e)}")
        return logger


# 模块级别的初始化
if not logging.getLogger().handlers:
    configure_logger_from_config()