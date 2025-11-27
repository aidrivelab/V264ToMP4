#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
转码引擎模块
封装FFmpeg调用，执行实际的视频转码操作
"""

import os
import subprocess
import re
import sys
import threading
# 修改导入方式，使用绝对导入
from utils.logger import get_logger

logger = get_logger(__name__)


class TranscodeEngine:
    """
    转码引擎类，用于执行视频转码操作
    """
    
    def __init__(self, config_manager):
        """
        初始化转码引擎
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        ffmpeg_path = config_manager.get_config("ffmpeg_path")
        
        # 处理FFmpeg路径，确保在打包后能正确找到
        if not os.path.isabs(ffmpeg_path):
            # 如果是相对路径，需要确定基础路径
            if hasattr(sys, '_MEIPASS'):
                # 打包后的环境，FFmpeg应该在可执行文件同目录
                base_path = os.path.dirname(sys.executable)
            else:
                # 开发环境，FFmpeg在项目根目录
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            ffmpeg_path = os.path.join(base_path, ffmpeg_path)
        
        self.ffmpeg_path = ffmpeg_path
        self.is_paused = False
        self.is_cancelled = False
        self.progress_callback = None
    
    def set_progress_callback(self, callback):
        """
        设置进度回调函数
        
        Args:
            callback: 进度回调函数，接收文件名和进度百分比作为参数
        """
        self.progress_callback = callback
    
    def pause(self):
        """
        暂停转码操作
        """
        self.is_paused = True
        logger.info("转码操作已暂停")
    
    def resume(self):
        """
        恢复转码操作
        """
        self.is_paused = False
        logger.info("转码操作已恢复")
    
    def cancel(self):
        """
        取消转码操作
        """
        self.is_cancelled = True
        logger.info("转码操作已取消")
    
    def reset(self):
        """
        重置转码状态
        """
        self.is_paused = False
        self.is_cancelled = False
    
    def build_ffmpeg_command(self, input_file, output_file, include_audio=False):
        """
        构建FFmpeg转码命令
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
            include_audio: 是否包含音频处理（默认False，保持原有行为）
            
        Returns:
            list: FFmpeg命令列表
        """
        # 获取配置参数
        video_codec = self.config_manager.get_config("video_codec")
        crf = self.config_manager.get_config("crf")
        audio_codec = self.config_manager.get_config("audio_codec")
        audio_bitrate = self.config_manager.get_config("audio_bitrate")
        threads = self.config_manager.get_config("threads")
        overwrite = self.config_manager.get_config("overwrite")
        
        # 构建FFmpeg命令 - 生成通用MP4格式，支持拖动播放
        # 对于v264文件，我们需要先解码再编码，确保生成标准MP4格式
        # 注意：海雀监控的.v264文件实际上是HEVC/H.265格式，不是H.264格式
        command = [
            self.ffmpeg_path,
            # 输入参数
            "-f", "hevc",  # 明确指定输入格式为hevc（海雀.v264文件实际是H.265格式）
            "-analyzeduration", "10M",  # 增加分析时间
            "-probesize", "10M",  # 增加缓冲区大小
            "-fflags", "+genpts",  # 生成显示时间戳
            "-r", "25",  # 假设输入帧率为25fps（海雀摄像头通常使用这个帧率）
            "-i", input_file,
            # 视频编码参数
            "-c:v", "libx264",  # 使用标准h.264编码，确保通用性
            "-preset", "fast",  # 快速编码预设
            "-crf", str(crf),  # 视频质量参数
        ]
        
        # 根据include_audio参数决定是否处理音频
        if include_audio:
            # 音频处理参数
            command.extend([
                "-c:a", audio_codec,  # 使用配置的音频编码器
                "-b:a", audio_bitrate,  # 使用配置的音频比特率
            ])
        else:
            # 保持原有行为，禁用音频流
            command.append("-an")  # 禁用音频流（v264文件通常没有音频）
        
        # 继续添加其他参数
        command.extend([
            # 兼容性参数
            "-profile:v", "main",  # 使用main profile确保兼容性
            "-level", "3.0",  # 视频级别，确保广泛兼容
            "-pix_fmt", "yuv420p",  # 使用通用的YUV格式
            # MP4封装参数
            "-movflags", "faststart",  # 将元数据移到文件头部，支持拖动播放
            # 输出参数
            "-y" if overwrite else "-n",
            output_file
        ])
        
        logger.debug(f"构建FFmpeg命令: {' '.join(command)}")
        return command
    
    def extract_progress(self, output_line):
        """
        从FFmpeg输出中提取转码进度
        
        Args:
            output_line: FFmpeg输出行
            
        Returns:
            float: 转码进度百分比，若无法提取则返回-1
        """
        # 匹配FFmpeg输出中的时间信息，格式如：time=00:01:23.45
        time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", output_line)
        if time_match:
            # 计算已转码时间（秒）
            hours = int(time_match.group(1))
            minutes = int(time_match.group(2))
            seconds = float(time_match.group(3))
            total_seconds = hours * 3600 + minutes * 60 + seconds
            
            # 这里简化处理，假设视频时长为10分钟（600秒）
            # 实际应用中应先获取视频时长
            video_duration = 600.0
            progress = (total_seconds / video_duration) * 100
            
            # 确保进度在0-100之间
            progress = max(0, min(100, progress))
            return progress
        
        return -1
    
    def transcode_file(self, input_file, output_file, include_audio=False):
        """
        转码单个视频文件
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
            include_audio: 是否包含音频处理（默认False，保持原有行为）
            
        Returns:
            tuple: (转码成功状态, 错误信息)
        """
        logger.info(f"开始转码文件: {input_file} -> {output_file} (音频处理: {'启用' if include_audio else '禁用'})")
        
        # 重置状态
        self.reset()
        
        # 检查输入文件是否存在
        if not os.path.exists(input_file):
            error_msg = f"输入文件不存在: {input_file}"
            logger.error(f"转码失败: {error_msg}")
            return False, error_msg
        
        # 检查输出目录是否存在，不存在则创建
        output_dir = os.path.dirname(output_file)
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                logger.info(f"创建输出目录: {output_dir}")
            except Exception as e:
                error_msg = f"无法创建输出目录: {output_dir}, {str(e)}"
                logger.error(f"转码失败: {output_dir}, {str(e)}")
                return False, error_msg
        
        try:
            # 构建FFmpeg命令
            command = self.build_ffmpeg_command(input_file, output_file, include_audio)
            
            # 执行FFmpeg命令，使用更低的bufsize并禁用输出缓冲
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding='utf-8',
                errors='ignore',
                bufsize=0,  # 无缓冲模式
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # 读取FFmpeg输出，监控转码进度
            ffmpeg_output = []
            for line in iter(process.stdout.readline, ''):
                # 保存FFmpeg输出，用于错误分析
                ffmpeg_output.append(line.strip())
                
                # 检查是否需要取消转码
                if self.is_cancelled:
                    process.terminate()
                    logger.info(f"转码已取消: {input_file}")
                    return False, "转码已取消"
                
                # 检查是否需要暂停转码
                while self.is_paused:
                    # 暂停时可以添加延迟，减少CPU占用
                    import time
                    time.sleep(0.1)
                
                # 提取转码进度
                progress = self.extract_progress(line)
                if progress >= 0 and self.progress_callback:
                    # 调用进度回调函数
                    self.progress_callback(os.path.basename(input_file), progress)
                
                # 记录FFmpeg输出
                logger.debug(f"FFmpeg输出: {line.strip()}")
            
            # 等待进程结束
            process.wait()
            
            # 检查转码结果
            if process.returncode == 0:
                logger.info(f"转码成功: {input_file} -> {output_file}")
                # 确保进度显示为100%
                if self.progress_callback:
                    self.progress_callback(os.path.basename(input_file), 100.0)
                return True, ""
            else:
                # 保存完整的FFmpeg输出到错误信息
                ffmpeg_output_str = "\n".join(ffmpeg_output)
                error_msg = f"FFmpeg返回错误码: {process.returncode}\n详细输出:\n{ffmpeg_output_str}"
                logger.error(f"转码失败: {input_file} -> {output_file}, {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = f"转码过程中发生错误: {str(e)}"
            logger.error(f"转码失败: {input_file} -> {output_file}, {error_msg}")
            return False, error_msg
    
    def get_output_filename(self, input_file, output_dir):
        """
        生成输出文件名
        
        Args:
            input_file: 输入文件路径
            output_dir: 输出目录路径
            
        Returns:
            str: 输出文件路径
        """
        # 获取输入文件名（不包含扩展名）
        input_filename = os.path.basename(input_file)
        name_without_ext = os.path.splitext(input_filename)[0]
        
        # 生成输出文件名，保留原始时间戳信息
        output_filename = f"{name_without_ext}.mp4"
        output_file = os.path.join(output_dir, output_filename)
        
        logger.debug(f"生成输出文件名: {output_file}")
        return output_file
    
    def get_merged_output_filename(self, output_dir):
        """
        生成合并后的输出文件名
        
        Args:
            output_dir: 输出目录路径
            
        Returns:
            str: 合并后的输出文件路径
        """
        # 生成带时间戳的合并文件名
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"merged_{timestamp}.mp4"
        output_file = os.path.join(output_dir, output_filename)
        
        logger.debug(f"生成合并输出文件名: {output_file}")
        return output_file
    
    def build_merge_command(self, input_files, output_file, include_audio=False):
        """
        构建合并视频的FFmpeg命令
        
        Args:
            input_files: 输入文件列表
            output_file: 输出文件路径
            include_audio: 是否包含音频处理（默认False，保持原有行为）
            
        Returns:
            tuple: (FFmpeg命令列表, 临时文件列表路径)
        """
        # 创建文件列表文件
        file_list_path = output_file + ".txt"
        with open(file_list_path, 'w', encoding='utf-8') as f:
            for file in input_files:
                # 使用绝对路径，避免FFmpeg找不到文件
                abs_path = os.path.abspath(file)
                f.write(f"file '{abs_path}'\n")
        
        # 获取配置参数
        overwrite = self.config_manager.get_config("overwrite")
        video_codec = self.config_manager.get_config("video_codec")
        crf = self.config_manager.get_config("crf")
        audio_codec = self.config_manager.get_config("audio_codec")
        audio_bitrate = self.config_manager.get_config("audio_bitrate")
        
        # 构建FFmpeg合并命令 - 确保合并后的视频支持拖动播放
        command = [
            self.ffmpeg_path,
            "-f", "concat",
            "-safe", "0",
            "-i", file_list_path,
            "-c:v", "libx264",  # 使用标准h.264编码
            "-preset", "fast",
            "-crf", str(crf),
        ]
        
        # 根据include_audio参数决定是否处理音频
        if include_audio:
            # 音频处理参数
            command.extend([
                "-c:a", audio_codec,  # 使用配置的音频编码器
                "-b:a", audio_bitrate,  # 使用配置的音频比特率
            ])
        else:
            # 保持原有行为，禁用音频流
            command.append("-an")  # 禁用音频流
        
        # 继续添加其他参数
        command.extend([
            "-movflags", "faststart",  # 将元数据移到文件头部，支持拖动播放
            "-profile:v", "main",  # 使用main profile确保兼容性
            "-level", "3.0",  # 视频级别，确保广泛兼容
            "-pix_fmt", "yuv420p",  # 使用通用的YUV格式
            "-y" if overwrite else "-n",
            output_file
        ])
        
        logger.debug(f"构建FFmpeg合并命令: {' '.join(command)}")
        return command, file_list_path
    
    def merge_videos(self, input_files, output_file, include_audio=False):
        """
        合并多个视频文件
        
        Args:
            input_files: 输入文件列表
            output_file: 输出文件路径
            include_audio: 是否包含音频处理（默认False，保持原有行为）
            
        Returns:
            tuple: (合并成功状态, 错误信息)
        """
        logger.info(f"开始合并视频文件，共 {len(input_files)} 个文件 -> {output_file} (音频处理: {'启用' if include_audio else '禁用'})")
        
        # 重置状态
        self.reset()
        
        try:
            # 构建FFmpeg合并命令
            command, file_list_path = self.build_merge_command(input_files, output_file, include_audio)
            
            # 执行FFmpeg命令，使用更低的bufsize并禁用输出缓冲
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding='utf-8',
                errors='ignore',
                bufsize=0,  # 无缓冲模式
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # 读取FFmpeg输出
            for line in iter(process.stdout.readline, ''):
                # 检查是否需要取消合并
                if self.is_cancelled:
                    process.terminate()
                    logger.info(f"视频合并已取消")
                    return False, "视频合并已取消"
                
                # 检查是否需要暂停合并
                while self.is_paused:
                    # 暂停时可以添加延迟，减少CPU占用
                    import time
                    time.sleep(0.1)
                
                # 记录FFmpeg输出
                logger.debug(f"FFmpeg合并输出: {line.strip()}")
            
            # 等待进程结束
            process.wait()
            
            # 删除临时文件列表
            if os.path.exists(file_list_path):
                os.remove(file_list_path)
            
            # 检查合并结果
            if process.returncode == 0:
                logger.info(f"视频合并成功: {output_file}")
                return True, ""
            else:
                error_msg = f"FFmpeg返回错误码: {process.returncode}"
                logger.error(f"视频合并失败: {output_file}, {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = f"视频合并过程中发生错误: {str(e)}"
            logger.error(f"视频合并失败: {output_file}, {error_msg}")
            return False, error_msg