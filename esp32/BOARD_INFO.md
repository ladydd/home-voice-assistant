# Seeed Studio XIAO ESP32-S3 Sense 开发板信息

## 基本信息

| 项目 | 详情 |
|------|------|
| 开发板 | Seeed Studio XIAO ESP32-S3 Sense |
| 芯片 | ESP32-S3 (QFN56) revision v0.2 |
| CPU | Xtensa LX7 双核 + LP Core, 240MHz |
| 无线 | Wi-Fi 802.11 b/g/n, Bluetooth 5 (LE) |
| PSRAM | 8MB (内置, AP_3v3) |
| Flash | 8MB (GigaDevice, Quad, 3.3V) |
| 晶振 | 40MHz |
| USB 模式 | USB-Serial/JTAG (内置) |
| MAC 地址 | 1C:DB:D4:76:86:70 |

## 连接信息

| 项目 | 详情 |
|------|------|
| 串口设备 | `/dev/cu.usbmodem21101` |
| 备用路径 | `/dev/tty.usbmodem21101` |
| 默认波特率 | 115200 |
| 烧录波特率 | 921600 |
| USB 速度 | Full Speed (12 Mbps) |

## Flash 详情

| 项目 | 详情 |
|------|------|
| 容量 | 8MB |
| 厂商 | GigaDevice (Manufacturer ID: 0xC8) |
| Device ID | 0x4017 |
| 数据线 | Quad (4 data lines) |
| 电压 | 3.3V |
| SPI 模式 | DIO |

## 分区表

| 分区名 | 类型 | 偏移地址 | 大小 |
|--------|------|----------|------|
| nvs | data/nvs | 0x9000 | 20KB |
| otadata | data/ota | 0xE000 | 8KB |
| app0 | app/ota_0 | 0x10000 | 3264KB |
| app1 | app/ota_1 | 0x340000 | 3264KB |
| spiffs | data/spiffs | 0x670000 | 1536KB |
| coredump | data/coredump | 0x7F0000 | 64KB |

## 安全状态

| 项目 | 状态 |
|------|------|
| Secure Boot | 未启用 |
| Flash 加密 | 未启用 |
| eFuse Key Slots | 全部空闲 (USER/EMPTY) |

## 当前固件

| 项目 | 详情 |
|------|------|
| 类型 | Arduino (arduino-lib-builder) |
| ESP-IDF 版本 | v5.4.1 |
| 编译日期 | Mar 28, 2025 |
| Arduino FQBN | `esp32:esp32:XIAO_ESP32S3` |
| 功能 | 出厂测试固件 (WiFi扫描, BT扫描, 摄像头, GPIO测试) |

## 板载外设 (Sense 版本)

- OV2640 摄像头模块
- 数字麦克风
- SD 卡槽 (扩展板)
- 状态 LED
- 用户按钮 (BOOT)
- Reset 按钮

## GPIO 引脚映射 (XIAO ESP32-S3)

```
        ┌─────────┐
   D0  ─┤1      14├─ 5V
   D1  ─┤2      13├─ GND
   D2  ─┤3      12├─ 3V3
   D3  ─┤4      11├─ D10
   D4  ─┤5      10├─ D9
   D5  ─┤6       9├─ D8
   D6  ─┤7       8├─ D7
        └─────────┘
```

| Arduino Pin | GPIO | 功能 |
|-------------|------|------|
| D0 | GPIO1 | ADC1_CH0 |
| D1 | GPIO2 | ADC1_CH1 |
| D2 | GPIO3 | ADC1_CH2 |
| D3 | GPIO4 | ADC1_CH3 |
| D4 | GPIO5 | ADC1_CH4 |
| D5 | GPIO6 | ADC1_CH5 |
| D6 | GPIO43 | TX |
| D7 | GPIO44 | RX |
| D8 | GPIO7 | SCK/ADC1_CH6 |
| D9 | GPIO8 | MISO |
| D10 | GPIO9 | MOSI |
| SDA | GPIO5 | I2C Data |
| SCL | GPIO6 | I2C Clock |
| LED | GPIO21 | 内置 LED |
