#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口类
负责创建和管理应用程序的主界面
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
# 修改导入方式，使用绝对导入
from core.file_manager import FileManager
from core.config_manager import ConfigManager
from core.transcode_engine import TranscodeEngine
from core.task_manager import TaskManager
from utils.logger import get_logger

logger = get_logger(__name__)


class MainWindow:
    """
    主窗口类，用于创建和管理应用程序的主界面
    """
    
    def __init__(self, root):
        """
        初始化主窗口
        
        Args:
            root: Tkinter根窗口实例
        """
        self.root = root
        self.root.title("海雀监控视频转码工具")
        self.root.geometry("1000x700")
        self.root.resizable(True, True)
        
        # 初始化核心组件
        self.config_manager = ConfigManager()
        self.file_manager = FileManager()
        self.transcode_engine = TranscodeEngine(self.config_manager)
        self.task_manager = TaskManager(self.transcode_engine, self.config_manager.get_config("threads"))
        
        # 设置转码引擎的进度回调
        self.transcode_engine.set_progress_callback(self.update_task_progress)
        
        # 设置任务管理器的回调函数
        self.task_manager.set_completion_callback(self.on_transcode_completed)
        # 设置任务管理器的进度回调函数
        self.task_manager.set_progress_callback(self.update_task_progress)
        
        # 初始化变量
        self.source_dir = tk.StringVar(value=self.config_manager.get_config("source_dir"))
        self.output_dir = tk.StringVar(value=self.config_manager.get_config("output_dir"))
        self.merge_videos = tk.BooleanVar(value=False)
        self.include_audio = tk.BooleanVar(value=self.config_manager.get_config("include_audio") or False)
        self.video_files = []
        self.selected_video_files_count = 0
        
        # 创建界面组件
        self.create_widgets()
        
        # 扫描默认目录
        self.scan_directory()
    
    def create_widgets(self):
        """
        创建界面组件
        """
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 1. 顶部配置区域
        config_frame = ttk.LabelFrame(main_frame, text="配置", padding="10")
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 源目录选择
        ttk.Label(config_frame, text="源目录:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(config_frame, textvariable=self.source_dir, width=60).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(config_frame, text="浏览", command=self.browse_source_dir).grid(row=0, column=2, padx=5, pady=5)
        
        # 输出目录选择
        ttk.Label(config_frame, text="输出目录:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(config_frame, textvariable=self.output_dir, width=60).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(config_frame, text="浏览", command=self.browse_output_dir).grid(row=1, column=2, padx=5, pady=5)
        
        # 扫描按钮
        ttk.Button(config_frame, text="扫描目录", command=self.scan_directory).grid(row=0, column=3, rowspan=2, padx=5, pady=5)
        
        # 2. 中间操作区域
        operation_frame = ttk.Frame(main_frame)
        operation_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 操作按钮
        self.start_btn = ttk.Button(operation_frame, text="开始转码", command=self.start_transcode)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.pause_btn = ttk.Button(operation_frame, text="暂停", command=self.pause_transcode, state=tk.DISABLED)
        self.pause_btn.pack(side=tk.LEFT, padx=5)
        
        self.resume_btn = ttk.Button(operation_frame, text="继续", command=self.resume_transcode, state=tk.DISABLED)
        self.resume_btn.pack(side=tk.LEFT, padx=5)
        
        self.cancel_btn = ttk.Button(operation_frame, text="取消", command=self.cancel_transcode, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
        
        self.retry_btn = ttk.Button(operation_frame, text="重试失败任务", command=self.retry_failed_tasks, state=tk.DISABLED)
        self.retry_btn.pack(side=tk.LEFT, padx=5)
        
        # 选项区域
        options_frame = ttk.Frame(operation_frame)
        options_frame.pack(side=tk.RIGHT, padx=5)
        
        # 合并视频选项
        ttk.Checkbutton(options_frame, text="合并为一个视频", variable=self.merge_videos).pack(side=tk.RIGHT, padx=5)
        
        # 音频处理选项
        ttk.Checkbutton(options_frame, text="包含音频处理", variable=self.include_audio, 
                       command=self.on_include_audio_changed).pack(side=tk.RIGHT, padx=5)
        
        # 3. 转码文件列表
        file_list_frame = ttk.LabelFrame(main_frame, text="转码文件列表", padding="10")
        file_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建表格
        columns = ("filename", "status", "progress")
        self.file_tree = ttk.Treeview(file_list_frame, columns=columns, show="headings", height=15)
        
        # 设置列标题
        self.file_tree.heading("filename", text="文件名")
        self.file_tree.heading("status", text="状态")
        self.file_tree.heading("progress", text="进度")
        
        # 设置列宽
        self.file_tree.column("filename", width=400, anchor=tk.W)
        self.file_tree.column("status", width=100, anchor=tk.CENTER)
        self.file_tree.column("progress", width=200, anchor=tk.CENTER)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(file_list_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        self.file_tree.configure(yscroll=scrollbar.set)
        
        # 布局表格和滚动条
        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 4. 进度条
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(progress_frame, text="总进度:").pack(side=tk.LEFT, padx=5)
        self.total_progress = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=200, mode="determinate")
        self.total_progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.progress_label = ttk.Label(progress_frame, text="0/0 个文件")
        self.progress_label.pack(side=tk.RIGHT, padx=5)
        
        # 5. 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建日志文本框
        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 添加日志滚动条
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscroll=log_scrollbar.set)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def on_include_audio_changed(self):
        """
        音频处理选项变化时的回调函数
        """
        # 保存配置
        self.config_manager.set_config("include_audio", self.include_audio.get())
        
        # 如果启用了音频处理，显示提示信息
        if self.include_audio.get():
            self.log_message("已启用音频处理，如果原始文件包含音频，将保留并转码为AAC格式")
        else:
            self.log_message("已禁用音频处理，输出文件将不包含音频流")
    
    def browse_source_dir(self):
        """
        浏览选择源目录
        """
        dir_path = filedialog.askdirectory(title="选择源目录", initialdir=self.source_dir.get())
        if dir_path:
            self.source_dir.set(dir_path)
            self.config_manager.set_config("source_dir", dir_path)
            self.scan_directory()
    
    def browse_output_dir(self):
        """
        浏览选择输出目录
        """
        dir_path = filedialog.askdirectory(title="选择输出目录", initialdir=self.output_dir.get())
        if dir_path:
            # 如果输出目录是源目录的子目录，保存相对路径
            source_dir = self.source_dir.get()
            if dir_path.startswith(source_dir):
                rel_path = os.path.relpath(dir_path, source_dir)
                self.output_dir.set(rel_path)
            else:
                self.output_dir.set(dir_path)
            self.config_manager.set_config("output_dir", self.output_dir.get())
    
    def scan_directory(self):
        """
        扫描目录下的视频文件
        """
        self.log_message("开始扫描目录...")
        
        # 清空文件列表
        self.file_tree.delete(*self.file_tree.get_children())
        self.video_files = []
        
        # 扫描目录
        source_dir = self.source_dir.get()
        if os.path.exists(source_dir):
            self.video_files = self.file_manager.scan_directory(source_dir)
            # 按时间戳排序
            self.video_files = self.file_manager.sort_files_by_timestamp()
            
            # 更新文件列表
            self.update_file_list()
            
            self.log_message(f"扫描完成，共找到 {len(self.video_files)} 个.v264文件")
        else:
            self.log_message(f"源目录不存在: {source_dir}")
            messagebox.showwarning("警告", f"源目录不存在: {source_dir}")
    
    def update_file_list(self):
        """
        更新文件列表显示
        """
        # 清空现有列表
        self.file_tree.delete(*self.file_tree.get_children())
        
        # 添加文件到列表
        for file_path in self.video_files:
            filename = os.path.basename(file_path)
            self.file_tree.insert("", tk.END, values=(filename, "等待", "0%"))
    
    def update_task_progress(self, filename, progress):
        """
        更新任务进度
        
        Args:
            filename: 文件名
            progress: 进度百分比
        """
        # 更新文件列表中的进度
        for item in self.file_tree.get_children():
            values = self.file_tree.item(item, "values")
            if values[0] == filename:
                # 更新状态为转码中
                if values[1] != "转码中":
                    self.file_tree.item(item, values=(filename, "转码中", f"{progress:.1f}%"))
                else:
                    self.file_tree.item(item, values=(filename, "转码中", f"{progress:.1f}%"))
                break
        
        # 更新总进度
        self.update_total_progress()
    
    def update_total_progress(self):
        """
        更新总进度
        """
        # 获取任务管理器中的任务总数
        total_tasks = self.task_manager.get_total_count()
        if total_tasks == 0:
            return
        
        # 计算总进度
        completed_count = self.task_manager.get_completed_count()
        failed_count = self.task_manager.get_failed_count()
        cancelled_count = self.task_manager.get_cancelled_count()
        total_count = total_tasks
        
        # 更新进度条
        progress = (completed_count + failed_count + cancelled_count) / total_count * 100
        self.total_progress["value"] = progress
        
        # 更新进度标签
        self.progress_label.config(text=f"{completed_count + failed_count + cancelled_count}/{total_count} 个文件")
    
    def start_transcode(self):
        """
        开始转码
        """
        if not self.video_files:
            messagebox.showwarning("警告", "没有找到可转码的文件")
            return
        
        # 获取用户选中的文件
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选择要转码的文件")
            return
        
        # 获取选中的文件名列表
        selected_filenames = []
        for item in selected_items:
            values = self.file_tree.item(item, "values")
            selected_filenames.append(values[0])
        
        # 筛选出选中的视频文件
        selected_video_files = []
        for file_path in self.video_files:
            filename = os.path.basename(file_path)
            if filename in selected_filenames:
                selected_video_files.append(file_path)
        
        # 保存选中的文件数量，用于进度计算
        self.selected_video_files_count = len(selected_video_files)
        
        # 清空之前的任务
        self.task_manager.clear_tasks()
        
        # 获取输出目录
        source_dir = self.source_dir.get()
        output_dir = self.config_manager.get_output_dir(source_dir)
        
        if self.merge_videos.get():
            # 合并视频模式
            self.log_message("开始转码并合并视频...")
            
            # 第一步：将选中的v264文件转码为mp4文件
            temp_mp4_files = []
            include_audio = self.include_audio.get()
            for input_file in selected_video_files:
                output_file = self.transcode_engine.get_output_filename(input_file, output_dir)
                temp_mp4_files.append(output_file)
                self.task_manager.add_task(input_file, output_file, include_audio)
            
            # 第二步：转码完成后合并视频
            def on_merge_completed(results):
                # 获取成功转码的文件
                completed_tasks = [task for task in self.task_manager.get_all_tasks() if task["status"] == "completed"]
                if completed_tasks:
                    # 只合并成功转码的文件
                    successful_mp4_files = [task["output_file"] for task in completed_tasks]
                    self.log_message(f"开始合并 {len(successful_mp4_files)} 个成功转码的视频...")
                    # 生成合并后的输出文件名
                    merged_output = self.transcode_engine.get_merged_output_filename(output_dir)
                    # 执行合并操作
                    success = self.merge_videos(successful_mp4_files, merged_output)
                    if success:
                        self.log_message(f"视频合并成功: {merged_output}")
                        # 删除临时文件
                        for temp_file in successful_mp4_files:
                            if os.path.exists(temp_file):
                                try:
                                    os.remove(temp_file)
                                    self.log_message(f"已删除临时文件: {temp_file}")
                                except Exception as e:
                                    self.log_message(f"删除临时文件失败: {temp_file}, {str(e)}")
                    else:
                        self.log_message(f"视频合并失败: {merged_output}")
                else:
                    self.log_message("没有成功转码的视频文件，无法合并")
                
                # 恢复原始的完成回调
                self.task_manager.set_completion_callback(original_completion_callback)
                
                # 恢复按钮状态
                self.start_btn.config(state=tk.NORMAL)
                self.pause_btn.config(state=tk.DISABLED)
                self.resume_btn.config(state=tk.DISABLED)
                self.cancel_btn.config(state=tk.DISABLED)
                self.retry_btn.config(state=tk.NORMAL)
                
                # 显示完成通知
                completed_count = self.task_manager.get_completed_count()
                failed_count = self.task_manager.get_failed_count()
                cancelled_count = self.task_manager.get_cancelled_count()
                total_count = len(selected_video_files)
                
                self.log_message(f"转码完成: {completed_count} 个成功, {failed_count} 个失败, {cancelled_count} 个取消")
                messagebox.showinfo("转码完成", f"转码完成: {completed_count} 个成功, {failed_count} 个失败, {cancelled_count} 个取消")
            
            # 保存原始的完成回调
            original_completion_callback = self.task_manager.completion_callback
            # 设置临时的完成回调用于合并视频
            self.task_manager.set_completion_callback(on_merge_completed)
        else:
            # 普通转码模式
            self.log_message("开始转码...")
            
            # 添加转码任务
            include_audio = self.include_audio.get()
            for input_file in selected_video_files:
                # 生成输出文件名
                output_file = self.transcode_engine.get_output_filename(input_file, output_dir)
                self.task_manager.add_task(input_file, output_file, include_audio)
        
        # 开始转码
        self.task_manager.start()
        
        # 更新按钮状态
        self.start_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.NORMAL)
        self.retry_btn.config(state=tk.DISABLED)
    
    def pause_transcode(self):
        """
        暂停转码
        """
        self.task_manager.pause()
        
        # 更新按钮状态
        self.pause_btn.config(state=tk.DISABLED)
        self.resume_btn.config(state=tk.NORMAL)
        
        self.log_message("转码已暂停")
    
    def resume_transcode(self):
        """
        恢复转码
        """
        self.task_manager.resume()
        
        # 更新按钮状态
        self.pause_btn.config(state=tk.NORMAL)
        self.resume_btn.config(state=tk.DISABLED)
        
        self.log_message("转码已恢复")
    
    def cancel_transcode(self):
        """
        取消转码
        """
        if messagebox.askyesno("确认", "确定要取消转码吗？"):
            self.task_manager.cancel()
            
            # 更新按钮状态
            self.start_btn.config(state=tk.NORMAL)
            self.pause_btn.config(state=tk.DISABLED)
            self.resume_btn.config(state=tk.DISABLED)
            self.cancel_btn.config(state=tk.DISABLED)
            self.retry_btn.config(state=tk.NORMAL)
            
            self.log_message("转码已取消")
    
    def retry_failed_tasks(self):
        """
        重试失败的任务
        """
        self.task_manager.retry_failed_tasks()
        
        # 更新按钮状态
        self.start_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.resume_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.retry_btn.config(state=tk.DISABLED)
        
        self.log_message("开始重试失败的任务...")
    
    def on_transcode_completed(self, results):
        """
        转码完成回调
        
        Args:
            results: 转码结果
        """
        # 更新按钮状态
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        self.resume_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.DISABLED)
        self.retry_btn.config(state=tk.NORMAL)
        
        # 更新文件列表中的状态
        for item in self.file_tree.get_children():
            values = self.file_tree.item(item, "values")
            filename = values[0]
            
            # 查找对应的任务
            for task in self.task_manager.get_all_tasks():
                task_filename = os.path.basename(task["input_file"])
                if task_filename == filename:
                    # 更新状态
                    status = task["status"]
                    if status == "completed":
                        self.file_tree.item(item, values=(filename, "完成", "100%"))
                    elif status == "failed":
                        self.file_tree.item(item, values=(filename, "失败", "0%"))
                    elif status == "cancelled":
                        self.file_tree.item(item, values=(filename, "取消", f"{task['progress']:.1f}%"))
                    break
        
        # 更新总进度
        self.update_total_progress()
        
        # 显示完成通知
        completed_count = self.task_manager.get_completed_count()
        failed_count = self.task_manager.get_failed_count()
        cancelled_count = self.task_manager.get_cancelled_count()
        total_count = len(self.video_files)
        
        self.log_message(f"转码完成: {completed_count} 个成功, {failed_count} 个失败, {cancelled_count} 个取消")
        messagebox.showinfo("转码完成", f"转码完成: {completed_count} 个成功, {failed_count} 个失败, {cancelled_count} 个取消")
    
    def merge_videos(self, input_files, output_file):
        """
        合并视频文件
        
        Args:
            input_files: 输入文件列表
            output_file: 输出文件路径
        
        Returns:
            bool: 是否成功
        """
        try:
            # 获取音频处理设置
            include_audio = self.include_audio.get()
            
            # 调用转码引擎合并视频
            success = self.transcode_engine.merge_videos(
                input_files, 
                output_file, 
                progress_callback=self.update_progress,
                include_audio=include_audio
            )
            
            if success:
                self.log_message(f"视频合并成功: {output_file}")
                return True
            else:
                self.log_message(f"视频合并失败: {output_file}")
                return False
                
        except Exception as e:
            self.log_message(f"视频合并异常: {str(e)}")
            return False
    
    def log_message(self, message):
        """
        记录日志消息
        
        Args:
            message: 日志消息
        """
        # 获取当前时间
        import datetime
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 插入日志到文本框
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{current_time}] {message}\n")
        self.log_text.see(tk.END)  # 滚动到最后一行
        self.log_text.config(state=tk.DISABLED)
    
    def update_file_status(self, filename, status):
        """
        更新文件状态
        
        Args:
            filename: 文件名
            status: 状态
        """
        for item in self.file_tree.get_children():
            values = self.file_tree.item(item, "values")
            if values[0] == filename:
                self.file_tree.item(item, values=(filename, status, values[2]))
                break