# H264ToMP4 - 海雀监控视频转码工具

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![Release](https://img.shields.io/badge/release-1.0.0-green.svg)](https://github.com/yourusername/H264ToMP4/releases)

## 项目简介

H264ToMP4是一个专门用于将海雀监控摄像头录制的.v264格式视频文件转换为标准MP4格式的工具。转换后的MP4文件可以在各种主流播放器和设备上播放，支持进度条拖动。

![应用截图](https://github.com/yourusername/H264ToMP4/raw/main/resources/screenshot.png)

## 功能特点

- 🎥 **批量转码**：支持一次性处理整个目录中的所有.v264文件
- ⚡ **多线程处理**：利用多核CPU加速转码过程
- 🔗 **视频合并**：可将多个视频片段合并为一个完整的视频文件
- 🎵 **音频处理**：可选择是否保留并转码音频流
- 📊 **进度监控**：实时显示转码进度和状态
- ⏸️ **任务控制**：支持暂停、继续、取消和重试失败任务
- 💾 **配置保存**：自动保存用户偏好设置
- 📝 **日志记录**：详细的操作日志，便于问题排查

## 快速开始

### 下载安装

1. 从[GitHub Releases](https://github.com/yourusername/H264ToMP4/releases)下载最新版本
2. 解压到任意目录（建议使用英文路径）
3. 双击运行`H264ToMP4.exe`即可使用

### 基本使用

1. 选择包含.v264文件的源目录
2. 选择输出目录（可选，默认为源目录下的converted子目录）
3. 点击"扫描目录"按钮列出所有视频文件
4. 配置选项（如需要）
5. 点击"开始转码"按钮开始处理

## 系统要求

- 操作系统：Windows 7/8/10/11 (64位)
- 内存：4GB以上推荐
- 硬盘：至少有源文件大小2倍的可用空间
- CPU：多核CPU推荐，以提高转码速度

## 技术架构

- **开发语言**：Python 3.7+
- **GUI框架**：tkinter
- **视频处理**：FFmpeg
- **多线程处理**：concurrent.futures
- **日志记录**：logging

## 项目结构

```
H264ToMP4/
├── core/                # 核心功能模块
│   ├── file_manager.py  # 文件管理模块
│   ├── config_manager.py # 配置管理模块
│   ├── transcode_engine.py # 转码引擎模块
│   └── task_manager.py  # 任务管理模块
├── gui/                 # GUI界面模块
│   └── main_window.py   # 主窗口类
├── utils/               # 工具模块
│   ├── logger.py        # 日志管理模块
│   └── error_handler.py # 错误处理模块
├── resources/           # 资源目录
├── config.json          # 配置文件
├── main.py              # 主程序入口
├── requirements.txt     # Python依赖
├── CHANGELOG.md         # 更新日志
├── LICENSE              # 许可证
└── README.md            # 项目说明文档
```

## 配置说明

配置文件为`config.json`，主要配置项包括：

```json
{
    "source_dir": "",
    "output_dir": "converted",
    "ffmpeg_path": "ffmpeg.exe",
    "video_codec": "libx264",
    "crf": 18,
    "audio_codec": "aac",
    "audio_bitrate": "128k",
    "threads": 4,
    "overwrite": false,
    "keep_original": true,
    "log_level": "INFO",
    "include_audio": false
}
```

## 常见问题

### Q: 转码后的视频无法播放？
A: 请确保使用的是最新版本的播放器，如VLC、PotPlayer等。如果仍然无法播放，请检查日志文件查看可能的错误信息。

### Q: 转码速度很慢怎么办？
A: 可以尝试增加配置文件中的threads数值，但不要超过CPU核心数。同时确保硬盘有足够的读写速度。

### Q: 如何合并多个视频片段？
A: 在界面上勾选"合并为一个视频"选项，程序会按文件名中的时间戳顺序合并所有视频片段。

## 开发指南

### 环境搭建

1. 克隆仓库：
   ```
   git clone https://github.com/yourusername/H264ToMP4.git
   cd H264ToMP4
   ```

2. 创建虚拟环境（推荐）：
   ```
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

4. 运行程序：
   ```
   python main.py
   ```

### 构建可执行文件

使用PyInstaller打包：

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=resources/app.ico main.py
```

## 贡献指南

欢迎提交Issue和Pull Request！请确保：

1. 代码符合项目编码规范
2. 添加必要的测试和文档
3. 提交信息清晰明确

## 更新日志

详见[CHANGELOG.md](CHANGELOG.md)

## 许可证

本项目采用MIT许可证，详见[LICENSE](LICENSE)文件。

## 致谢

感谢FFmpeg项目提供的强大视频处理能力，以及所有为本项目做出贡献的开发者。

## 联系方式

- 邮箱：your_email@example.com
- GitHub：https://github.com/yourusername/H264ToMP4
- Issues：https://github.com/yourusername/H264ToMP4/issues