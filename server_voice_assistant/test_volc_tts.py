"""测试火山引擎 TTS - Vivi 2.0 陕西话"""
import requests
import json
import base64
import uuid

url = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
headers = {
    "Content-Type": "application/json",
    "X-Api-Key": "f103d3e6-118c-41ab-b2f5-99d7320d625e",
    "X-Api-Resource-Id": "seed-tts-2.0",
    "X-Api-Request-Id": str(uuid.uuid4()),
}

payload = {
    "user": {"uid": "voice-assistant"},
    "req_params": {
        "text": "兄弟，你说啥呢，我没听清楚，你再说一遍嘛。今天天气好得很，咱出去转转。",
        "speaker": "zh_female_vv_uranus_bigtts",
        "audio_params": {
            "format": "mp3",
            "sample_rate": 24000
        },
        "additions": json.dumps({
            "explicit_dialect": "shaanxi"
        })
    }
}

resp = requests.post(url, json=payload, headers=headers, stream=True, timeout=30)
print(f"Status: {resp.status_code}")

if resp.status_code == 200:
    audio_data = b""
    for line in resp.iter_lines():
        if line:
            try:
                obj = json.loads(line)
                if obj.get("data"):
                    audio_data += base64.b64decode(obj["data"])
                if obj.get("code") == 20000000:
                    print(f"TTS finished. Usage: {obj.get('usage')}")
            except:
                pass
    
    if audio_data:
        with open("/tmp/volc_tts_shaanxi.mp3", "wb") as f:
            f.write(audio_data)
        print(f"Audio saved: {len(audio_data)} bytes")
    else:
        print("No audio data received")
else:
    print(f"Error: {resp.text[:500]}")
