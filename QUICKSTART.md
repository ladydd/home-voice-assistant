# 快速开始指南

## 环境准备

### 已安装的工具 (本目录 .venv)

```bash
# 激活虚拟环境
source .venv/bin/activate

# 可用工具
esptool          # Flash 烧录/读取工具
python3          # Python 3 + pyserial
```

### 常用 esptool 命令

```bash
# 激活环境
source .venv/bin/activate

# 查看芯片信息
esptool --port /dev/cu.usbmodem21101 chip-id

# 查看 Flash 信息
esptool --port /dev/cu.usbmodem21101 flash-id

# 擦除整个 Flash
esptool --port /dev/cu.usbmodem21101 erase-flash

# 烧录固件 (Arduino 编译产物)
esptool --port /dev/cu.usbmodem21101 --baud 921600 \
  write-flash 0x0 firmware.bin

# 烧录分区固件 (ESP-IDF 标准布局)
esptool --port /dev/cu.usbmodem21101 --baud 921600 \
  write-flash \
  0x0000 bootloader.bin \
  0x8000 partition-table.bin \
  0x10000 app.bin

# 读取 Flash 内容
esptool --port /dev/cu.usbmodem21101 read-flash 0x0 0x800000 full_flash_backup.bin

# 监控串口输出
python3 -m serial.tools.miniterm /dev/cu.usbmodem21101 115200
```

---

## 开发框架选择

### 方案 1: Arduino IDE / Arduino CLI

最简单的入门方式，适合快速原型开发。

```bash
# 安装 Arduino CLI (如果没有)
brew install arduino-cli

# 添加 ESP32 板支持
arduino-cli config init
arduino-cli config add board_manager.additional_urls \
  https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
arduino-cli core update-index
arduino-cli core install esp32:esp32

# 编译示例
arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32S3 sketch/

# 上传
arduino-cli upload --fqbn esp32:esp32:XIAO_ESP32S3 --port /dev/cu.usbmodem21101 sketch/
```

**Arduino FQBN**: `esp32:esp32:XIAO_ESP32S3`

常用编译选项:
- `UploadSpeed=921600`
- `USBMode=hwcdc`
- `CDCOnBoot=default`
- `CPUFreq=240`
- `FlashMode=qio`
- `FlashSize=8M`
- `PartitionScheme=default_8MB`
- `PSRAM=enabled` (推荐启用)

### 方案 2: ESP-IDF (官方 SDK)

功能最完整，适合产品级开发。

```bash
# 安装 ESP-IDF
mkdir -p ~/esp
cd ~/esp
git clone -b v5.4 --recursive https://github.com/espressif/esp-idf.git
cd esp-idf
./install.sh esp32s3

# 每次使用前 source
source ~/esp/esp-idf/export.sh

# 创建项目
idf.py create-project my_project
cd my_project

# 配置目标芯片
idf.py set-target esp32s3

# 菜单配置
idf.py menuconfig

# 编译
idf.py build

# 烧录
idf.py -p /dev/cu.usbmodem21101 flash

# 监控
idf.py -p /dev/cu.usbmodem21101 monitor
```

### 方案 3: PlatformIO

适合 VS Code 用户，集成度高。

```ini
; platformio.ini
[env:seeed_xiao_esp32s3]
platform = espressif32
board = seeed_xiao_esp32s3
framework = arduino
monitor_speed = 115200
upload_port = /dev/cu.usbmodem21101
monitor_port = /dev/cu.usbmodem21101
board_build.arduino.memory_type = qio_opi
board_build.psram = enabled
```

### 方案 4: MicroPython

适合快速脚本开发和教学。

```bash
# 下载 MicroPython 固件
# https://micropython.org/download/ESP32_GENERIC_S3/

# 擦除并烧录 MicroPython
source .venv/bin/activate
esptool --port /dev/cu.usbmodem21101 erase-flash
esptool --port /dev/cu.usbmodem21101 --baud 921600 \
  write-flash 0x0 ESP32_GENERIC_S3-*.bin

# 连接 REPL
python3 -m serial.tools.miniterm /dev/cu.usbmodem21101 115200
```

---

## 串口监控

```bash
# 方法 1: pyserial miniterm (已安装)
source .venv/bin/activate
python3 -m serial.tools.miniterm /dev/cu.usbmodem21101 115200

# 方法 2: screen
screen /dev/cu.usbmodem21101 115200

# 退出 screen: Ctrl+A, 然后按 K, 然后 Y
```

---

## 注意事项

1. **USB-JTAG 模式**: 这块板子使用内置 USB-JTAG，不需要外部 USB-TTL 转换器
2. **自动下载**: esptool 可以自动触发下载模式，通常不需要手动按 BOOT 按钮
3. **如果串口消失**: 烧录某些固件后 USB-JTAG 可能被禁用，需要手动进入下载模式:
   - 按住 BOOT 按钮
   - 按一下 RESET 按钮
   - 松开 BOOT 按钮
4. **PSRAM**: 板子有 8MB PSRAM，使用摄像头或大内存应用时记得在配置中启用
5. **摄像头**: Sense 版本自带 OV2640，使用 Arduino CameraWebServer 示例可快速验证
