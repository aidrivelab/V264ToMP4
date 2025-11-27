#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
负责读取和保存应用程序配置
"""

import json
import os
import sys
# 修改导入方式，使用绝对导入
from utils.logger import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """
    配置管理类，用于处理应用程序的配置
    """
    
    def __init__(self, config_file="config.json"):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径，默认为config.json
        """
        # 处理打包后的路径问题
        if hasattr(sys, '_MEIPASS'):
            # 如果是打包后的可执行文件，配置文件应该在可执行文件同目录
            base_path = os.path.dirname(sys.executable)
        else:
            # 开发环境中，配置文件在项目根目录
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.config_file = os.path.join(base_path, config_file)
        self.config = self._load_config()
    
    def _load_config(self):
        """
        从配置文件中加载配置
        
        Returns:
            dict: 配置字典
        """
        default_config = {
            "source_dir": "",
            "output_dir": "converted",
            "ffmpeg_path": "ffmpeg.exe",
            "video_codec": "libx264",
            "crf": 18,
            "audio_codec": "aac",
            "audio_bitrate": "128k",
            "threads": 4,
            "overwrite": False,
            "keep_original": True,
            "log_level": "INFO"
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                logger.info(f"成功加载配置文件: {self.config_file}")
                
                # 合并默认配置和文件配置，确保所有配置项都存在
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                
                return config
            else:
                logger.warning(f"配置文件不存在，使用默认配置: {self.config_file}")
                self._save_config(default_config)
                return default_config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return default_config
    
    def _save_config(self, config):
        """
        将配置保存到配置文件中
        
        Args:
            config: 要保存的配置字典
        """
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            logger.info(f"成功保存配置文件: {self.config_file}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def get_config(self, key=None):
        """
        获取配置值
        
        Args:
            key: 配置项名称，若为None则返回所有配置
            
        Returns:
            配置值或配置字典
        """
        if key is None:
            return self.config
        return self.config.get(key)
    
    def set_config(self, key, value):
        """
        设置配置值
        
        Args:
            key: 配置项名称
            value: 配置项值
        """
        self.config[key] = value
        self._save_config(self.config)
        logger.info(f"更新配置: {key} = {value}")
    
    def get_output_dir(self, source_dir):
        """
        获取输出目录路径
        
        Args:
            source_dir: 源目录路径
            
        Returns:
            str: 输出目录路径
        """
        output_dir = self.config.get("output_dir")
        
        # 如果输出目录是相对路径，则相对于源目录
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(source_dir, output_dir)
        
        # 标准化路径，确保使用统一的分隔符（Windows使用反斜杠）
        output_dir = os.path.normpath(output_dir)
        
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"创建输出目录: {output_dir}")
        
        return output_dir