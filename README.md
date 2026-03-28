# PodScribe

小宇宙播客转文字工具。输入播客链接，自动提取音频并转录为文本。

支持 TXT 纯文本和 SRT 字幕格式输出，可选 AI 后处理（自动加标点、分段）。

## 前置要求

- macOS / Linux / Windows
- Python 3.10+
- 阿里云 DashScope API Key（[点此获取](https://bailian.console.aliyun.com/)）
- 默认输出目录：`~/PodScribe`

如果没有 Python 3.10+，先按平台安装：

```bash
# macOS
brew install python@3.12

# Linux
sudo apt install python3

# Windows
# 从 python.org 下载并安装最新版 Python
```

## 安装步骤

全局安装（推荐，适合直接使用命令）：

```bash
# macOS
brew install pipx

# Linux
sudo apt install pipx
# 或
python3 -m pip install --user pipx

# Windows
python -m pip install --user pipx

# 所有平台
pipx install git+https://github.com/tens1x/podscribe.git
```

安装完成后直接运行：

```bash
podscribe
```

如果想直接打开桌面窗口版：

```bash
podscribe-gui
# 或
podscribe gui
```

注意：当前桌面窗口版基于 Python 内置 `tkinter`，不额外引入大型 GUI 依赖。macOS / Windows 上建议使用带 Tk 支持的 Python 发行版。

首次运行 `podscribe` 时会引导你配置 API Key。

`setup.sh` 仅适用于 macOS / Linux。Windows 用户请使用上面的 `pipx` 安装方式。

<details>
<summary>开发者 / 手动安装（适合需要改代码的贡献者）</summary>

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

安装后直接运行：

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

## 子命令

除了直接运行交互式主流程，也支持以下子命令：

```bash
podscribe config
podscribe history
```

- `podscribe config`：查看或修改当前配置
- `podscribe history`：查看历史转录记录

## 功能特性

- 交互式 CLI 界面（上下选择、多选、彩色输出）
- 最小桌面窗口入口（适合逐步演进为 macOS app）
- 支持 TXT 和 SRT 两种输出格式
- AI 后处理（自动标点、分段，基于通义千问）
- 任务中断自动恢复
- 首次运行引导配置

## 用完退出虚拟环境

```bash
deactivate
```

如果你使用的是上面的 `pipx` 全局安装方式，则不需要激活或退出虚拟环境。
