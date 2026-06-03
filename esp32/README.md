# ESP32 无线麦克风终端（规划中）

用 XIAO ESP32-S3 Sense 做无线拾音终端，替代 USB 麦克风，放在家里任意位置。

## 硬件

- Seeed Studio XIAO ESP32-S3 Sense
- 双核 240MHz + 8MB PSRAM + 8MB Flash
- 板载 PDM 麦克风 + OV2640 摄像头
- WiFi + BLE

## 当前状态

- [x] 硬件识别和测试（全部通过）
- [x] 资料整理（引脚、分区表、开发环境）
- [ ] 固件开发
- [ ] 对接 voice-hermes 服务端

## 文件说明

| 文件 | 内容 |
|------|------|
| `BOARD_INFO.md` | 硬件信息、引脚映射、分区表 |
| `QUICKSTART.md` | 开发环境搭建、烧录命令 |
| `TEST_REPORT.md` | 全面硬件测试报告 |
| `PROJECT_B_ESP32无线麦克风.md` | 项目规划和方案设计 |
| `scripts/` | 板子测试/备份/监控脚本 |
