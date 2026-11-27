# Dreame FP10 空气净化器接入说明（v2.0.0）

`custom_components/dreame_airpurifier` 是面向追觅宠物空气净化器 FP10（`dreame.airp.u2513`）的 Home Assistant 自定义集成，已升级至 `cloud_push` 实时推送架构并完整适配 `1.9.3_1072` 新固件（同时兼容旧版 `1.8.x` 固件）。

## 核心特性

- **Dreame 云端 MQTT 实时推送（`cloud_push`）**：基于 `aiomqtt` 建立 TLS 长连接订阅 `properties_changed` 与 `_otc.info`，状态变化秒级同步；连接正常时 HTTP 兜底轮询自动降频至 300 秒，断线自动切回配置间隔并指数退避重连。
- **双固件自动适配**：自动读取设备固件版本并写入 HA 设备信息，自动兼容新旧点位差异（童锁 `6.10` / `2.5`、按键音 `6.17` / `6.7`）。
- **全功能实体覆盖**：
  - `fan`：开关机、1–10 真实风速百分比映射、净化预设模式（兼容 HomeKit Bridge）。
  - `number`：风速（1–10）、定时关机（0–12 小时）。
  - `select`：净化模式、氛围灯亮度（关闭/微亮/自然/明亮）、氛围灯色温（2700K/4000K/5700K，需 `1.9.3_1072` 及以上固件）。
  - `switch`：童锁、氛围灯呼吸模式、按键提示音。
  - `button`：开始自清洁、确认自清洁完成；HEPA 滤芯重置与集毛盒重置（默认禁用防误触）。
  - `sensor`（17 项）：PM2.5、PM10、TVOC、综合空气质量、空气质量等级、屏显数值、当前风速、温度、湿度、自清洁状态、HEPA 寿命/剩余天数、集毛盒寿命/剩余天数、运行状态、故障代码、Wi-Fi 信号强度（RSSI）。
  - `binary_sensor`：云端实时推送链路状态诊断。
- **平滑升级**：从 `v1.0.0` 升级时保留 `DOMAIN`、设备标识与全部 17 个既有实体 `unique_id`，不影响现有自动化与看板。

## 安装与配置

1. 通过 HACS 添加自定义仓库 `https://github.com/sxzcy/dreame_airpurifier`（分类选 `Integration`），或手动复制 `custom_components/dreame_airpurifier` 到 HA 的 `config/custom_components/`。
2. 重启 Home Assistant。
3. 在 **设置 -> 设备与服务 -> 添加集成** 中搜索 **Dreame FP10 Air Purifier**。
4. 使用 Dreame Smart Life 账号登录（区域默认选“自动识别”即可），选择你的 FP10 设备。

## 离线探测工具

仓库保留了 `tools/dreame_airpurifier_probe.py`，可用于排查新批次或新固件的属性点位：

```powershell
python tools/dreame_airpurifier_probe.py --username 你的账号 --password 你的密码 --region cn --device-index 0 --max-siid 8 --max-piid 17
```
