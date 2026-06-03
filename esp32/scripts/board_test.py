#!/usr/bin/env python3
"""
ESP32-S3 开发板全面测试脚本
用法: source .venv/bin/activate && python3 scripts/board_test.py
"""

import serial
import time
import subprocess
import sys
import json

PORT = "/dev/cu.usbmodem21101"
BAUD = 115200


def run_esptool(args):
    """运行 esptool 命令并返回输出"""
    cmd = ["esptool", "--port", PORT] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout + result.stderr


def test_connection():
    """测试串口连接"""
    print("\n[1/7] 串口连接测试...")
    try:
        ser = serial.Serial(PORT, BAUD, timeout=2)
        ser.close()
        print("  ✅ 串口连接成功")
        return True
    except Exception as e:
        print(f"  ❌ 串口连接失败: {e}")
        return False


def test_chip_id():
    """测试芯片识别"""
    print("\n[2/7] 芯片识别测试...")
    output = run_esptool(["chip-id"])
    if "ESP32-S3" in output:
        print("  ✅ 芯片识别成功: ESP32-S3")
        # 提取关键信息
        for line in output.split("\n"):
            if any(k in line for k in ["Chip type", "Features", "Crystal", "MAC"]):
                print(f"     {line.strip()}")
        return True
    else:
        print(f"  ❌ 芯片识别失败")
        return False


def test_flash():
    """测试 Flash"""
    print("\n[3/7] Flash 测试...")
    output = run_esptool(["flash-id"])
    if "Detected flash size" in output:
        for line in output.split("\n"):
            if any(k in line for k in ["Manufacturer", "Device", "flash size", "Flash type", "voltage"]):
                print(f"     {line.strip()}")
        print("  ✅ Flash 识别成功")
        return True
    else:
        print("  ❌ Flash 识别失败")
        return False


def test_serial_throughput():
    """测试串口吞吐量"""
    print("\n[4/7] 串口吞吐量测试...")
    try:
        ser = serial.Serial(PORT, BAUD, timeout=2)
        test_data = b"A" * 1024
        start = time.time()
        for _ in range(10):
            ser.write(test_data)
        elapsed = time.time() - start
        throughput = 10240 / elapsed
        ser.close()
        print(f"  ✅ TX 吞吐量: {throughput/1024:.1f} KB/s ({throughput*8/1000:.0f} kbps)")
        return True
    except Exception as e:
        print(f"  ❌ 吞吐量测试失败: {e}")
        return False


def test_stability():
    """测试连接稳定性"""
    print("\n[5/7] 连接稳定性测试 (20次快速连接)...")
    success = 0
    for _ in range(20):
        try:
            s = serial.Serial(PORT, BAUD, timeout=0.5)
            s.write(b"ping\r\n")
            time.sleep(0.02)
            s.close()
            success += 1
        except:
            pass
        time.sleep(0.02)
    
    if success == 20:
        print(f"  ✅ 稳定性测试通过: {success}/20")
    else:
        print(f"  ⚠️  稳定性测试: {success}/20 (有失败)")
    return success >= 18


def test_boot():
    """测试启动输出"""
    print("\n[6/7] 启动测试 (复位板子)...")
    try:
        ser = serial.Serial(PORT, BAUD, timeout=3)
        ser.dtr = False
        ser.rts = True
        time.sleep(0.1)
        ser.rts = False
        time.sleep(2)
        
        data = b""
        start = time.time()
        while time.time() - start < 3:
            if ser.in_waiting:
                data += ser.read(ser.in_waiting)
            time.sleep(0.05)
        ser.close()
        
        output = data.decode("utf-8", errors="replace")
        if "ESP-ROM" in output:
            print("  ✅ 启动正常")
            for line in output.split("\n")[:5]:
                if line.strip():
                    print(f"     {line.strip()}")
            return True
        else:
            print("  ⚠️  未捕获到启动信息 (可能需要手动复位)")
            return False
    except Exception as e:
        print(f"  ❌ 启动测试失败: {e}")
        return False


def test_security():
    """测试安全状态"""
    print("\n[7/7] 安全状态检查...")
    output = run_esptool(["get-security-info"])
    secure_boot = "Disabled" if "Secure Boot: Disabled" in output else "Enabled"
    flash_enc = "Disabled" if "Flash Encryption: Disabled" in output else "Enabled"
    
    print(f"     Secure Boot: {secure_boot}")
    print(f"     Flash Encryption: {flash_enc}")
    
    if secure_boot == "Disabled" and flash_enc == "Disabled":
        print("  ✅ 芯片未锁定，可自由开发")
    else:
        print("  ⚠️  芯片有安全限制")
    return True


def main():
    print("=" * 50)
    print("  ESP32-S3 开发板全面测试")
    print(f"  端口: {PORT}")
    print(f"  时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    results = []
    results.append(("串口连接", test_connection()))
    results.append(("芯片识别", test_chip_id()))
    results.append(("Flash", test_flash()))
    results.append(("串口吞吐", test_serial_throughput()))
    results.append(("连接稳定性", test_stability()))
    results.append(("启动流程", test_boot()))
    results.append(("安全状态", test_security()))
    
    print("\n" + "=" * 50)
    print("  测试总结")
    print("=" * 50)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name:<12} {status}")
    
    print(f"\n  总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n  🎉 所有测试通过！开发板状态良好。")
    else:
        print("\n  ⚠️  部分测试未通过，请检查连接。")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
