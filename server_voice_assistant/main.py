#!/usr/bin/env python3
"""
家庭语音助手 - 主程序
录音(VAD触发) → STT(Whisper) → Hermes(LLM) → TTS(Edge) → 播放(音响)

用法: python main.py
退出: Ctrl+C
"""

import asyncio
import io
import json
import os
import struct
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

import numpy as np
import requests
import sounddevice as sd
import yaml

# ─── 加载配置 ───────────────────────────────────────────────

CONFIG_PATH = Path(__file__).parent / "config.yaml"

with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)

HERMES_URL = config["hermes"]["url"]
HERMES_KEY = config["hermes"]["api_key"]
HERMES_MODEL = config["hermes"]["model"]
SYSTEM_PROMPT = config["hermes"]["system_prompt"]

SAMPLE_RATE = config["audio"]["sample_rate"]
CHANNELS = config["audio"]["channels"]
DEVICE_INDEX = config["audio"]["device_index"]

# 实际录音采样率（某些 USB 麦克风只支持 48000）
RECORD_SAMPLE_RATE = 48000

ENERGY_THRESHOLD = config["vad"]["energy_threshold"]
SILENCE_DURATION = config["vad"]["silence_duration"]
MIN_RECORDING = config["vad"]["min_recording_duration"]
MAX_RECORDING = config["vad"]["max_recording_duration"]

TTS_PROVIDER = config["tts"]["provider"]
TTS_VOICE = config["tts"]["edge"]["voice"]
PIPER_MODEL = config["tts"]["piper"]["model"]

PLAYBACK_DEVICE = config["playback"]["device"]

# 唤醒词配置
WAKE_WORD_MODEL = config.get("wakeword", {}).get("model", "hey_jarvis_v0.1")
WAKE_WORD_THRESHOLD = config.get("wakeword", {}).get("threshold", 0.5)
WAKE_WORD_ENABLED = config.get("wakeword", {}).get("enabled", True)

# 对话历史（保持上下文）
conversation_history = [
    {"role": "system", "content": SYSTEM_PROMPT}
]
MAX_HISTORY = 20  # 最多保留多少轮对话


# ─── 工具函数 ───────────────────────────────────────────────

# ─── 唤醒词检测 ──────────────────────────────────────────────

_wakeword_model = None


def get_wakeword_model():
    global _wakeword_model
    if _wakeword_model is None:
        from openwakeword.model import Model as WakeModel
        print(f"  加载唤醒词模型: {WAKE_WORD_MODEL}")
        _wakeword_model = WakeModel(
            wakeword_models=[WAKE_WORD_MODEL],
            inference_framework="onnx"
        )
        print("  唤醒词模型就绪")
    return _wakeword_model


def wait_for_wakeword(device_idx):
    """
    持续监听，等待唤醒词触发。
    返回 True 表示检测到唤醒词。
    """
    model = get_wakeword_model()
    chunk_samples = 1280  # openWakeWord 需要 80ms @ 16kHz 的帧

    # 用 48kHz 录音，降采样到 16kHz 给唤醒词模型
    record_chunk = int(chunk_samples * (RECORD_SAMPLE_RATE / SAMPLE_RATE))

    print(f"  👂 等待唤醒词 \"{WAKE_WORD_MODEL.replace('_v0.1', '')}\"...")

    with sd.InputStream(
        samplerate=RECORD_SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        device=device_idx,
        blocksize=record_chunk,
    ) as stream:
        while True:
            chunk, _ = stream.read(record_chunk)
            # 双声道取第一个
            if chunk.ndim > 1:
                chunk = chunk[:, 0]
            # 降采样到 16kHz
            ratio = RECORD_SAMPLE_RATE // SAMPLE_RATE
            chunk_16k = chunk[::ratio]

            # 送入唤醒词模型
            prediction = model.predict(chunk_16k)
            score = prediction.get(WAKE_WORD_MODEL, 0)

            if score >= WAKE_WORD_THRESHOLD:
                model.reset()  # 重置状态，防止连续触发
                return True


# ─── 工具函数 ───────────────────────────────────────────────

def find_mic_device():
    """找到无线麦克风设备"""
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        if d["max_input_channels"] > 0:
            name = d["name"].lower()
            if "wireless" in name or "microphone" in name or "usb" in name:
                print(f"  找到麦克风: [{i}] {d['name']}")
                return i
    # 没找到特定的，用默认输入
    default = sd.default.device[0]
    if default is not None and default >= 0:
        print(f"  使用默认输入设备: [{default}] {devices[default]['name']}")
        return default
    return None


def calculate_rms(audio_chunk):
    """计算音频片段的 RMS 音量"""
    return np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2))


def record_with_vad(device_idx):
    """
    VAD 录音：检测到说话开始录，静音后停止。
    返回录音数据 (numpy array, 16kHz) 或 None（如果没检测到有效语音）
    """
    chunk_duration = 0.1  # 每次读 100ms
    chunk_samples = int(RECORD_SAMPLE_RATE * chunk_duration)

    print("  🎧 监听中... (说话即触发)")

    recording = []
    is_recording = False
    silence_start = None
    record_start = None

    with sd.InputStream(
        samplerate=RECORD_SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        device=device_idx,
        blocksize=chunk_samples,
    ) as stream:
        while True:
            chunk, _ = stream.read(chunk_samples)
            # 如果是双声道，取第一个声道
            if chunk.ndim > 1:
                chunk = chunk[:, 0]
            rms = calculate_rms(chunk)

            if not is_recording:
                # 等待触发
                if rms > ENERGY_THRESHOLD:
                    is_recording = True
                    record_start = time.time()
                    silence_start = None
                    recording = [chunk.copy()]
                    print("  🔴 检测到语音，开始录音...")
            else:
                # 正在录音
                recording.append(chunk.copy())
                elapsed = time.time() - record_start

                if rms > ENERGY_THRESHOLD:
                    silence_start = None
                else:
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start >= SILENCE_DURATION:
                        # 静音够久，停止录音
                        if elapsed >= MIN_RECORDING:
                            print(f"  ⏹️  录音结束 ({elapsed:.1f}s)")
                            break
                        else:
                            # 太短，当作误触发，重置
                            print("  ⚠️  录音太短，忽略")
                            recording = []
                            is_recording = False
                            silence_start = None
                            continue

                # 超时保护
                if elapsed >= MAX_RECORDING:
                    print(f"  ⏹️  达到最大录音时长 ({MAX_RECORDING}s)")
                    break

    if not recording:
        return None

    # 合并录音并降采样到 16kHz（Whisper 需要 16kHz）
    audio_data = np.concatenate(recording, axis=0)
    if RECORD_SAMPLE_RATE != SAMPLE_RATE:
        # 简单降采样：每 N 个取一个
        ratio = RECORD_SAMPLE_RATE // SAMPLE_RATE
        audio_data = audio_data[::ratio]
    return audio_data


def audio_to_wav_bytes(audio_data):
    """将 numpy 音频数据转为 WAV 字节"""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_data.tobytes())
    return buf.getvalue()


# ─── STT (语音转文字) ────────────────────────────────────────

# STT 提供者配置
STT_PROVIDER = config.get("stt", {}).get("provider", "whisper")

# 全局加载 Whisper 模型（只加载一次，仅 whisper 模式用）
_whisper_model = None


def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        print("  加载 Whisper 模型...")
        _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
        print("  Whisper 模型就绪")
    return _whisper_model


def speech_to_text_whisper(audio_data):
    """Whisper 本地语音转文字"""
    wav_bytes = audio_to_wav_bytes(audio_data)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.write(wav_bytes)
    tmp.close()

    try:
        model = get_whisper_model()
        segments, info = model.transcribe(tmp.name, language="zh")
        text = "".join([s.text for s in segments]).strip()
        return text
    finally:
        os.unlink(tmp.name)


def speech_to_text_volcengine(audio_data):
    """火山引擎 Seed-ASR 语音转文字"""
    import uuid

    wav_bytes = audio_to_wav_bytes(audio_data)
    audio_b64 = __import__("base64").b64encode(wav_bytes).decode()

    volcengine_cfg = config.get("stt", {}).get("volcengine", {})
    api_key = volcengine_cfg.get("api_key", "")
    resource_id = volcengine_cfg.get("resource_id", "volc.seedasr.auc")

    req_id = str(uuid.uuid4())

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": req_id,
        "X-Api-Sequence": "-1",
    }

    payload = {
        "user": {"uid": "voice-assistant"},
        "audio": {
            "data": audio_b64,
            "format": "wav",
            "codec": "raw",
            "rate": SAMPLE_RATE,
            "bits": 16,
            "channel": 1,
        },
        "request": {
            "model_name": "bigmodel",
            "enable_itn": True,
            "enable_punc": True,
        },
    }

    base_url = "https://openspeech.bytedance.com/api/v3/auc/bigmodel"

    try:
        # 提交任务
        resp = requests.post(f"{base_url}/submit", json=payload, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"  ⚠️  火山引擎提交失败: {resp.status_code}")
            return None

        # 查询结果
        import time
        query_headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "X-Api-Resource-Id": resource_id,
            "X-Api-Request-Id": req_id,
        }

        for _ in range(10):  # 最多等 5 秒
            time.sleep(0.5)
            query_resp = requests.post(f"{base_url}/query", json={}, headers=query_headers, timeout=10)
            if query_resp.status_code == 200:
                result = query_resp.json()
                text = result.get("result", {}).get("text", "")
                if text:
                    return text.strip()
        return None
    except Exception as e:
        print(f"  ⚠️  火山引擎 ASR 错误: {e}")
        return None


def speech_to_text(audio_data):
    """语音转文字（根据配置选择提供者）"""
    if STT_PROVIDER == "volcengine":
        result = speech_to_text_volcengine(audio_data)
        if result:
            return result
        # fallback to whisper
        print("  ⚠️  火山引擎失败，回退到 Whisper")
    return speech_to_text_whisper(audio_data)


# ─── Hermes LLM 对话 ────────────────────────────────────────

def chat_with_hermes(user_text):
    """发送文字给 Hermes，获取回复"""
    global conversation_history

    conversation_history.append({"role": "user", "content": user_text})

    # 限制历史长度
    if len(conversation_history) > MAX_HISTORY + 1:  # +1 for system
        conversation_history = [conversation_history[0]] + conversation_history[-(MAX_HISTORY):]

    payload = {
        "model": HERMES_MODEL,
        "messages": conversation_history,
    }

    headers = {
        "Authorization": f"Bearer {HERMES_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(HERMES_URL, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        reply = data["choices"][0]["message"]["content"]
        conversation_history.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        print(f"  ❌ Hermes 请求失败: {e}")
        return "抱歉，我暂时无法回答。"


# ─── TTS (文字转语音) ────────────────────────────────────────

async def text_to_speech_edge(text, output_path):
    """Edge TTS (在线)"""
    import edge_tts
    communicate = edge_tts.Communicate(text, TTS_VOICE)
    await communicate.save(output_path)


def text_to_speech_piper(text, output_path):
    """Piper TTS (本地)"""
    subprocess.run(
        ["piper", "--model", PIPER_MODEL, "--output_file", output_path],
        input=text.encode(),
        capture_output=True,
    )


def text_to_speech_volcengine(text, output_path):
    """火山引擎 TTS (Vivi 2.0 陕西话)"""
    import uuid
    import base64

    volcengine_cfg = config.get("tts", {}).get("volcengine", {})
    api_key = volcengine_cfg.get("api_key", "")
    resource_id = volcengine_cfg.get("resource_id", "seed-tts-2.0")
    speaker = volcengine_cfg.get("speaker", "zh_female_vv_uranus_bigtts")
    dialect = volcengine_cfg.get("dialect", "")
    sample_rate = volcengine_cfg.get("sample_rate", 24000)

    url = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": str(uuid.uuid4()),
    }

    additions = {}
    if dialect:
        additions["explicit_dialect"] = dialect

    payload = {
        "user": {"uid": "voice-assistant"},
        "req_params": {
            "text": text,
            "speaker": speaker,
            "audio_params": {
                "format": "mp3",
                "sample_rate": sample_rate,
            },
            "additions": json.dumps(additions) if additions else "",
        },
    }

    resp = requests.post(url, json=payload, headers=headers, stream=True, timeout=30)
    if resp.status_code != 200:
        raise Exception(f"Volcengine TTS failed: {resp.status_code} {resp.text[:200]}")

    audio_data = b""
    for line in resp.iter_lines():
        if line:
            try:
                obj = json.loads(line)
                if obj.get("data"):
                    audio_data += base64.b64decode(obj["data"])
            except:
                pass

    if not audio_data:
        raise Exception("Volcengine TTS: no audio data received")

    with open(output_path, "wb") as f:
        f.write(audio_data)


def text_to_speech(text):
    """文字转语音，返回 WAV 文件路径"""
    # 如果文本太长，截断（防止 TTS 失败）
    if len(text) > 200:
        text = text[:200] + "...就说到这里。"

    tmp_mp3 = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp_mp3.close()
    tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_wav.close()

    try:
        if TTS_PROVIDER == "volcengine":
            text_to_speech_volcengine(text, tmp_mp3.name)
            # 转换为 WAV
            subprocess.run(
                ["ffmpeg", "-i", tmp_mp3.name, "-f", "wav", "-acodec", "pcm_s16le",
                 "-ar", "44100", tmp_wav.name, "-y"],
                capture_output=True,
            )
            os.unlink(tmp_mp3.name)
            return tmp_wav.name
        elif TTS_PROVIDER == "edge":
            asyncio.run(text_to_speech_edge(text, tmp_mp3.name))
            # 转换为 WAV
            subprocess.run(
                ["ffmpeg", "-i", tmp_mp3.name, "-f", "wav", "-acodec", "pcm_s16le",
                 "-ar", "44100", tmp_wav.name, "-y"],
                capture_output=True,
            )
            os.unlink(tmp_mp3.name)
            return tmp_wav.name
        else:
            # Piper 直接输出 WAV
            os.unlink(tmp_mp3.name)
            text_to_speech_piper(text, tmp_wav.name)
            return tmp_wav.name
    except Exception as e:
        print(f"  ⚠️  TTS 失败: {e}")
        # 清理临时文件
        for f in [tmp_mp3.name, tmp_wav.name]:
            try:
                os.unlink(f)
            except:
                pass
        return None


# ─── 播放 ───────────────────────────────────────────────────

def play_audio(wav_path):
    """通过 ALSA 播放音频"""
    if wav_path is None:
        return
    subprocess.run(
        ["aplay", "-D", PLAYBACK_DEVICE, wav_path],
        capture_output=True,
    )
    try:
        os.unlink(wav_path)
    except:
        pass


# ─── 主循环 ─────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("  🏠 家庭语音助手")
    print("=" * 50)
    print()

    # 找麦克风
    device_idx = DEVICE_INDEX
    if device_idx is None:
        device_idx = find_mic_device()
    if device_idx is None:
        print("❌ 找不到麦克风设备！请插入 USB 麦克风。")
        sys.exit(1)

    # 预加载模型
    get_whisper_model()
    if WAKE_WORD_ENABLED:
        get_wakeword_model()

    print()
    if WAKE_WORD_ENABLED:
        print("  ✅ 就绪！说唤醒词唤醒，然后说话。")
    else:
        print("  ✅ 就绪！对着麦克风说话即可（VAD 模式）。")
    print("  按 Ctrl+C 退出")
    print()

    try:
        while True:
            # 0. 唤醒词检测（如果启用）
            if WAKE_WORD_ENABLED:
                wait_for_wakeword(device_idx)
                print("  🔔 唤醒成功！请说话...")
                # 播放提示音（可选）
                _play_ding()

            # 1. VAD 录音
            audio_data = record_with_vad(device_idx)
            if audio_data is None:
                continue

            # 2. STT
            print("  🧠 识别中...")
            start = time.time()
            user_text = speech_to_text(audio_data)
            stt_time = time.time() - start

            if not user_text:
                print("  ⚠️  没有识别到有效文字")
                continue

            print(f"  📝 你说: {user_text} ({stt_time:.1f}s)")

            # 3. Hermes 对话
            print("  💭 思考中...")
            start = time.time()
            reply = chat_with_hermes(user_text)
            llm_time = time.time() - start
            print(f"  💬 回复: {reply} ({llm_time:.1f}s)")

            # 4. TTS
            print("  🔊 合成语音...")
            start = time.time()
            wav_path = text_to_speech(reply)
            tts_time = time.time() - start
            print(f"  ⏱️  TTS: {tts_time:.1f}s")

            # 5. 播放
            play_audio(wav_path)
            print()

    except KeyboardInterrupt:
        print("\n\n  👋 再见！")


def _play_ding():
    """播放一个短提示音表示唤醒成功"""
    try:
        # 生成一个简短的提示音 (880Hz, 0.15s)
        duration = 0.15
        sample_rate = 44100
        t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
        tone = (np.sin(2 * np.pi * 880 * t) * 16000).astype(np.int16)

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(tone.tobytes())
        tmp.close()

        subprocess.run(["aplay", "-D", PLAYBACK_DEVICE, tmp.name], capture_output=True)
        os.unlink(tmp.name)
    except Exception:
        pass  # 提示音失败不影响主流程


if __name__ == "__main__":
    main()
