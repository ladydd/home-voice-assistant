# voice-doubao

火山引擎端到端实时语音助手。一个 Python 脚本实现全双工实时语音对话。

## 特点

- 🎙️ 无需唤醒词，直接说话
- ⚡ 实时对话，延迟极低（<1秒）
- 🗣️ 支持方言（陕西话、四川话、东北话）
- 🔄 自动重连，永久运行
- 🎯 自定义人设（bot_name / system_role / speaking_style）
- 📡 麦克风断开自动重试

## 架构

```
USB麦克风 → 服务器 → WebSocket → 火山引擎端到端模型 → WebSocket → 服务器 → 音响
         (实时推音频20ms/包)                              (实时接收音频并播放)
```

服务器只做音频搬运，所有智能在云端。

## 前提

- Linux 服务器（任意 CPU，无 GPU 要求）
- USB 麦克风
- 有线音响（3.5mm）
- 火山引擎账号 + 开通"端到端实时语音大模型"

## 安装

```bash
# 依赖
pip install websockets sounddevice numpy

# 系统音频工具
sudo apt-get install -y alsa-utils

# 用户加入 audio 组
sudo usermod -aG audio $USER
```

## 配置

1. 在[火山引擎控制台](https://console.volcengine.com/speech/app)获取 App ID 和 Access Token
2. 设置环境变量或直接修改 `main.py` 顶部：

```bash
export VOLC_APP_ID="your-app-id"
export VOLC_ACCESS_KEY="your-access-key"
```

3. 修改 `main.py` 中的音频设备和人设配置

## 运行

```bash
# 直接运行
python main.py

# 或用 systemd 永久运行（见下方）
```

## 部署为系统服务

```bash
sudo cp voice-doubao.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable voice-doubao
sudo systemctl start voice-doubao
```

管理命令：
```bash
sudo systemctl status voice-doubao    # 查看状态
sudo systemctl restart voice-doubao   # 重启
journalctl -u voice-doubao -f         # 实时日志
```

## 配置说明

在 `main.py` 顶部修改：

| 配置项 | 说明 |
|--------|------|
| `MIC_RECORD_RATE` | 麦克风采样率（USB麦通常48000） |
| `MIC_DEVICE` | 麦克风设备编号（`python -c "import sounddevice; print(sounddevice.query_devices())"` 查看） |
| `BOT_NAME` | 助手名字 |
| `SYSTEM_ROLE` | 背景人设 |
| `SPEAKING_STYLE` | 说话风格 |
| `DIALECT` | 方言（shaanxi/dongbei/sichuan/留空为普通话） |
| `MODEL_VERSION` | 模型版本（1.2.1.1=O2.0） |

## 计费

- 按 tokens 计费，挂着不说话不花钱
- 免费额度：1,000,000 tokens（约数百轮对话）
- 超过 10 分钟无对话会断开，程序自动重连

## 已知限制

- LLM 是火山的模型，不可自定义
- 无唤醒词，环境嘈杂时会误触发
- 上下文仅保留最近 20 轮（非持久记忆）

## License

MIT
