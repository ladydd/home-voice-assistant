#!/usr/bin/env python3
"""
备份/恢复 ESP32-S3 Flash 内容
用法:
  备份: source .venv/bin/activate && python3 scripts/flash_backup.py backup
  恢复: source .venv/bin/activate && python3 scripts/flash_backup.py restore backup_file.bin
"""

import subprocess
import sys
import time
import os

PORT = "/dev/cu.usbmodem21101"
FLASH_SIZE = "8MB"
FLASH_SIZE_BYTES = 8 * 1024 * 1024


def backup():
    """备份整个 Flash"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"flash_backup_{timestamp}.bin"
    
    print(f"开始备份 Flash ({FLASH_SIZE}) 到 {filename}")
    print("这可能需要几分钟...")
    
    cmd = [
        "esptool", "--port", PORT,
        "read-flash", "0x0", hex(FLASH_SIZE_BYTES), filename
    ]
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0 and os.path.exists(filename):
        size = os.path.getsize(filename)
        print(f"\n✅ 备份完成: {filename} ({size/1024/1024:.1f} MB)")
    else:
        print("\n❌ 备份失败")
        return 1
    return 0


def restore(filename):
    """恢复 Flash"""
    if not os.path.exists(filename):
        print(f"❌ 文件不存在: {filename}")
        return 1
    
    size = os.path.getsize(filename)
    print(f"准备恢复 Flash: {filename} ({size/1024/1024:.1f} MB)")
    print("⚠️  这将覆盖板子上所有数据！")
    
    confirm = input("确认恢复? (yes/no): ")
    if confirm.lower() != "yes":
        print("已取消")
        return 0
    
    # 先擦除
    print("擦除 Flash...")
    subprocess.run(["esptool", "--port", PORT, "erase-flash"])
    
    # 写入
    print("写入备份...")
    cmd = [
        "esptool", "--port", PORT, "--baud", "921600",
        "write-flash", "0x0", filename
    ]
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n✅ 恢复完成")
    else:
        print("\n❌ 恢复失败")
        return 1
    return 0


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  备份: python3 scripts/flash_backup.py backup")
        print("  恢复: python3 scripts/flash_backup.py restore <file.bin>")
        return 1
    
    action = sys.argv[1]
    
    if action == "backup":
        return backup()
    elif action == "restore":
        if len(sys.argv) < 3:
            print("请指定备份文件: python3 scripts/flash_backup.py restore <file.bin>")
            return 1
        return restore(sys.argv[2])
    else:
        print(f"未知操作: {action}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
