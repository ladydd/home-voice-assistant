# voice-hermes — Hermes Agent 语音助手

纯开源方案：Whisper STT + Hermes Agent (DeepSeek) + 火山引擎 TTS。

## 特点
- 对接自己的 Hermes Agent（带记忆、技能）
- 可深度定制 LLM 行为
- 火山引擎 ASR（识别准）+ TTS（陕西话）
- 唤醒词 + VAD 触发
- 后续可接日程提醒、智能家居等

## 服务器部署路径
`/home/ladydd/voice-hermes/`

## 启动
```bash
sg audio -c '/home/ladydd/.hermes/hermes-agent/venv/bin/python /home/ladydd/voice-hermes/main.py'
```

## 后续规划
- [ ] 接入 HTTP 接口（支持主动推送/提醒）
- [ ] 优化唤醒词（自定义中文唤醒词）
- [ ] 接入 ESP32 无线麦克风
- [ ] 日程提醒功能
