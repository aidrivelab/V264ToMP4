#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频转码工具主程序
用于将.v264格式的海雀监控视频文件批量转换为MP4格式
"""

import sys
import os
import logging
from tkinter import Tk

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 修改导入方式，使用绝对导入
from utils.logger import setup_logger
from utils.error_handler import initialize_error_handling
from gui.main_window import MainWindow


def main():
    """
    主函数，启动应用程序
    """
    try:
        # 初始化日志
        setup_logger()
        logger = logging.getLogger(__name__)
        logger.info("视频转码工具启动")
        
        # 初始化错误处理机制
        initialize_error_handling()
        
        # 创建主窗口
        root = Tk()
        app = MainWindow(root)
        root.mainloop()
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"应用程序启动失败: {e}", exc_info=True)
        
        # 尝试显示错误对话框
        try:
            from tkinter import messagebox
            messagebox.showerror(
                "启动错误",
                f"应用程序启动失败:\n\n{e}\n\n"
                f"详细信息已记录到日志文件中。"
            )
        except:
            print(f"应用程序启动失败: {e}")
        
        sys.exit(1)
    finally:
        logger = logging.getLogger(__name__)
        logger.info("视频转码工具退出")


if __name__ == "__main__":
    main()