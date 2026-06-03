#!/usr/bin/env python3
"""
简易串口监控工具
用法: source .venv/bin/activate && python3 scripts/serial_monitor.py
按 Ctrl+C 退出
"""

import serial
import sys
import time
import threading

PORT = "/dev/cu.usbmodem21101"
BAUD = 115200


def reader(ser):
    """读取串口数据的线程"""
    while True:
        try:
            if ser.in_waiting:
                data = ser.read(ser.in_waiting)
                text = data.decode("utf-8", errors="replace")
                sys.stdout.write(text)
                sys.stdout.flush()
            else:
                time.sleep(0.01)
        except (serial.SerialException, OSError):
            print("\n[连接断开]")
            break


def main():
    print(f"[串口监控] 端口: {PORT} 波特率: {BAUD}")
    print("[按 Ctrl+C 退出]\n")
    
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except Exception as e:
        print(f"无法打开串口: {e}")
        return 1
    
    # 启动读取线程
    t = threading.Thread(target=reader, args=(ser,), daemon=True)
    t.start()
    
    # 主线程处理用户输入
    try:
        while True:
            line = input()
            ser.write((line + "\r\n").encode())
    except KeyboardInterrupt:
        print("\n[退出]")
    except EOFError:
        # 等待读取线程
        t.join(timeout=2)
    finally:
        ser.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
