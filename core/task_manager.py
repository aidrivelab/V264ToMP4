#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务管理模块
负责管理转码任务队列，支持多线程处理
"""

import os
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
# 修改导入方式，使用绝对导入
from utils.logger import get_logger

logger = get_logger(__name__)


class TaskManager:
    """
    任务管理类，用于管理转码任务队列和多线程处理
    """
    
    def __init__(self, transcode_engine, max_workers=4):
        """
        初始化任务管理器
        
        Args:
            transcode_engine: 转码引擎实例
            max_workers: 最大工作线程数，默认为4
        """
        self.transcode_engine = transcode_engine
        self.max_workers = max_workers
        self.executor = None
        self.tasks = []
        self.task_results = {}
        self.is_running = False
        self.is_paused = False
        self.is_cancelled = False
        self.completed_count = 0
        self.total_count = 0
        self.progress_callback = None
        self.completion_callback = None
    
    def set_progress_callback(self, callback):
        """
        设置进度回调函数
        
        Args:
            callback: 进度回调函数，接收文件名和进度百分比作为参数
        """
        self.progress_callback = callback
    
    def set_completion_callback(self, callback):
        """
        设置完成回调函数
        
        Args:
            callback: 完成回调函数，接收任务结果作为参数
        """
        self.completion_callback = callback
    
    def add_task(self, input_file, output_file, include_audio=False):
        """
        添加转码任务
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
            include_audio: 是否包含音频处理，默认为False
        """
        task = {
            "input_file": input_file,
            "output_file": output_file,
            "include_audio": include_audio,
            "status": "waiting",  # waiting, running, completed, failed, cancelled
            "progress": 0.0,
            "error_msg": ""
        }
        self.tasks.append(task)
        logger.info(f"添加转码任务: {input_file} -> {output_file}, 音频处理: {include_audio}")
    
    def add_tasks(self, task_list):
        """
        批量添加转码任务
        
        Args:
            task_list: 任务列表，每个任务包含input_file、output_file和可选的include_audio
        """
        for task in task_list:
            include_audio = task.get("include_audio", False)
            self.add_task(task["input_file"], task["output_file"], include_audio)
        logger.info(f"批量添加转码任务，共 {len(task_list)} 个任务")
    
    def _task_wrapper(self, task_index):
        """
        任务包装函数，用于执行转码任务并更新任务状态
        
        Args:
            task_index: 任务索引
        """
        task = self.tasks[task_index]
        input_file = task["input_file"]
        output_file = task["output_file"]
        include_audio = task.get("include_audio", False)
        filename = os.path.basename(input_file)
        
        # 更新任务状态为运行中
        task["status"] = "running"
        # 立即通知GUI任务开始运行，进度为0%
        if self.progress_callback:
            self.progress_callback(filename, 0.0)
        
        # 执行转码任务
        success, error_msg = self.transcode_engine.transcode_file(input_file, output_file, include_audio=include_audio)
        
        # 更新任务结果
        if success:
            task["status"] = "completed"
            task["progress"] = 100.0
            task["error_msg"] = ""
            self.completed_count += 1
            logger.info(f"任务完成: {input_file} -> {output_file}")
        else:
            task["status"] = "failed"
            task["error_msg"] = error_msg
            logger.error(f"任务失败: {input_file} -> {output_file}, {error_msg}")
        
        # 检查是否所有任务都已完成
        if self.completed_count + self.get_failed_count() + self.get_cancelled_count() == self.total_count:
            self.is_running = False
            logger.info("所有转码任务已完成")
            # 调用完成回调函数
            if self.completion_callback:
                self.completion_callback(self.task_results)
    
    def start(self):
        """
        开始执行所有转码任务
        """
        if self.is_running:
            logger.warning("转码任务已经在运行中")
            return
        
        if not self.tasks:
            logger.warning("没有待执行的转码任务")
            return
        
        logger.info(f"开始执行转码任务，共 {len(self.tasks)} 个任务，使用 {self.max_workers} 个线程")
        
        # 重置状态
        self.is_running = True
        self.is_paused = False
        self.is_cancelled = False
        self.completed_count = 0
        self.total_count = len(self.tasks)
        
        # 创建线程池
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # 提交所有任务到线程池
        for i in range(len(self.tasks)):
            self.executor.submit(self._task_wrapper, i)
        
        # 关闭线程池，等待所有任务完成
        self.executor.shutdown(wait=False)
    
    def pause(self):
        """
        暂停转码任务
        """
        if not self.is_running:
            logger.warning("转码任务没有在运行中")
            return
        
        self.is_paused = True
        self.transcode_engine.pause()
        logger.info("转码任务已暂停")
    
    def resume(self):
        """
        恢复转码任务
        """
        if not self.is_running:
            logger.warning("转码任务没有在运行中")
            return
        
        self.is_paused = False
        self.transcode_engine.resume()
        logger.info("转码任务已恢复")
    
    def cancel(self):
        """
        取消所有转码任务
        """
        if not self.is_running:
            logger.warning("转码任务没有在运行中")
            return
        
        self.is_cancelled = True
        self.transcode_engine.cancel()
        
        # 更新所有等待中的任务状态为已取消
        for task in self.tasks:
            if task["status"] == "waiting":
                task["status"] = "cancelled"
        
        logger.info("转码任务已取消")
        self.is_running = False
    
    def get_task_status(self, task_index):
        """
        获取指定任务的状态
        
        Args:
            task_index: 任务索引
            
        Returns:
            dict: 任务状态信息
        """
        if 0 <= task_index < len(self.tasks):
            return self.tasks[task_index]
        return None
    
    def get_all_tasks(self):
        """
        获取所有任务的状态
        
        Returns:
            list: 所有任务的状态信息
        """
        return self.tasks
    
    def get_completed_count(self):
        """
        获取已完成的任务数量
        
        Returns:
            int: 已完成的任务数量
        """
        return self.completed_count
    
    def get_failed_count(self):
        """
        获取失败的任务数量
        
        Returns:
            int: 失败的任务数量
        """
        return sum(1 for task in self.tasks if task["status"] == "failed")
    
    def get_cancelled_count(self):
        """
        获取已取消的任务数量
        
        Returns:
            int: 已取消的任务数量
        """
        return sum(1 for task in self.tasks if task["status"] == "cancelled")
    
    def get_total_count(self):
        """
        获取总任务数量
        
        Returns:
            int: 总任务数量
        """
        return len(self.tasks)
    
    def clear_tasks(self):
        """
        清空所有任务
        """
        self.tasks = []
        self.task_results = {}
        self.is_running = False
        self.is_paused = False
        self.is_cancelled = False
        self.completed_count = 0
        self.total_count = 0
        logger.info("已清空所有转码任务")
    
    def retry_failed_tasks(self):
        """
        重试所有失败的任务
        """
        failed_tasks = [task for task in self.tasks if task["status"] == "failed"]
        if not failed_tasks:
            logger.warning("没有失败的任务可以重试")
            return
        
        logger.info(f"开始重试失败的任务，共 {len(failed_tasks)} 个任务")
        
        # 重置失败任务的状态
        for task in failed_tasks:
            task["status"] = "waiting"
            task["progress"] = 0.0
            task["error_msg"] = ""
        
        # 重新开始执行任务
        self.start()

