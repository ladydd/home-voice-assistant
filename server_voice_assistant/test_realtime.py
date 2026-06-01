"""测试火山引擎端到端实时语音 - WebSocket 连接测试"""
import asyncio
import json
import struct
import uuid
import websockets

# 鉴权信息
APP_ID = "your-app-id"
ACCESS_KEY = "your-access-key"
RESOURCE_ID = "volc.speech.dialog"
APP_KEY = "PlgvMymc7f3tQnJ6"

WS_URL = "wss://openspeech.bytedance.com/api/v3/realtime/dialogue"


def build_event_frame(event_id, session_id=None, payload=None):
    """构建二进制事件帧"""
    # Header: protocol_version(4bit) + header_size(4bit) = 0x11
    # Message type(4bit) = 0001 (Full-client request) + flags(4bit) = 0100 (has event)
    # Serialization(4bit) = 0001 (JSON) + Compression(4bit) = 0000 (none)
    # Reserved = 0x00
    header = bytes([0x11, 0x14, 0x10, 0x00])

    # Event ID (4 bytes, big-endian)
    event_bytes = struct.pack(">I", event_id)

    # Session ID (if provided)
    session_bytes = b""
    if session_id:
        sid_encoded = session_id.encode("utf-8")
        session_bytes = struct.pack(">I", len(sid_encoded)) + sid_encoded

    # Payload
    if payload is None:
        payload_data = b"{}"
    elif isinstance(payload, dict):
        payload_data = json.dumps(payload).encode("utf-8")
    else:
        payload_data = payload.encode("utf-8")

    payload_size = struct.pack(">I", len(payload_data))

    return header + event_bytes + session_bytes + payload_size + payload_data


async def test_connection():
    """测试 WebSocket 连接"""
    headers = {
        "X-Api-App-ID": APP_ID,
        "X-Api-Access-Key": ACCESS_KEY,
        "X-Api-Resource-Id": RESOURCE_ID,
        "X-Api-App-Key": APP_KEY,
        "X-Api-Connect-Id": str(uuid.uuid4()),
    }

    print(f"Connecting to {WS_URL}...")
    try:
        async with websockets.connect(
            WS_URL,
            additional_headers=headers,
        ) as ws:
            print("✅ WebSocket connected!")

            # Send StartConnection (event_id=1)
            frame = build_event_frame(1)
            await ws.send(frame)
            print("Sent StartConnection")

            # Wait for ConnectionStarted (event_id=50)
            resp = await asyncio.wait_for(ws.recv(), timeout=5)
            print(f"Received: {len(resp)} bytes")
            # Parse event ID from response
            if len(resp) >= 8:
                resp_event = struct.unpack(">I", resp[4:8])[0]
                print(f"Event ID: {resp_event}")
                if resp_event == 50:
                    print("✅ ConnectionStarted received! 连接成功!")
                elif resp_event == 51:
                    print("❌ ConnectionFailed")
                    # Try to parse error
                    try:
                        payload_start = resp.find(b"{")
                        if payload_start >= 0:
                            error_json = json.loads(resp[payload_start:])
                            print(f"   Error: {error_json}")
                    except:
                        pass

            # Send FinishConnection (event_id=2)
            frame = build_event_frame(2)
            await ws.send(frame)
            print("Sent FinishConnection")

    except Exception as e:
        print(f"❌ Connection failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_connection())
