# 家庭语音助手

用 Linux 服务器 + USB 麦克风 + 有线音响，搭了一个家庭语音助手。两套方案都跑通了，目前主力用 voice-doubao（火山引擎端到端实时语音）。

## 项目结构

```
├── voice-doubao/     火山引擎端到端实时语音（主力方案，已部署，永久运行）
├── voice-hermes/     全开源方案，对接 Hermes Agent（备用，可扩展）
├── esp32/            ESP32-S3 无线麦克风终端（规划中）
└── blog/             搭建过程踩坑博客
```

## voice-doubao（主力方案）

火山引擎"豆包端到端实时语音大模型"，一个 WebSocket 搞定听+想+说。体验很好，但**价格要注意**。

**体验**：
- 延迟 <1 秒，接近真人对话节奏
- 支持陕西话/四川话/东北话方言
- 支持打断（你说话它立刻闭嘴）
- 无需唤醒词，直接说话
- 断线自动重连，systemd 永久运行

**踩坑完善**：
- 修复了 aplay 播放进程假死/Broken pipe 问题（看门狗自动重建）
- 配置了 udev 规则，麦克风热插拔自动恢复服务
- 解决了 ALSA Auto-Mute、systemd 音频权限等一系列坑
- 详见 [TROUBLESHOOTING.md](voice-doubao/TROUBLESHOOTING.md)

### 计费（血泪教训）

端到端模型按 token 计费，不同类型价格差异巨大：

| token 类型 | 单价 (元/token) | 说明 |
|-----------|----------------|------|
| **输出-音频** | **¥0.0003** | 最贵！模型回复的语音 |
| 输入-音频 | ¥0.00008 | 麦克风推的音频 |
| 输出-文本 | ¥0.00008 | 模型回复的文字部分 |
| 输入-文本 | ¥0.00001 | 上下文历史 |
| cached | ¥0.000005 | 缓存命中 |

**实测**：一下午随意用（~70 轮对话），**花了 ¥57**。其中 61% 烧在输出音频上。

**为什么这么贵**：
1. 没有唤醒词，家里小孩/电视一直在触发对话，白烧 token
2. 输出音频单价是输入文本的 30 倍，模型每回复一句话都很贵

**建议**：不用的时候 `voice stop` 关掉。后续计划加唤醒词门禁止血。

## voice-hermes（备用方案）

全开源组件：Whisper + Hermes Agent + Edge-TTS。免费但体验一般。

- 延迟 4-8 秒
- 中文识别准确率 70%，方言基本不行
- 优势：能接自己的 LLM、有持久记忆、数据不出门

## 两套方案对比

| | voice-doubao | voice-hermes |
|--|--|--|
| 延迟 | <1 秒 | 4-8 秒 |
| 识别准确率 | 95%（懂方言） | 70-80% |
| 唤醒 | 无（VAD 直接触发） | 唤醒词 |
| 打断 | 支持 | 不支持 |
| LLM | 火山模型（黑盒） | 自选（Hermes/DeepSeek） |
| 成本 | **贵（一下午57元）** | 全免费 |
| 隐私 | 音频上云 | 基本内网 |
| 适合 | 体验优先、偶尔用 | 成本优先、长期挂 |

## 硬件需求

- Linux 服务器（CPU 即可，无 GPU）
- USB 麦克风（我用的猛犸无线麦）
- 3.5mm 有线音响

## 快速开始

```bash
# 克隆
git clone https://github.com/ladydd/home-voice-assistant.git
cd home-voice-assistant

# 安装依赖
pip install websockets sounddevice numpy
sudo apt-get install -y alsa-utils

# 配置火山引擎凭证
export VOLC_APP_ID="your-app-id"
export VOLC_ACCESS_KEY="your-access-key"

# 运行
cd voice-doubao
python main.py
```

详细部署、配置和排查见各子目录的 README 和 TROUBLESHOOTING。

## 博客

- [折腾记（一）：全开源方案](blog/01_开源语音助手_Hermes方案.md)
- [折腾记（二）：火山引擎实时语音](blog/02_豆包端到端实时语音助手.md)

## License

MIT
