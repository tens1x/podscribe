# PodScribe

小宇宙播客转文字工具。输入播客链接，自动提取音频并转录为文本。

支持 TXT 纯文本和 SRT 字幕格式输出，可选 AI 后处理（自动加标点、分段）。

## 前置要求

- macOS / Linux / Windows
- Python 3.10+
- 阿里云 DashScope API Key（[点此获取](https://bailian.console.aliyun.com/)）

macOS 如果没有 Python 3.10+，先安装：

```bash
brew install python@3.12
```

## 安装步骤

一键安装（推荐）：

```bash
git clone https://github.com/tens1x/podscribe.git
cd podscribe
bash setup.sh
```

脚本会自动创建虚拟环境、安装依赖、引导你配置 API Key，完成后会提示如何运行。

<details>
<summary>手动安装</summary>

```bash
git clone https://github.com/tens1x/podscribe.git
cd podscribe
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

首次运行 `podscribe` 时会引导你配置 API Key。

</details>

## 使用方法

每次使用前先激活虚拟环境：

```bash
cd podscribe
source venv/bin/activate
```

然后运行：

```bash
podscribe
```

程序会通过交互式界面引导你完成以下步骤：

1. 粘贴小宇宙播客链接
2. 选择是否保存音频文件
3. 选择输出格式（TXT / SRT / 两者都要）
4. 选择是否启用 AI 后处理
5. 设置输出目录

支持上下箭头选择、空格多选，操作体验类似现代 CLI 工具。

## 功能特性

- 交互式 CLI 界面（上下选择、多选、彩色输出）
- 支持 TXT 和 SRT 两种输出格式
- AI 后处理（自动标点、分段，基于通义千问）
- 任务中断自动恢复
- 首次运行引导配置

## 用完退出虚拟环境

```bash
deactivate
```
