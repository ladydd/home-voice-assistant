# voice-doubao 运维排查手册

每次出问题按这个顺序排查。

## 快速检查命令

```bash
# 查看服务状态
systemctl status voice-doubao --no-pager

# 看最近日志
journalctl -u voice-doubao --no-pager -n 30

# 重启服务
sudo systemctl restart voice-doubao

# 查看音频设备
arecord -l   # 录音设备
aplay -l     # 播放设备
lsusb        # USB 设备
```

---

## 坑 1：麦克风未找到

**症状**：日志刷 `⚠️ 麦克风未找到，等待重连...`

**原因**：无线麦 USB 接收器没插、没开机、或者发射端没开。

**排查**：
```bash
lsusb | grep 3547          # 看 USB 接收器在不在
arecord -l                  # 看声卡里有没有 Wireless microphone
```

**解决**：
- 确认 USB 接收器插好
- 确认麦克风发射端开机
- 已配置 udev 规则，插入麦克风会自动重启服务（延迟 3 秒等 ALSA 注册）

---

## 坑 2：会话启动失败（循环重连）

**症状**：日志刷 `✅ WebSocket 连接成功` + `❌ 会话启动失败` 循环

**原因**：火山引擎额度用完了。

**错误信息**（从原始字节解码）：
```json
{"error":"quota exceeded for types: tokens_lifetime"}
```

**解决**：
- 登录 [火山引擎控制台](https://console.volcengine.com/speech) → 豆包端到端实时语音大模型
- 确认服务状态是**运行中**（不是"暂停"）
- 确认有额度（充值或开通按量付费）
- 注意：端到端实时语音 (`volc.speech.dialog`) 的额度跟普通 ASR/TTS 是独立的

---

## 坑 3：音响没声音

**症状**：日志显示正常识别和回复、tokens 消耗正常，但音响不出声。

**排查步骤**：

### 3.1 物理检查
- 音响电源开了没？
- 音响音量旋钮拧开了没？
- 3.5mm 线插在主板后面的**绿色口**（Line Out）？

### 3.2 ALSA 设置
```bash
# 检查音量和静音状态
amixer -c 0 get Master
amixer -c 0 get 'Auto-Mute Mode'

# 修复
amixer -c 0 set 'Auto-Mute Mode' Disabled
amixer -c 0 set Master 100% unmute
amixer -c 0 set Front 100% unmute

# 保存设置（重启不丢失）
sudo alsactl store
```

### 3.3 测试出声
```bash
# 先停掉 voice-doubao（它会占着声卡）
sudo systemctl stop voice-doubao

# 播放测试音
speaker-test -D plughw:0,0 -t sine -f 440 -l 1 -p 2

# 确认能听到"嘟"声后再启动服务
sudo systemctl restart voice-doubao
```

### 3.4 Device busy
如果 speaker-test 报 `Device or resource busy`，说明 voice-doubao 的 aplay 进程占着声卡，先 stop 服务再测。

---

## 坑 4：Auto-Mute Mode（重启后音响没声音）

**原因**：主板 ALC897 声卡有自动静音功能，某些情况下会重新开启。

**症状**：重启服务器后音响没声音。

**解决**：
```bash
amixer -c 0 set 'Auto-Mute Mode' Disabled
sudo alsactl store   # 持久化
```

---

## 坑 5：环境噪音误触发

**症状**：日志里识别出的文字明显是电视/小孩/环境音，token 哗哗消耗。

**原因**：端到端模型靠 VAD 触发，没有唤醒词，任何人声都会被当成对话。

**临时缓解**：
- 把麦克风放离电视远一点
- 不用的时候关掉麦克风发射端

**根本解决**（TODO）：
- 客户端加唤醒词门禁，平时不推音频

---

## 坑 6：udev 规则时序问题

**症状**：拔插麦克风后 udev 触发重启，但服务起来后还是找不到麦克风。

**原因**：USB 设备刚插入时 ALSA 还没注册声卡，服务起太早。

**解决**：udev 规则指向延迟脚本，等 3 秒再重启：

```bash
# /etc/udev/rules.d/99-voice-doubao-mic.rules
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="3547", ATTR{idProduct}=="000c", RUN+="/usr/local/bin/restart-voice-doubao.sh"

# /usr/local/bin/restart-voice-doubao.sh
#!/bin/bash
sleep 3
/bin/systemctl restart voice-doubao.service
```

---

## 服务管理

```bash
sudo systemctl start voice-doubao     # 启动
sudo systemctl stop voice-doubao      # 停止
sudo systemctl restart voice-doubao   # 重启
sudo systemctl status voice-doubao    # 状态
journalctl -u voice-doubao -f         # 实时日志
```

## 服务器信息

- IP: 192.168.0.190
- 用户: ladydd
- 部署路径: /home/ladydd/voice-doubao
- Python 环境: /home/ladydd/.hermes/hermes-agent/venv
- 麦克风: Hollyland 猛犸无线麦 (USB ID: 3547:000c)
- 声卡: HDA Intel PCH ALC897 (plughw:0,0)

---

## 坑 7：播放 Broken pipe（音响突然没声音，日志刷错误）

**症状**：运行一段时间后音响突然没声了，日志里反复出现：
```
⚠️  播放错误: [Errno 32] Broken pipe
⚠️  播放错误: [Errno 32] Broken pipe
⚠️  播放错误: [Errno 32] Broken pipe
```

**原因**：aplay 进程意外退出（可能是被打断逻辑 kill 后没正确重建，或者运行太久自己挂了），代码继续往已死进程的 stdin 写数据，就报 Broken pipe。旧代码只是把 `_aplay_proc` 设为 None，但同一批 TTS 音频有多个 chunk，后面的 chunk 还是在写死进程。

**修复**（已应用到服务器）：

`play_audio_chunk` 改为出错后立即重建 aplay 并重试写入：

```python
def _start_aplay(self):
    """启动一个新的 aplay 进程"""
    import subprocess
    try:
        if self._aplay_proc and self._aplay_proc.poll() is None:
            try:
                self._aplay_proc.kill()
                self._aplay_proc.wait(timeout=2)
            except:
                pass
    except:
        pass
    self._aplay_proc = subprocess.Popen(
        ["aplay", "-D", "plughw:0,0", "-f", "S16_LE", "-r", str(PLAY_SAMPLE_RATE), "-c", "1", "-t", "raw"],
        stdin=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

def play_audio_chunk(self, audio_bytes):
    """直接写入 aplay 进程，出错自动重建"""
    with self.play_lock:
        if self._aplay_proc is None or self._aplay_proc.poll() is not None:
            self._start_aplay()
        try:
            self._aplay_proc.stdin.write(audio_bytes)
            self._aplay_proc.stdin.flush()
        except Exception as e:
            # aplay 挂了，重建并重试一次
            try:
                self._start_aplay()
                self._aplay_proc.stdin.write(audio_bytes)
                self._aplay_proc.stdin.flush()
            except Exception as e2:
                print(f"  ⚠️  播放错误: {e2}")
                self._aplay_proc = None
```

**状态**：已修复，部署在服务器上。本地 `main.py` 也需要同步更新。

---

## 坑 8：aplay 假死（进程活着但不出声）

**症状**：日志正常（识别、tokens 消耗），无报错，但音响就是没声音。`ps aux` 看 aplay 进程还活着。

**原因**：aplay 进程内部卡住（ALSA 缓冲区满或底层驱动问题），进程没退出但不再播放音频。代码只检查"进程是否退出"，没检查"是否真的在工作"。

**修复**（已应用到服务器）：加看门狗——如果 aplay 超过 2 分钟没成功写入新数据，主动杀掉重建。每次成功写入都刷新时间戳。

**临时恢复**：
```bash
pkill -f aplay
# 代码会自动重建新的 aplay 进程
```

---

## 一键管理命令

服务器上已配置 `voice` 命令（`/usr/local/bin/voice`），无需 sudo 密码：

```bash
voice start     # 启动
voice stop      # 停止
voice restart   # 重启
voice s         # 查看状态
voice l         # 最近日志
voice f         # 实时跟踪日志（Ctrl+C 退出）
```

实现：
- 脚本路径：`/usr/local/bin/voice`
- 免密配置：`/etc/sudoers.d/voice-doubao`（仅允许 ladydd 免密操作 voice-doubao 服务）
