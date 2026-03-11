# podcast-transform-

小宇宙播客转文字工具。输入播客链接，自动提取音频并转录为文本。

## 前置要求

- macOS / Linux / Windows
- Python 3.8+
- 阿里云 DashScope API Key（[点此获取](https://bailian.console.aliyun.com/)）

macOS 如果没有 Python 3，先安装：

```bash
brew install python3
```

## 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/tens1x/podcast-transform-.git
cd podcast-transform-

# 2. 创建虚拟环境
python3 -m venv venv

# 3. 激活虚拟环境
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 配置 API Key
echo 'DASHSCOPE_API_KEY=你的key替换到这里' > .env
```

## 使用方法

每次使用前先激活虚拟环境：

```bash
cd podcast-transform-
source venv/bin/activate
```

基本用法：

```bash
python main.py "https://www.xiaoyuzhoufm.com/episode/你的播客链接"
```

可选参数：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-o, --output-dir` | 输出目录 | `output` |
| `-l, --language` | 语言提示 | `zh` |
| `--save-audio` | 同时保存音频文件 | 不保存 |

示例：

```bash
# 转录并保存音频
python main.py "https://www.xiaoyuzhoufm.com/episode/xxxxx" --save-audio

# 指定输出目录和语言
python main.py "https://www.xiaoyuzhoufm.com/episode/xxxxx" -o transcripts -l en
```

转录结果会保存在输出目录下的 `.txt` 文件中。

## 用完退出虚拟环境

```bash
deactivate
```
