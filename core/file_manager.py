#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件管理模块
负责扫描、筛选和排序视频文件
"""

import os
import re
from utils.logger import get_logger

logger = get_logger(__name__)


class FileManager:
    """
    文件管理类，用于处理视频文件的扫描、筛选和排序
    """
    
    def __init__(self):
        """
        初始化文件管理器
        """
        self.video_files = []
    
    def scan_directory(self, directory, file_extension=".v264"):
        """
        扫描指定目录下的所有视频文件
        
        Args:
            directory: 要扫描的目录路径
            file_extension: 要筛选的文件扩展名，默认为.v264
            
        Returns:
            list: 扫描到的视频文件列表
        """
        logger.info(f"开始扫描目录: {directory}")
        self.video_files = []
        
        try:
            # 遍历目录下的所有文件
            for root, dirs, files in os.walk(directory):
                for file in files:
                    # 筛选指定扩展名的文件
                    if file.lower().endswith(file_extension):
                        file_path = os.path.join(root, file)
                        self.video_files.append(file_path)
                        logger.debug(f"找到文件: {file_path}")
            
            logger.info(f"扫描完成，共找到 {len(self.video_files)} 个{file_extension}文件")
            return self.video_files
        except Exception as e:
            logger.error(f"扫描目录失败: {e}")
            return []
    
    def sort_files_by_timestamp(self):
        """
        按照文件名中的时间戳对文件进行排序
        文件名格式如：0-102042.v264，其中102042为时间戳
        
        Returns:
            list: 按时间戳排序后的文件列表
        """
        logger.info("开始按时间戳排序文件")
        
        def get_timestamp(file_path):
            """
            从文件名中提取时间戳
            
            Args:
                file_path: 文件路径
                
            Returns:
                int: 提取的时间戳，若无法提取则返回0
            """
            # 获取文件名（不包含路径）
            file_name = os.path.basename(file_path)
            
            # 使用正则表达式提取时间戳
            # 匹配格式如：0-102042.v264，提取102042
            match = re.match(r"\d+-(\d+)\.v264", file_name)
            if match:
                return int(match.group(1))
            else:
                logger.warning(f"无法从文件名中提取时间戳: {file_name}")
                return 0
        
        # 按时间戳排序文件列表
        sorted_files = sorted(self.video_files, key=get_timestamp)
        self.video_files = sorted_files
        
        logger.info(f"文件排序完成，共 {len(self.video_files)} 个文件")
        return self.video_files
    
    def get_file_list(self):
        """
        获取当前的文件列表
        
        Returns:
            list: 当前的文件列表
        """
        return self.video_files
    
    def filter_files(self, filter_func=None):
        """
        根据自定义过滤函数筛选文件
        
        Args:
            filter_func: 过滤函数，接收文件路径作为参数，返回布尔值
            
        Returns:
            list: 筛选后的文件列表
        """
        if filter_func is None:
            return self.video_files
        
        filtered_files = [file for file in self.video_files if filter_func(file)]
        self.video_files = filtered_files
        return self.video_files
    
    def clear_file_list(self):
        """
        清空当前的文件列表
        """
        self.video_files = []
        logger.info("文件列表已清空")
