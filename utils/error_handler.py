#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误处理模块
提供应用程序的异常处理和错误报告功能
"""

import sys
import os
import traceback
import logging
from tkinter import messagebox

# 修改导入方式，使用绝对导入
from core.config_manager import ConfigManager

# 获取日志记录器
logger = logging.getLogger(__name__)


def handle_exception(exc_type, exc_value, exc_traceback):
    """
    全局异常处理函数
    
    Args:
        exc_type: 异常类型
        exc_value: 异常值
        exc_traceback: 异常回溯
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # 处理键盘中断，让默认处理程序处理
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # 记录异常信息
    logger.error("未捕获的异常:", exc_info=(exc_type, exc_value, exc_traceback))
    
    # 创建错误报告
    error_info = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    # 尝试显示错误对话框
    try:
        messagebox.showerror(
            "程序错误",
            f"程序遇到了未预期的错误:\n\n{exc_value}\n\n"
            f"详细信息已记录到日志文件中。"
        )
    except:
        # 如果无法显示错误对话框，至少将错误信息打印到控制台
        print(f"程序错误: {exc_value}")
        print(f"详细信息: {error_info}")


def setup_exception_handler():
    """
    设置全局异常处理
    """
    # 设置全局异常处理函数
    sys.excepthook = handle_exception
    
    # 处理未捕获的线程异常
    def handle_thread_exception(args):
        if args.exc_type == SystemExit:
            return
        
        logger.error(
            "未捕获的线程异常:",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback)
        )
        
        # 尝试显示错误对话框
        try:
            error_msg = f"线程 {args.thread.name} 遇到了未预期的错误:\n\n{args.exc_value}"
            messagebox.showerror("线程错误", error_msg)
        except:
            print(f"线程错误: {args.exc_value}")
    
    # 注册线程异常处理函数（Python 3.8+）
    if hasattr(sys, 'unraisablehook'):
        sys.unraisablehook = handle_thread_exception
    
    # 在Python 3.8+中，可以使用threading.excepthook
    if hasattr(sys, 'excepthook'):
        import threading
        threading.excepthook = handle_thread_exception


def check_dependencies():
    """
    检查应用程序依赖是否满足
    
    Returns:
        bool: 所有依赖是否满足
    """
    missing_deps = []
    
    # 检查FFmpeg
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode != 0:
            missing_deps.append("FFmpeg未正确安装或不在PATH中")
    except FileNotFoundError:
        # 检查本地FFmpeg
        ffmpeg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe")
        if not os.path.exists(ffmpeg_path):
            missing_deps.append("FFmpeg未找到，请确保ffmpeg.exe在应用程序目录中")
    
    # 检查其他依赖
    try:
        import tkinter
    except ImportError:
        missing_deps.append("tkinter模块未安装")
    
    # 报告缺失的依赖
    if missing_deps:
        error_msg = "以下依赖缺失，应用程序无法正常运行:\n\n"
        error_msg += "\n".join(missing_deps)
        
        try:
            messagebox.showerror("依赖检查失败", error_msg)
        except:
            print(error_msg)
        
        return False
    
    return True


def initialize_error_handling():
    """
    初始化错误处理机制
    """
    # 设置异常处理
    setup_exception_handler()
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    logger.info("错误处理机制已初始化")