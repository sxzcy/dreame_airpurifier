# Dreame 空气净化器 FP10 接入说明

我已经在工作区生成了一个 Home Assistant 自定义集成：

- `custom_components/dreame_smartlife`

## 目前已经打通的部分

- Dreame Smart Life 云端登录
- 设备列表读取
- 设备选择
- `props` 状态轮询
- `sendCommand` 原始命令通道
- `dreame_smartlife.send_raw_command` 服务
- FP10 默认映射

## 现在怎么用

1. 把 `custom_components/dreame_smartlife` 复制到你的 HA 配置目录。
2. 重启 HA。
3. 在 HA 里添加集成 `Dreame Air Purifier FP10`。
4. 输入 Dreame Smart Life 账号、密码、区域，例如 `eu` / `us` / `cn`。
5. 在设备列表里选中你的 FP10 空气净化器。
6. 添加完成后，进入集成选项页。
7. 如有需要，手工调整各项映射 JSON。

## 适用范围

这个仓库目前是按 FP10 空气净化器适配的，对应模型：

- `dreame.airp.u2513`

之所以还保留手工映射，是因为不同批次或后续变种机型，具体 `siid/piid` 仍可能有差异。

当前已知重点点位包括：

- 开关机
- 模式
- 风速
- PM2.5
- TVOC
- 温湿度
- 负离子
- 灯光
- 滤芯寿命

这些点位，APK 里没有直接给出完整映射，所以我保留了手工映射能力。

## 额外的离线工具

我还加了一个本地命令行脚本：

- `tools/dreame_smartlife_probe.py`

它可以：

- 登录 Dreame Smart Life
- 列设备
- 指定设备探测属性
- 输出候选 `sensor_mappings / switch_mappings`

示例：

```powershell
python tools/dreame_smartlife_probe.py --username 你的账号 --password 你的密码 --region eu --device-index 0 --max-siid 8 --max-piid 16
```

## 映射怎么配

在集成的 Options 里可以填：

- `watched_keys`
  - 逗号分隔，例如：`2.1,2.2,4.1,4.2`
- `sensor_mappings`
  - JSON
- `switch_mappings`
  - JSON
- `select_mappings`
  - JSON
- `fan_power_key`
- `fan_speed_key`
- `fan_speed_map`

示例在：

- `custom_components/dreame_smartlife/README.md`

## 现在的建议

如果你用的是 FP10，直接使用当前仓库即可。如果后续还有额外功能点需要补，再继续补映射。
