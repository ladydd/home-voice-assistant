# 折腾记（一）：用全开源组件给家里搭一个语音助手，对接自己的 Hermes Agent

## 起因

事情是从一块 ESP32-S3 开发板开始的。

我手上有一块 Seeed Studio XIAO ESP32-S3 Sense，带摄像头和麦克风。最初的想法很美好：用这块板子做一个无线语音终端，对着它说话，连到我服务器上跑的 Hermes Agent（一个自托管的 AI agent），让它回答我。

但折腾到一半我突然意识到一件事：**我的麦克风、音响、服务器全在家里，为什么要绕一圈用 ESP32？直接把麦克风和音响插到服务器上不就行了？**

ESP32 那条路（做无线拾音终端）当然也有价值，但那是"为了学嵌入式而学"，不是解决问题的最短路径。于是这个项目就从"嵌入式项目"变成了"在服务器上拼一个语音助手"。这篇就记录后者。

> 教训零：先想清楚你要解决的是什么问题。很多时候最优解比你最初设想的简单得多。

## 目标

- 对着麦克风说话
- 服务器识别成文字，发给我的 Hermes Agent（背后是 DeepSeek）
- Agent 的回复用语音播放出来
- 全部用开源/免费组件，数据不出家门

## 硬件（全是现成的，零采购）

| 设备 | 型号 | 作用 |
|------|------|------|
| 服务器 | 家里的 i5-12400 + 32GB，**无独显** | 跑所有东西 |
| 麦克风 | Hollyland 猛犸系列无线麦（USB 接收器） | 拾音 |
| 音响 | 普通有线音响，3.5mm | 出声 |

服务器是台 Ubuntu，平时跑着一堆 docker（爬虫、数据库之类），顺便挂语音助手。

## 整体链路

```
麦克风 → VAD检测 → STT(语音转文字) → Hermes Agent(LLM) → TTS(文字转语音) → 音响
```

五个环节，每个都是可替换的独立模块。下面按真实的踩坑顺序讲。

---

## 第一步：环境，第一个坑就来了

服务器是 Ubuntu 24.04，Python 3.12。想装 esptool 和 pyserial，直接 `pip install` 就报错：

```
error: externally-managed-environment
```

这是新版 Python 的 PEP 668 保护，不让你往系统 Python 里乱装包。解决办法就是老老实实建虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install ...
```

后面所有 Python 依赖都装在 venv 里，干净不污染系统。

## 第二步：让音响先出声

在搞复杂的之前，我想先确认音响能响。装基础音频工具：

```bash
sudo apt-get install -y alsa-utils pulseaudio ffmpeg
```

然后用一段 TTS 生成的测试音频去播：

```bash
aplay -D plughw:0,0 test.wav
```

**没声音。**

排查发现两个问题：

1. **用户不在 audio 组** — `/dev/snd/` 下的设备属于 audio 组，普通用户访问不了。
   ```bash
   sudo usermod -aG audio $USER
   ```
   注意加完组要重新登录才生效，或者用 `sg audio -c '命令'` 临时切换组来测试。

2. **Auto-Mute Mode 在捣鬼** — 主板声卡有个"自动静音"功能，插了某个口就把其他口静音了。我的音响插在后面的 3.5mm，被自动静音了。关掉它：
   ```bash
   amixer -c 0 set "Auto-Mute Mode" Disabled
   amixer -c 0 set Master 100% unmute
   amixer -c 0 set Front 100% unmute
   ```

搞定这两个，音响终于响了。

> 教训一：音频问题，先用 `aplay -l` / `arecord -l` 确认设备，再查权限和静音设置。Linux 音频的坑大多在这两块。

## 第三步：TTS（文字转语音）

TTS 我对比了两个方案：

**Edge-TTS（微软）** — 调用 Edge 浏览器的朗读服务，免费、不要 key、中文很自然。它本质上是个在线服务，但稳定用了好几年。

```python
import edge_tts
communicate = edge_tts.Communicate("你好，我是你的语音助手", "zh-CN-XiaoxiaoNeural")
await communicate.save("out.mp3")
```

合成 10 个字大概 1.4 秒（含网络往返）。

**Piper（本地）** — 纯离线，CPU 推理，但中文音质明显机器人味儿。

```
Piper:    1.1s  | 离线 | 音质中等（机器人味）
Edge:     1.5s  | 在线 | 音质好
```

实测下来，Edge-TTS 只慢 0.4 秒，音质好太多，而且我家有网，就选它了。常用的几个中文声音：

- `zh-CN-XiaoxiaoNeural`（女声，自然）
- `zh-CN-YunxiNeural`（男声）

**惊喜发现**：edge-tts 居然支持方言！

```
zh-CN-shaanxi-XiaoniNeural    # 陕西话
zh-CN-liaoning-XiaobeiNeural  # 东北话
```

陕西话那个一播出来，整个项目的乐趣直接翻倍。

## 第四步：STT（语音转文字）

用 faster-whisper（OpenAI Whisper 的优化版，CPU 上比原版快很多）。

```python
from faster_whisper import WhisperModel
model = WhisperModel("base", device="cpu", compute_type="int8")
segments, info = model.transcribe("audio.wav", language="zh")
```

第一次用 `base` 模型（74MB），识别"你好你好我是一个机器人"还行，但日常说话经常出错。换成 `small`（244MB）：

| 模型 | 加载 | 识别耗时 | 效果 |
|------|------|---------|------|
| base | 1.4s | 0.5s | 一般 |
| small | 60s（首次下载） | 1.2s | 明显更好 |

i5 跑 small 识别一句话才 1.2 秒，完全能接受。

> 教训二：Whisper 模型选择是准确率和速度的权衡。base 太糙，large 太慢，**small 是 CPU 场景的甜点**。

但说实话，即便是 small，中文口语识别也就 70 分。这个坑后面用火山引擎 ASR 才真正解决（见下篇）。

## 第五步：对接 Hermes Agent

这一步反而最简单。Hermes Agent 自带一个 OpenAI 兼容的 API server，跟调 OpenAI 一模一样：

```python
import requests

def chat_with_hermes(text):
    resp = requests.post(
        "http://localhost:8642/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": "deepseek-v4-pro",
            "messages": conversation_history,  # 带上下文
        },
    )
    return resp.json()["choices"][0]["message"]["content"]
```

**关键认知**：语音助手跟 Hermes 其实是解耦的。Hermes 正常跑它的，我只是像任何一个客户端那样调它的 API。这意味着这套语音前端可以接任何 OpenAI 兼容的后端 —— 换成直接调 DeepSeek、本地 Ollama，改一行 URL 就行。

用 Hermes 的好处是它带持久记忆和技能系统，能记住我是谁、我的偏好。但也有个副作用：语音对话的内容会混进 Hermes 的全局记忆里，跟我平时用它干别的事的记忆搅在一起。这个取舍后面要注意。

## 第六步：VAD + 唤醒词，把它们串起来

最后是触发逻辑——板子怎么知道你要说话了。

**VAD（语音活动检测）**：检测到音量超过阈值就开始录，静音超过 N 秒就停。

```python
def record_with_vad(device_idx):
    with sd.InputStream(samplerate=48000, channels=1,
                        dtype="int16", device=device_idx) as stream:
        while True:
            chunk, _ = stream.read(chunk_samples)
            rms = np.sqrt(np.mean(chunk.astype(np.float32) ** 2))
            if not recording and rms > THRESHOLD:
                recording = True       # 开始
            elif recording and rms < THRESHOLD:
                if silence > 3.0:
                    break              # 说完了
```

这里又踩一个坑：**无线麦克风只支持 48kHz**，但 Whisper 要 16kHz。一开始直接用 16kHz 打开麦克风，报 `Invalid sample rate`。解决办法是 48kHz 录音，然后降采样：

```python
chunk_16k = chunk[::3]   # 48000 / 16000 = 3，每3个取1个
```

**唤醒词**：用 openWakeWord，自带 alexa / hey_jarvis 等英文唤醒词。这里又有个版本冲突坑：

openWakeWord 默认用 tflite 后端，但它要求 numpy<2，而 faster-whisper 装的是 numpy 2.x，一跑就崩：

```
A module that was compiled using NumPy 1.x cannot be run in NumPy 2.4.3
```

解决：openWakeWord 支持 onnx 后端，切过去就好：

```python
Model(wakeword_models=["alexa_v0.1"], inference_framework="onnx")
```

## 完整流程

```
说 "Alexa" → 叮一声 → 说话 → 静音3秒结束 → Whisper识别
   → Hermes思考 → Edge-TTS合成 → aplay播放 → 回到等待唤醒
```

第一次完整跑通，对着麦克风说"中国一共有多少个省份"，音响里用陕西话女声回答出来的时候，还是挺有成就感的。

## 又一个坑：超长回复

跑通后第一个 bug：问"中国有多少省份"，Hermes 老老实实把 34 个省级行政区全列出来了，结果 edge-tts 处理超长文本直接报 `NoAudioReceived`，程序崩了。

两个修复：

1. system prompt 里加约束：`"回答控制在两三句话以内，不要列举太多内容"`
2. 代码里截断超长文本 + TTS 失败不崩溃：

```python
if len(text) > 200:
    text = text[:200] + "...就说到这里。"
try:
    ... # TTS
except Exception as e:
    print(f"TTS失败: {e}")
    return None  # 跳过，不崩
```

## 这套方案的优缺点

**优点：**
- ✅ 完全免费（Whisper 本地、Edge-TTS 白嫖微软）
- ✅ 隐私好（除了 TTS 调微软，识别和对话都在内网）
- ✅ 高度可定制，每个模块可换
- ✅ 无 GPU，i5 够用
- ✅ 对接自己的 Agent，有记忆有技能

**缺点：**
- ❌ 延迟高，说完到回复 4-8 秒
- ❌ 唤醒词是英文的，体验别扭
- ❌ 本地 Whisper 中文识别只有 70 分
- ❌ 半双工，它说话时你打断不了
- ❌ 组件多，维护成本高

## 适合谁

- 在意隐私、想数据不出门的人
- 想对接自己 LLM/Agent 的开发者
- 有服务器、爱折腾、预算为零的人

## 后来呢

这套能用，但体验只能算"能用"。识别不准、唤醒别扭、延迟高这几个问题，靠堆开源组件很难根治。

后来我去试了火山引擎（字节，豆包同款）的语音方案，体验直接上了一个台阶——识别准到能听懂陕西话，还有个端到端实时语音模型能做到接近真人对话的延迟。那是下一篇的故事。

但这套开源方案我没删——它能接我自己的 Hermes Agent（带记忆、能扩展日程提醒/智能家居），这是商业黑盒给不了的。两套各有各的命。

---

*相关代码已开源，包含完整的 main.py、config.yaml 和踩坑记录。*
