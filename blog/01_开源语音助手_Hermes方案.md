# 用 Hermes Agent + Whisper + Edge-TTS 搭建纯开源家庭语音助手

## 前言

想在家里搞一个语音助手，不想用小爱/Alexa 那些云端方案（隐私、定制性差），于是用纯开源组件自己搓了一个。整套方案零成本（除了硬件），全部跑在自己的服务器上。

## 架构

```
麦克风 → VAD检测 → Whisper(STT) → Hermes Agent(LLM) → Edge-TTS → 音响播放
```

每个环节都是独立的开源组件，可以单独替换。

## 硬件

- 一台 Linux 服务器（i5-12400 + 32GB，无 GPU）
- USB 无线麦克风（Hollyland 猛犸系列）
- 3.5mm 有线音响
- 总成本：利用家里现有设备，零额外采购

## 技术栈

| 环节 | 方案 | 说明 |
|------|------|------|
| 语音唤醒 | openWakeWord | 开源唤醒词检测，CPU 跑，支持自定义 |
| 语音活动检测 | 自写 VAD | 基于音量阈值，简单有效 |
| 语音识别 (STT) | faster-whisper (small) | OpenAI Whisper 的优化版，本地 CPU 跑 |
| 大语言模型 | Hermes Agent + DeepSeek | 自托管 AI Agent，带记忆和技能系统 |
| 语音合成 (TTS) | Edge-TTS | 微软免费 TTS，音质好，支持多种中文声音 |
| 音频播放 | ALSA (aplay) | Linux 原生音频 |

## 核心代码结构

```
voice-assistant/
├── main.py          # 主程序（录音→STT→LLM→TTS→播放）
├── config.yaml      # 配置文件
└── run.sh           # 启动脚本
```

## 工作流程

1. **唤醒**：openWakeWord 持续监听，检测到唤醒词（如 "Alexa"）后激活
2. **录音**：VAD 检测到说话开始录音，静音 3 秒后停止
3. **识别**：faster-whisper 将音频转为文字（~1秒）
4. **对话**：发送文字给 Hermes Agent（OpenAI 兼容 API），获取回复
5. **合成**：Edge-TTS 将回复文字转为语音（~1.5秒）
6. **播放**：aplay 通过 ALSA 播放到音响

## 关键实现细节

### VAD（语音活动检测）

```python
def record_with_vad(device_idx):
    """检测到说话开始录，静音后停止"""
    with sd.InputStream(samplerate=48000, channels=1, dtype="int16", device=device_idx) as stream:
        while True:
            chunk, _ = stream.read(chunk_samples)
            rms = np.sqrt(np.mean(chunk.astype(np.float32) ** 2))
            
            if not is_recording and rms > ENERGY_THRESHOLD:
                is_recording = True  # 开始录音
            elif is_recording and rms < ENERGY_THRESHOLD:
                if silence_duration >= 3.0:
                    break  # 停止录音
```

### 对接 Hermes Agent

```python
def chat_with_hermes(user_text):
    """标准 OpenAI 兼容 API 调用"""
    payload = {
        "model": "deepseek-v4-pro",
        "messages": conversation_history,
    }
    resp = requests.post(
        "http://localhost:8642/v1/chat/completions",
        json=payload,
        headers={"Authorization": f"Bearer {API_KEY}"},
    )
    return resp.json()["choices"][0]["message"]["content"]
```

### Edge-TTS 语音合成

```python
async def text_to_speech(text, output_path):
    communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
    await communicate.save(output_path)
```

## 优缺点

**优点：**
- ✅ 完全免费（Edge-TTS 免费，Whisper 本地跑）
- ✅ 隐私安全（语音数据不出局域网，LLM 自托管）
- ✅ 高度可定制（每个组件可独立替换）
- ✅ 无 GPU 要求（i5 CPU 足够）
- ✅ 对接自己的 AI Agent（Hermes 带记忆/技能）

**缺点：**
- ❌ 延迟较高（说完到回复约 4-8 秒）
- ❌ 唤醒词体验一般（openWakeWord 英文词为主）
- ❌ 本地 Whisper 中文识别准确率有限（base/small 模型）
- ❌ 无法打断（半双工，播放时不监听）
- ❌ 需要自己维护多个组件

## 适用场景

- 对隐私要求高的用户
- 想对接自己的 LLM/Agent 的开发者
- 预算为零但有服务器的折腾党
- 学习语音助手架构的入门项目

## 后续优化方向

- 替换 Whisper 为火山引擎 ASR（准确率大幅提升）
- 替换 Edge-TTS 为火山引擎 TTS（支持方言、情感）
- 加入 VAD + Whisper 实现自定义中文唤醒词
- 接入 ESP32 做无线麦克风终端
