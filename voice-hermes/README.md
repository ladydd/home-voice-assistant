# voice-hermes

全开源家庭语音助手，对接任意 OpenAI 兼容 LLM（Hermes Agent / DeepSeek / Ollama 等）。

## 特点

- 🔓 数据可控，LLM 自选（隐私友好）
- 🧠 可对接带记忆的 AI Agent（如 Hermes Agent）
- 🎯 唤醒词 + VAD 触发
- 🔧 每个模块可独立替换（STT / LLM / TTS）
- 🆓 纯开源方案零成本可用（Whisper + Edge-TTS）
- 🗣️ 支持火山引擎 ASR/TTS 升级（更准、支持方言）

## 架构

```
唤醒词 → VAD录音 → STT(语音转文字) → LLM(对话) → TTS(文字转语音) → 音响播放
```

每个环节独立，通过 `config.yaml` 切换不同方案。

## 技术栈选项

| 环节 | 免费方案 | 付费方案（更好） |
|------|---------|----------------|
| 唤醒 | openWakeWord (alexa/hey_jarvis) | — |
| STT | faster-whisper (本地) | 火山引擎 Seed-ASR |
| LLM | Hermes Agent / Ollama | DeepSeek API / 任意 OpenAI 兼容 |
| TTS | Edge-TTS (微软免费) | 火山引擎 TTS (支持方言) |

## 前提

- Linux 服务器（CPU 即可，无 GPU 要求）
- USB 麦克风
- 有线音响（3.5mm）
- 一个 OpenAI 兼容的 LLM API（本地或远程）

## 安装

```bash
# Python 依赖
pip install sounddevice numpy requests pyyaml edge-tts faster-whisper openwakeword

# 系统音频工具
sudo apt-get install -y alsa-utils pulseaudio ffmpeg

# 用户加入 audio 组
sudo usermod -aG audio $USER
```

## 配置

复制并修改配置文件：

```bash
cp config.yaml config.yaml  # 修改里面的 API 地址和密钥
```

关键配置项：

```yaml
# LLM 接口（改成你自己的）
hermes:
  url: "http://localhost:8642/v1/chat/completions"
  api_key: "your-api-key"
  model: "deepseek-v4-pro"

# STT 选择
stt:
  provider: "whisper"  # 或 "volcengine"

# TTS 选择
tts:
  provider: "edge"  # 或 "volcengine" 或 "piper"
```

## 运行

```bash
# 需要 audio 组权限
sg audio -c 'python main.py'
```

## 工作流程

1. openWakeWord 持续监听唤醒词（如 "Alexa"）
2. 检测到唤醒词 → 播放提示音
3. VAD 检测说话，开始录音
4. 静音 3 秒 → 停止录音
5. STT 转文字 → 发给 LLM → 获取回复
6. TTS 合成语音 → 播放
7. 回到步骤 1

## 对接不同 LLM

本项目通过标准 OpenAI chat completions 接口对接 LLM，可接：

- **Hermes Agent**：自托管 AI Agent，带持久记忆和技能系统
- **Ollama**：本地跑开源模型（Llama/Qwen 等）
- **DeepSeek API**：直接调 DeepSeek
- **OpenAI API**：调 GPT 系列
- 任何 OpenAI 兼容的接口

只需修改 `config.yaml` 中的 `url` 和 `api_key`。

## 已知限制

- 延迟较高（说完到回复约 4-8 秒）
- 唤醒词目前仅英文（alexa / hey_jarvis）
- Whisper small 中文识别约 70-80 分
- 半双工，播放时不监听（无法打断）

## 后续可扩展

- [ ] HTTP 接口（支持外部主动推送提醒）
- [ ] 自定义中文唤醒词
- [ ] ESP32 无线麦克风终端
- [ ] 日程提醒 / 智能家居联动

## License

MIT
