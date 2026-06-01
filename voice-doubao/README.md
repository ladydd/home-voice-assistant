# voice-doubao — 豆包端到端实时语音助手

火山引擎 Realtime API，全双工实时语音对话，陕西话方言。

## 特点
- 无需唤醒词，直接说话
- 实时对话，延迟极低
- 陕西话方言
- 自动重连，永久运行
- systemd 服务，开机自启

## 服务器部署路径
`/home/ladydd/voice-doubao/`

## 管理命令
```bash
sudo systemctl status voice-doubao    # 查看状态
sudo systemctl restart voice-doubao   # 重启
sudo systemctl stop voice-doubao      # 停止
journalctl -u voice-doubao -f         # 实时日志
```

## 计费
- 按 tokens 计费，挂着不说话不花钱
- 免费额度：1,000,000 tokens
