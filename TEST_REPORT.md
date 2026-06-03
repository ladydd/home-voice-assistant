# ESP32-S3 开发板测试报告

测试日期: 2026-06-01  
测试设备: Seeed Studio XIAO ESP32-S3 Sense  
测试环境: macOS (Mac Mini M-series)

---

## 1. 连接测试

### USB 识别 ✅ 通过
- 设备正确识别为 Espressif USB JTAG/serial debug unit
- 串口设备: `/dev/cu.usbmodem21101`
- USB Full Speed (12 Mbps) 连接正常

### 串口通信 ✅ 通过
- 115200 波特率通信正常
- 数据收发无误
- DTR/RTS 信号控制正常

### 连接稳定性 ✅ 通过
- 20次快速连接/断开循环: 全部成功 (20/20)
- 无连接丢失或超时

### 串口吞吐量 ✅ 通过
- TX 吞吐量: ~789 KB/s (6461 kbps)
- USB CDC 虚拟串口性能正常

---

## 2. 芯片识别测试

### chip-id ✅ 通过
```
Chip type:       ESP32-S3 (QFN56) (revision v0.2)
Features:        Wi-Fi, BT 5 (LE), Dual Core + LP Core, 240MHz, Embedded PSRAM 8MB
Crystal:         40MHz
USB mode:        USB-Serial/JTAG
MAC:             1c:db:d4:76:86:70
```

### flash-id ✅ 通过
```
Manufacturer:    0xC8 (GigaDevice)
Device:          0x4017
Flash size:      8MB
Flash type:      Quad (4 data lines)
Flash voltage:   3.3V
```

---

## 3. Flash 读取测试

### Bootloader 读取 ✅ 通过
- 地址 0x0000: 有效 ESP-IDF bootloader (magic=0xE9)
- 4 个段, 入口点 0x403c88b8
- SPI 模式: DIO

### 分区表读取 ✅ 通过
- 地址 0x8000: 有效分区表
- 6 个分区, 支持 OTA 双分区

### 应用固件读取 ✅ 通过
- 地址 0x10000: 有效应用镜像
- 项目: arduino-lib-builder (出厂测试固件)
- IDF 版本: v5.4.1

---

## 4. 安全信息测试

### get-security-info ✅ 通过
```
Secure Boot:     Disabled
Flash Encryption: Disabled
Key Purposes:    All USER/EMPTY (未使用)
Chip ID:         9
```

芯片处于完全开放状态，可自由开发和烧录。

---

## 5. 启动测试

### 复位启动 ✅ 通过
```
ESP-ROM:esp32s3-20210327
Build:Mar 27 2021
rst:0x15 (USB_UART_CHIP_RESET),boot:0x8 (SPI_FAST_FLASH_BOOT)
...
Hello from Seeed Studio XIAO ESP32-S3 Sense
```

- ROM 版本: esp32s3-20210327
- 启动模式: SPI_FAST_FLASH_BOOT
- 固件正常运行，输出心跳信号 (`.` 每秒)

---

## 6. esptool 烧录通道测试

### 自动复位进入下载模式 ✅ 通过
- esptool 可通过 USB-JTAG 自动进入下载模式
- 无需手动按 BOOT 按钮
- Stub flasher 加载成功

### Flash 读写速度
- 读取速度: ~91 kbit/s (通过 stub flasher)
- 烧录通道就绪，可随时写入新固件

---

## 7. 多波特率测试

| 波特率 | 状态 |
|--------|------|
| 9600 | ✅ 通信正常 |
| 19200 | ✅ 通信正常 |
| 38400 | ✅ 通信正常 |
| 57600 | ✅ 连接正常 |
| 115200 | ✅ 连接正常 (默认) |
| 230400 | ✅ 通信正常 |
| 460800 | ✅ 通信正常 |
| 921600 | ✅ 连接正常 (烧录用) |

---

## 测试总结

| 测试类别 | 结果 |
|----------|------|
| USB 连接 | ✅ 通过 |
| 串口通信 | ✅ 通过 |
| 连接稳定性 | ✅ 通过 |
| 芯片识别 | ✅ 通过 |
| Flash 识别 | ✅ 通过 |
| 分区表 | ✅ 通过 |
| 固件完整性 | ✅ 通过 |
| 安全状态 | ✅ 通过 |
| 启动流程 | ✅ 通过 |
| 烧录通道 | ✅ 通过 |
| 信号控制 | ✅ 通过 |

**结论: 开发板硬件状态良好，所有通信通道正常，可以开始开发。**

---

## 使用的工具

- esptool v5.2.0
- pyserial 3.5
- Python 3 虚拟环境 (`.venv/`)
