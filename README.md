# PodScribe

小宇宙播客转文字工具。输入播客链接，自动提取音频并转录为文本。

- 语音识别：Qwen3-ASR（阿里通义千问语音大模型）
- 输出格式：TXT 纯文本 / SRT 带时间戳字幕
- AI 后处理：自动加标点、分段（基于通义千问 LLM）

## 前置要求

- macOS / Linux / Windows
- Python 3.10+
- 阿里云百炼平台 API Key

### 获取 API Key

1. 打开 [百炼控制台](https://bailian.console.aliyun.com/)，注册/登录阿里云账号
2. 进入 [API-KEY 管理](https://bailian.console.aliyun.com/#/api-key)
3. 创建 API Key（选择北京地域）

> API Key 以 `sk-` 开头。同一个 Key 同时用于语音识别（Qwen3-ASR）和 AI 后处理（Qwen LLM），无需分别申请。
>
> Key 存储在本地配置文件 `~/.config/podscribe/config.json` 中，不会上传到任何第三方服务。

## 安装

```bash
# 1. 安装 pipx（如果还没装）
brew install pipx        # macOS
sudo apt install pipx    # Linux
python -m pip install --user pipx  # Windows

# 2. 安装 PodScribe
pipx install git+https://github.com/tens1x/podcast-transform-.git
```

## 使用

```bash
podscribe
```

首次运行会引导你配置 API Key。之后进入交互式界面：

```
╭───────────────────────────────────────╮
│  🎙  PodScribe  v0.1.0               │
│  Podcast → Text, powered by AI       │
│                                       │
│  Format: txt + srt                    │
│  Output: ~/PodScribe                  │
│  AI post: on                          │
╰───────────────────────────────────────╯
? What would you like to do?
› Start transcription
  Edit config
  View history
  Quit
```

### 转写流程

1. 选择 **Start transcription**
2. 粘贴小宇宙播客链接（支持多个，逗号分隔）
3. 自动完成：解析页面 → 转写音频 → AI 润色 → 保存文件

### 子命令

```bash
podscribe config    # 直接进入设置
podscribe history   # 查看历史记录
```

## 功能特性

| 功能 | 说明 |
|------|------|
| 语音转文字 | Qwen3-ASR，支持中文（含方言）、英语等多语种 |
| SRT 字幕 | 带句级时间戳，可直接用于视频字幕 |
| AI 后处理 | 自动修标点、去语气词、分段落 |
| 批量转写 | 一次粘贴多个链接，依次转写 |
| 断点续传 | 中断后再次运行可恢复上次任务 |
| 音频下载 | 可选保存原始音频文件到指定目录 |
| 交互式界面 | 上下箭头选择、空格多选、彩色输出 |

## 配置项

在 **Edit config** 菜单中可修改：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| Output formats | txt + srt | 选择输出 TXT、SRT 或两者 |
| Save audio | off | 是否保存原始音频文件 |
| Audio directory | ~/PodScribe/audio | 音频保存路径 |
| AI post-process | on | 是否用 LLM 润色转写结果 |
| Output directory | ~/PodScribe | 转写结果保存路径 |

## 安全说明

- API Key 仅存储在本地 `~/.config/podscribe/config.json`
- 所有 API 调用通过 HTTPS 加密传输
- 音频文件 URL 由百炼平台处理，不经过第三方
- `.gitignore` 已排除 `.env` 和配置文件，不会意外提交密钥

## 开发

```bash
git clone https://github.com/tens1x/podcast-transform-.git
cd podcast-transform-
pip install -e .
podscribe
```
