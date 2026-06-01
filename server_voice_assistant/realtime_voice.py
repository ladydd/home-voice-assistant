#!/usr/bin/env python3
"""
火山引擎端到端实时语音对话 - 家庭语音助手 v2
WebSocket 全双工实时对话，支持陕西话方言。

用法: python realtime_voice.py
退出: Ctrl+C
"""

import asyncio
import json
import struct
import sys
import threading
import time
import uuid

import numpy as np
import sounddevice as sd
import websockets

# ─── 配置 ────────────────────────────────────────────────────

# 鉴权
APP_ID = "your-app-id"
ACCESS_KEY = "your-access-key"
RESOURCE_ID = "volc.speech.dialog"
APP_KEY = "PlgvMymc7f3tQnJ6"

WS_URL = "wss://openspeech.bytedance.com/api/v3/realtime/dialogue"

# 音频配置
MIC_SAMPLE_RATE = 16000  # 服务端要求 16kHz
MIC_RECORD_RATE = 48000  # 麦克风实际采样率（无线麦只支持48kHz）
MIC_CHANNELS = 1
MIC_DEVICE = 6  # Wireless microphone: USB Audio (hw:1,0)
CHUNK_DURATION_MS = 20  # 每包 20ms
CHUNK_SAMPLES = int(MIC_RECORD_RATE * CHUNK_DURATION_MS / 1000)  # 录音用 48kHz
DOWNSAMPLE_RATIO = MIC_RECORD_RATE // MIC_SAMPLE_RATE  # 48000/16000 = 3

# 播放配置
PLAY_SAMPLE_RATE = 24000  # 服务端返回 24kHz
PLAY_CHANNELS = 1
PLAY_DEVICE = 0  # HDA Intel PCH: ALC897 Analog

# 人设配置
BOT_NAME = "小陕"
SYSTEM_ROLE = "你是一个热情的家庭语音助手，说话用陕西方言风格，简洁明了，像朋友一样聊天。"
SPEAKING_STYLE = "你说话带陕西味儿，口语化，不要太正式。"

# 模型版本
MODEL_VERSION = "1.2.1.1"  # O2.0 版本
TTS_SPEAKER = "zh_female_vv_jupiter_bigtts"  # vv 音色
DIALECT = "shaanxi"  # 陕西话


# ─── 二进制协议构建 ─────────────────────────────────────────────

def build_client_event(event_id, session_id=None, payload=None):
    """构建客户端文本事件帧 (Message Type = 0b0001)"""
    # Byte 0: protocol_version(0001) + header_size(0001) = 0x11
    # Byte 1: message_type(0001) + flags(0100=has event) = 0x14
    # Byte 2: serialization(0001=JSON) + compression(0000=none) = 0x10
    # Byte 3: reserved = 0x00
    header = bytes([0x11, 0x14, 0x10, 0x00])

    # Event ID (4 bytes big-endian)
    event_bytes = struct.pack(">I", event_id)

    # Session ID (only for session-level events, event_id >= 100)
    session_bytes = b""
    if session_id and event_id >= 100:
        sid_encoded = session_id.encode("utf-8")
        session_bytes = struct.pack(">I", len(sid_encoded)) + sid_encoded

    # Payload
    if payload is None:
        payload_data = b"{}"
    elif isinstance(payload, dict):
        payload_data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    else:
        payload_data = payload.encode("utf-8")

    payload_size = struct.pack(">I", len(payload_data))

    return header + event_bytes + session_bytes + payload_size + payload_data


def build_audio_frame(audio_bytes, session_id):
    """构建音频数据帧 (Message Type = 0b0010, event_id=200)"""
    # Byte 0: protocol_version(0001) + header_size(0001) = 0x11
    # Byte 1: message_type(0010) + flags(0100=has event) = 0x24
    # Byte 2: serialization(0000=Raw) + compression(0000=none) = 0x00
    # Byte 3: reserved = 0x00
    header = bytes([0x11, 0x24, 0x00, 0x00])

    # Event ID = 200 (TaskRequest)
    event_bytes = struct.pack(">I", 200)

    # Session ID
    sid_encoded = session_id.encode("utf-8")
    session_bytes = struct.pack(">I", len(sid_encoded)) + sid_encoded

    # Payload (raw audio bytes)
    payload_size = struct.pack(">I", len(audio_bytes))

    return header + event_bytes + session_bytes + payload_size + audio_bytes


def parse_server_frame(data):
    """解析服务端返回的帧"""
    if len(data) < 4:
        return None

    byte1 = data[1]
    msg_type = (byte1 >> 4) & 0x0F
    flags = byte1 & 0x0F

    byte2 = data[2]
    serialization = (byte2 >> 4) & 0x0F

    offset = 4

    # Parse event ID if flags indicate event (0b0100 = 4)
    event_id = None
    if flags & 0x04:
        if offset + 4 <= len(data):
            event_id = struct.unpack(">I", data[offset:offset + 4])[0]
            offset += 4

    # Parse session ID if present (for session-level events)
    session_id = None
    if event_id and event_id >= 100:
        if offset + 4 <= len(data):
            sid_len = struct.unpack(">I", data[offset:offset + 4])[0]
            offset += 4
            if offset + sid_len <= len(data):
                session_id = data[offset:offset + sid_len].decode("utf-8")
                offset += sid_len

    # Parse payload
    payload = None
    if offset + 4 <= len(data):
        payload_len = struct.unpack(">I", data[offset:offset + 4])[0]
        offset += 4
        if offset + payload_len <= len(data):
            raw_payload = data[offset:offset + payload_len]
            if msg_type == 0b1011:  # Audio response
                payload = raw_payload  # raw audio bytes
            elif serialization == 1:  # JSON
                try:
                    payload = json.loads(raw_payload.decode("utf-8"))
                except:
                    payload = raw_payload
            else:
                payload = raw_payload

    return {
        "msg_type": msg_type,
        "event_id": event_id,
        "session_id": session_id,
        "payload": payload,
    }


# ─── 主程序 ─────────────────────────────────────────────────

class RealtimeVoiceAssistant:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.ws = None
        self.running = False
        self.audio_buffer = bytearray()
        self.is_playing = False
        self.play_lock = threading.Lock()
        self._aplay_proc = None

    def get_session_payload(self):
        """构建 StartSession 的 payload"""
        return {
            "tts": {
                "speaker": TTS_SPEAKER,
                "extra": {
                    "explicit_dialect": DIALECT,
                },
                "audio_config": {
                    "channel": 1,
                    "format": "pcm_s16le",
                    "sample_rate": PLAY_SAMPLE_RATE,
                },
            },
            "asr": {
                "audio_info": {
                    "format": "pcm",
                    "sample_rate": MIC_SAMPLE_RATE,
                    "channel": MIC_CHANNELS,
                },
                "extra": {
                    "end_smooth_window_ms": 2000,
                    "enable_custom_vad": True,
                },
            },
            "dialog": {
                "bot_name": BOT_NAME,
                "system_role": SYSTEM_ROLE,
                "speaking_style": SPEAKING_STYLE,
                "dialog_id": "home-assistant-main",
                "extra": {
                    "strict_audit": False,
                    "model": MODEL_VERSION,
                    "input_mod": "keep_alive",
                },
            },
        }

    async def send_audio(self):
        """从麦克风读取音频并发送到服务端"""
        print("  🎤 麦克风已开启，开始推送音频...")

        with sd.InputStream(
            samplerate=MIC_RECORD_RATE,
            channels=MIC_CHANNELS,
            dtype="int16",
            device=MIC_DEVICE,
            blocksize=CHUNK_SAMPLES,
        ) as stream:
            while self.running:
                try:
                    chunk, _ = stream.read(CHUNK_SAMPLES)
                    if chunk.ndim > 1:
                        chunk = chunk[:, 0]
                    # 降采样 48kHz -> 16kHz
                    chunk_16k = chunk[::DOWNSAMPLE_RATIO]
                    audio_bytes = chunk_16k.tobytes()
                    frame = build_audio_frame(audio_bytes, self.session_id)
                    await self.ws.send(frame)
                    await asyncio.sleep(CHUNK_DURATION_MS / 1000.0)
                except Exception as e:
                    if self.running:
                        print(f"  ⚠️  音频发送错误: {e}")
                    break

    async def receive_events(self):
        """接收服务端事件"""
        while self.running:
            try:
                data = await self.ws.recv()
                parsed = parse_server_frame(data)
                if parsed is None:
                    continue

                event_id = parsed["event_id"]
                payload = parsed["payload"]
                msg_type = parsed["msg_type"]

                if event_id == 50:  # ConnectionStarted
                    print("  ✅ 连接建立")
                elif event_id == 150:  # SessionStarted
                    dialog_id = payload.get("dialog_id", "") if isinstance(payload, dict) else ""
                    print(f"  ✅ 会话开始 (dialog_id: {dialog_id})")
                elif event_id == 450:  # ASRInfo - 检测到说话
                    print("  🔴 检测到语音...")
                    # 打断当前播放
                    self.stop_playback()
                elif event_id == 451:  # ASRResponse - 识别文本
                    if isinstance(payload, dict):
                        results = payload.get("results", [])
                        for r in results:
                            text = r.get("text", "")
                            is_interim = r.get("is_interim", True)
                            if not is_interim:
                                print(f"  📝 你说: {text}")
                elif event_id == 459:  # ASREnded
                    pass
                elif event_id == 350:  # TTSSentenceStart
                    if isinstance(payload, dict):
                        text = payload.get("text", "")
                        if text:
                            print(f"  💬 回复: {text}")
                elif event_id == 352:  # TTSResponse - 音频数据
                    if msg_type == 0b1011 and isinstance(payload, (bytes, bytearray)):
                        self.play_audio_chunk(payload)
                elif event_id == 359:  # TTSEnded
                    self.flush_audio()
                elif event_id == 550:  # ChatResponse
                    pass  # 文本回复，已在 TTSSentenceStart 打印
                elif event_id == 153:  # SessionFailed
                    error = payload.get("error", "") if isinstance(payload, dict) else str(payload)
                    print(f"  ❌ 会话失败: {error}")
                elif event_id == 599:  # DialogCommonError
                    if isinstance(payload, dict):
                        print(f"  ⚠️  错误: {payload.get('message', '')}")
                elif event_id == 154:  # UsageResponse
                    if isinstance(payload, dict):
                        usage = payload.get("usage", {})
                        total = sum(usage.values()) if usage else 0
                        print(f"  📊 本轮消耗: {total} tokens")

            except websockets.exceptions.ConnectionClosed:
                if self.running:
                    print("  ⚠️  连接断开，尝试重连...")
                break
            except Exception as e:
                if self.running:
                    print(f"  ⚠️  接收错误: {e}")

    def play_audio_chunk(self, audio_bytes):
        """直接写入 aplay 进程"""
        with self.play_lock:
            if self._aplay_proc is None or self._aplay_proc.poll() is not None:
                # 启动一个持续的 aplay 进程
                import subprocess
                self._aplay_proc = subprocess.Popen(
                    ["aplay", "-D", "plughw:0,0", "-f", "S16_LE", "-r", str(PLAY_SAMPLE_RATE), "-c", "1", "-t", "raw"],
                    stdin=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
            try:
                self._aplay_proc.stdin.write(audio_bytes)
                self._aplay_proc.stdin.flush()
            except Exception as e:
                print(f"  ⚠️  播放错误: {e}")
                self._aplay_proc = None

    def _play_buffer(self):
        pass

    def stop_playback(self):
        """立即停止播放（用于打断）"""
        with self.play_lock:
            if self._aplay_proc and self._aplay_proc.poll() is None:
                try:
                    self._aplay_proc.kill()
                except:
                    pass
                self._aplay_proc = None

    def flush_audio(self):
        """结束当前播放"""
        with self.play_lock:
            if self._aplay_proc and self._aplay_proc.poll() is None:
                try:
                    self._aplay_proc.stdin.close()
                    self._aplay_proc.wait(timeout=5)
                except:
                    pass
                self._aplay_proc = None

    async def run(self):
        """主运行循环（带自动重连）"""
        print("=" * 50)
        print("  🏠 家庭语音助手 v2 (豆包端到端实时语音)")
        print("=" * 50)
        print()
        print(f"  人设: {BOT_NAME}")
        print(f"  方言: 陕西话")
        print(f"  模型: O2.0")
        print(f"  模式: 永久运行（自动重连）")
        print()

        while True:
            try:
                await self._run_session()
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"  ⚠️  连接异常: {e}")

            if not self.running:
                break

            # 自动重连
            print("  🔄 5秒后自动重连...")
            self.session_id = str(uuid.uuid4())
            self._aplay_proc = None
            await asyncio.sleep(5)

        print("\n  👋 再见！")

    async def _run_session(self):
        """单次会话"""
        headers = {
            "X-Api-App-ID": APP_ID,
            "X-Api-Access-Key": ACCESS_KEY,
            "X-Api-Resource-Id": RESOURCE_ID,
            "X-Api-App-Key": APP_KEY,
            "X-Api-Connect-Id": str(uuid.uuid4()),
        }

        async with websockets.connect(
            WS_URL,
            additional_headers=headers,
            ping_interval=30,
            ping_timeout=10,
        ) as ws:
            self.ws = ws
            self.running = True

            # 1. StartConnection
            await ws.send(build_client_event(1))
            resp = await ws.recv()
            parsed = parse_server_frame(resp)
            if not parsed or parsed["event_id"] != 50:
                print("  ❌ 连接失败")
                return
            print("  ✅ WebSocket 连接成功")

            # 2. StartSession
            session_payload = self.get_session_payload()
            frame = build_client_event(100, self.session_id, session_payload)
            await ws.send(frame)

            # Wait for SessionStarted
            resp = await asyncio.wait_for(ws.recv(), timeout=10)
            parsed = parse_server_frame(resp)
            if not parsed or parsed["event_id"] != 150:
                print(f"  ❌ 会话启动失败")
                return
            print("  ✅ 会话已启动")
            print()
            print("  🎧 就绪！直接说话即可，无需唤醒词。")
            print()

            # 3. 并发：发送音频 + 接收事件
            await asyncio.gather(
                self.send_audio(),
                self.receive_events(),
            )


async def main():
    assistant = RealtimeVoiceAssistant()
    await assistant.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n  👋 再见！")
    except Exception as e:
        print(f"  Fatal: {e}")
        sys.exit(1)
