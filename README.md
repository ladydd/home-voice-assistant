# ESP32 工作区总览

家庭语音助手 + ESP32 学习项目的文档集合。

---

## 两个项目（分开做，都要搞）

### 🚀 项目 A：即用语音助手
**满足功能需求 —— 不写代码，今晚能用。**
麦克风和音响直接插家庭服务器，Hermes 自带语音能力搞定一切。
→ 详见 [`PROJECT_A_即用语音助手.md`](PROJECT_A_即用语音助手.md)

### 🛠️ 项目 B：ESP32 无线麦克风
**学习 ESP32 开发 —— 要写固件，循序渐进。**
用 XIAO ESP32-S3 Sense 做无线拾音终端，替代项目 A 的 USB 麦克风。
→ 详见 [`PROJECT_B_ESP32无线麦克风.md`](PROJECT_B_ESP32无线麦克风.md)

> 关系：项目 A 先把服务端语音链路跑通；项目 B 复用这套服务端，
> 只是把麦克风换成无线的 ESP32。功能和学习两不误。

---

## 硬件资料文档

| 文档 | 内容 |
|------|------|
| [`BOARD_INFO.md`](BOARD_INFO.md) | 开发板硬件信息、引脚映射、分区表 |
| [`TEST_REPORT.md`](TEST_REPORT.md) | 开发板全面测试报告（7 项全通过）|
| [`QUICKSTART.md`](QUICKSTART.md) | 开发环境搭建、烧录/监控命令 |

## 工具脚本（scripts/）

| 脚本 | 用途 |
|------|------|
| `board_test.py` | 一键全面测试开发板 |
| `serial_monitor.py` | 简易串口监控 |
| `flash_backup.py` | Flash 备份 / 恢复 |

环境：`.venv/`（已装 esptool + pyserial），用前 `source .venv/bin/activate`

---

## 设备速查

| 设备 | 关键信息 |
|------|---------|
| 开发板 | Seeed Studio XIAO ESP32-S3 Sense |
| 芯片 | ESP32-S3，双核 240MHz，8MB PSRAM，8MB Flash |
| 串口 | `/dev/cu.usbmodem21101` |
| 无线 | WiFi + BLE（**注意：无经典蓝牙**）|
| 板载 | PDM 麦克风 + OV2640 摄像头 |

---

## 当前进度

- [x] 开发板识别、测试、资料整理
- [x] 需求分析、方案设计（拆成项目 A / B）
- [ ] 项目 A：服务端语音链路跑通
- [ ] 项目 B：ESP32 固件开发（Phase 0 起步）

日期：2026-06-01
