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
        # 修复：修改输入格式检测方式，使用更通用的参数来处理裸流
        command = [
            self.ffmpeg_path,
            # 输入参数
            # 修改：不强制指定输入格式，让FFmpeg自动检测
            # 增加更宽松的分析参数以处理可能不标准的裸流
            "-analyzeduration", "20M",  # 进一步增加分析时间
            "-probesize", "20M",  # 进一步增加缓冲区大小
            "-fflags", "+genpts+igndts",  # 生成显示时间戳并忽略DTS错误
            "-err_detect", "ignore_err",  # 忽略解码错误，尝试继续处理
            "-i", input_file,
            # 视频编码参数
            "-c:v", "libx264",  # 使用标准h.264编码，确保通用性
            "-preset", "fast",  # 快速编码预设
            "-crf", str(crf),  # 视频质量参数
            # 添加更多容错参数
            "-tune", "zerolatency",  # 低延迟模式，有助于处理问题流
            "-x264opts", "keyint=25:min-keyint=25:no-scenecut",  # 固定关键帧间隔
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
                "-level", "4.0",  # 提高级别以支持更高分辨率
                "-pix_fmt", "yuv420p",  # 使用通用的YUV格式
                # MP4封装参数
                "-movflags", "faststart",  # 将元数据移到文件头部，支持拖动播放
                # 输出参数
                "-y" if overwrite else "-n",
                # 添加严格实验性功能支持（处理非标准流）
                "-strict", "experimental",
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
            logger.debug(f"转码进度: {progress:.1f}%")
            return progress
        
        # 检查是否有错误信息，但不要对所有错误都警告，只对严重错误警告
        # 对于一些非致命错误，FFmpeg可能仍能继续处理
        error_keywords = ["error:", "failed:", "could not", "unable to", "no start code", "invalid data"]
        if any(keyword in output_line.lower() for keyword in error_keywords):
            logger.warning(f"FFmpeg警告/错误: {output_line.strip()}")
            
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
            # 确保命令列表中的路径正确处理，尤其是带空格的路径
            # subprocess会自动处理命令列表中的空格，不需要额外引号
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
                
                # 检查是否有重要的FFmpeg消息
                if "frame=" in line or "size=" in line or "bitrate=" in line:
                    logger.debug(f"FFmpeg输出: {line.strip()}")
                
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
                logger.debug(f"转码完成输出:\n" + "\n".join(ffmpeg_output[-10:]))
                # 确保进度显示为100%
                if self.progress_callback:
                    self.progress_callback(os.path.basename(input_file), 100.0)
                return True, ""
            else:
                # 分析错误原因，从FFmpeg输出中查找错误信息
                error_lines = [line for line in ffmpeg_output if any(err in line.lower() for err in ["error", "failed", "could not", "unable to"])]
                error_msg = f"FFmpeg转码失败，返回码: {process.returncode}"
                if error_lines:
                    # 添加最相关的错误信息
                    error_msg += f"\n错误详情: {error_lines[-1]}"
                logger.error(f"转码失败: {input_file} -> {output_file}, {error_msg}")
                # 记录详细的FFmpeg输出
                logger.debug(f"FFmpeg详细输出:\n" + "\n".join(ffmpeg_output[-50:]))
                return False, error_msg
                
        except subprocess.SubprocessError as e:
            # 捕获子进程相关错误，提供更详细信息
            error_msg = f"FFmpeg进程错误: {str(e)}"
            logger.error(f"转码失败: {input_file} -> {output_file}, {error_msg}")
            return False, error_msg
        except UnicodeDecodeError as e:
            # 处理编码错误
            error_msg = f"输出解码错误: {str(e)}"
            logger.error(f"转码失败: {input_file} -> {output_file}, {error_msg}")
            return False, error_msg
        except KeyboardInterrupt:
            # 处理用户中断
            if process:
                process.terminate()
            error_msg = "用户中断操作"
            logger.info(f"转码中断: {input_file} -> {output_file}, {error_msg}")
            return False, error_msg
        except Exception as e:
            # 捕获其他所有异常
            error_msg = f"转码过程中发生异常: {str(e)}"
            logger.error(f"转码失败: {input_file} -> {output_file}, {error_msg}", exc_info=True)  # 记录完整堆栈
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
                # 在Windows上使用双引号确保路径正确解析
                f.write(f"file \"{abs_path}\"\n")
        
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
        file_list_path = None
        
        # 检查输入文件列表是否为空
        if not input_files:
            error_msg = "合并失败: 输入文件列表为空"
            logger.error(error_msg)
            return False, error_msg
        
        # 检查所有输入文件是否存在和文件大小
        valid_files = []
        invalid_files = []
        for input_file in input_files:
            if os.path.exists(input_file):
                if os.path.getsize(input_file) > 0:
                    valid_files.append(input_file)
                else:
                    invalid_files.append(f"{input_file} (文件大小为0)")
            else:
                invalid_files.append(f"{input_file} (文件不存在)")
        
        if invalid_files:
            error_msg = f"合并失败: 以下文件无效:\n" + "\n".join(invalid_files)
            logger.error(error_msg)
            return False, error_msg
        
        # 检查输出目录是否存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                logger.info(f"创建输出目录: {output_dir}")
            except Exception as e:
                error_msg = f"无法创建输出目录: {output_dir}, {str(e)}"
                logger.error(f"合并失败: {error_msg}")
                return False, error_msg
        
        try:
            # 构建FFmpeg合并命令
            command, file_list_path = self.build_merge_command(valid_files, output_file, include_audio)
            
            # 执行FFmpeg命令，使用更低的bufsize并禁用输出缓冲
            # 确保命令列表中的路径正确处理，尤其是带空格的路径
            # subprocess会自动处理命令列表中的空格，不需要额外引号
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
            
            # 读取FFmpeg输出并保存以供错误分析
            output_lines = []
            for line in iter(process.stdout.readline, ''):
                line_content = line.strip()
                output_lines.append(line_content)
                
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
                
                # 只记录重要的FFmpeg输出信息，避免日志过大
                if any(keyword in line_content.lower() for keyword in ["frame", "size", "bitrate", "error", "failed", "warning"]):
                    logger.debug(f"FFmpeg合并输出: {line_content}")
            
            # 等待进程结束
            process.wait()
            
            # 删除临时文件列表
            if os.path.exists(file_list_path):
                os.remove(file_list_path)
            
            # 检查合并结果
            if process.returncode == 0 and os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                logger.info(f"视频合并成功: {output_file} (文件大小: {file_size/1024/1024:.2f} MB)")
                logger.debug(f"合并完成输出:\n" + "\n".join(output_lines[-10:]))
                return True, ""
            else:
                # 分析错误原因
                error_lines = [line for line in output_lines if any(err in line.lower() for err in ["error", "failed", "could not", "unable to"])]
                error_msg = f"FFmpeg返回错误码: {process.returncode}"
                if error_lines:
                    error_msg += f"\n错误详情: {error_lines[-1]}"
                
                # 检查输出文件是否存在但可能不完整
                if os.path.exists(output_file):
                    error_msg += f"\n输出文件已创建但可能不完整: {output_file}"
                
                logger.error(f"视频合并失败: {output_file}, {error_msg}")
                logger.debug(f"FFmpeg合并详细输出:\n" + "\n".join(output_lines[-50:]))
                return False, error_msg
                
        except subprocess.SubprocessError as e:
            error_msg = f"FFmpeg进程错误: {str(e)}"
            logger.error(f"视频合并失败: {output_file}, {error_msg}")
            return False, error_msg
        except UnicodeDecodeError as e:
            error_msg = f"输出解码错误: {str(e)}"
            logger.error(f"视频合并失败: {output_file}, {error_msg}")
            return False, error_msg
        except KeyboardInterrupt:
            if process:
                process.terminate()
            error_msg = "用户中断合并操作"
            logger.info(f"视频合并中断: {output_file}, {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"视频合并过程中发生异常: {str(e)}"
            logger.error(f"视频合并失败: {output_file}, {error_msg}", exc_info=True)  # 记录完整堆栈
            return False, error_msg
        finally:
            # 确保临时文件被清理
            if file_list_path and os.path.exists(file_list_path):
                try:
                    os.remove(file_list_path)
                    logger.debug(f"已删除临时文件列表: {file_list_path}")
                except Exception as e:
                    logger.warning(f"无法删除临时文件列表: {file_list_path}, {str(e)}")