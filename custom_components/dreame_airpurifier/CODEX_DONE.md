# CODEX_DONE

执行端：win端

范围：仅处理 `D:\UserData\Desktop\codex\Ha\ha_custom_components_rewrite\work\custom_components\dreame_airpurifier`。

## 1. 本轮改动文件

- `__init__.py`
- `button.py`
- `config_flow.py`
- `const.py`
- `coordinator.py`
- `dreame/exceptions.py`
- `dreame/models.py`
- `dreame/protocol.py`
- `fan.py`
- `number.py`
- `sensor.py`
- `manifest.json`
- `strings.json`
- `translations/en.json`
- `translations/zh-Hans.json`
- `README.md`
- `services.yaml`
- `brand/icon.png`
- `brand/icon@2x.png`
- `brand/logo.png`
- `brand/logo@2x.png`

## 2. 每个文件主要改动

- `__init__.py`：卸载配置项时调用 coordinator 清理延迟刷新任务；错误提示文案统一为 `Dreame FP10 Air Purifier`。
- `button.py`：修正读取 `hass.data` 时使用的 domain，从旧的错误 domain 改为当前插件 domain。
- `config_flow.py`：增加 reauth 流程；增加 options 输入校验；空字符串选项不再无意覆盖默认映射。
- `const.py`：加入 `Platform.BUTTON`；默认设备名改为 `Dreame FP10`。
- `coordinator.py`：鉴权失败改为抛 `ConfigEntryAuthFailed`；卸载时可取消 follow-up refresh task；缓存读取更稳健。
- `dreame/exceptions.py`：新增命令失败异常类型，用于区分云端/API 成功但设备命令失败。
- `dreame/models.py`：修正默认映射合并逻辑；避免空 options 覆盖 FP10 默认映射；调整默认实体名称和图标；主风扇实体默认不再额外叫“净化器”。
- `dreame/protocol.py`：区分登录鉴权、网络/API、命令失败；校验 `set_properties` 和 `action` 返回结果；兼容不同命令返回结构。
- `fan.py`：去掉虚假的百分比调速能力；非法 preset 会明确失败；正百分比只执行开机，不再硬切“强净化”。
- `number.py`：number 映射的 min/max/step/mode 做容错处理。
- `sensor.py`：诊断实体改名为“调试信息”，图标改为 `mdi:tools`，并保持 diagnostic 且默认禁用。
- `manifest.json`：集成展示名改为 `Dreame FP10 Air Purifier`。
- `strings.json`：英文 UI 文案同步新名称；options 字段说明同步“显示名覆盖”语义。
- `translations/en.json`：英文翻译同步。
- `translations/zh-Hans.json`：中文翻译同步。
- `README.md`：文档名称和示例图标同步。
- `services.yaml`：服务描述中的产品名同步。
- `brand/icon.png`：新增 256x256 透明 PNG 主图标，用于 HA 集成品牌图标。
- `brand/icon@2x.png`：新增 512x512 透明 PNG 高清主图标。
- `brand/logo.png`：新增 640x160 透明 PNG 横向 logo。
- `brand/logo@2x.png`：新增 1280x320 透明 PNG 高清横向 logo。

## 3. 修复的问题

- 选项页保存空字符串会清空默认 FP10 映射，导致实体丢失。
- `button.py` 使用错误 domain，且 button 平台未加载。
- 鉴权失败只表现为普通更新失败，无法触发 HA reauth。
- 登录、网络、API、命令失败分类混乱，容易误报账号密码错误或假装写入成功。
- 写入属性/动作后未校验云端返回结果，可能本地状态假更新。
- 风扇实体声明了不真实的百分比调速能力。
- 诊断 sensor 属性较重，默认启用会增加 recorder 压力。
- number 映射中异常 mode 或数值配置可能导致实体创建失败。
- 默认实体命名和图标不够清晰，已统一为更适合 HA 设备页的风格。
- 插件缺少本地 brand 主图标，已补齐 `brand/` 透明 PNG 资产。

## 4. 未解决或仍需注意的风险

- 没有连接 HA，也没有在 HA 运行时加载测试；本地环境没有安装 `homeassistant` 包。
- Dreame 云端真实返回结构未在线验证；协议层已经做了更稳健的分支，但仍需生产前实测登录、轮询、开关机、模式切换。
- 现有 HA entity registry 可能保留旧实体显示名或旧 entity_id；代码默认名更新不一定覆盖用户曾手动改过的名称。
- 插件内仍保留原有 Dreame App 协议常量名，例如 app basic auth/salt 相关常量；本轮没有新增 token、账号密码、私钥或生产凭据。

## 5. 关键文件和兼容性确认

- `manifest.json`：已改，仅修改展示名。
- `translations/*.json`：已改，同步中英文显示文案。
- `strings.json`：已改，同步默认 UI 文案。
- `config_flow.py`：已改，增加 reauth 和 options 校验。
- 实体 `unique_id`：未改。仍使用原有 `did + platform/name` 结构。
- 设备注册逻辑：未改。`DeviceInfo.identifiers={(DOMAIN, descriptor.did)}` 保持不变。
- domain：未改。仍是 `dreame_airpurifier`。
- service 名：未改。仍是 `probe_properties` 和 `send_raw_command`。
- brand 资产：已新增。仅为展示图片，不改变配置项、实体、服务或设备注册逻辑。

## 6. 已运行检查

### JSON 解析

命令：

```powershell
$plugin = 'D:\UserData\Desktop\codex\Ha\ha_custom_components_rewrite\work\custom_components\dreame_airpurifier'
$jsonFiles = Get-ChildItem -LiteralPath $plugin -Recurse -File -Include '*.json'
foreach ($file in $jsonFiles) { Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json | Out-Null }
"JSON_OK count=$($jsonFiles.Count)"
```

结果：

```text
JSON_OK count=4
```

### Python 语法检查

命令：

```powershell
$plugin = 'D:\UserData\Desktop\codex\Ha\ha_custom_components_rewrite\work\custom_components\dreame_airpurifier'
$pyFiles = Get-ChildItem -LiteralPath $plugin -Recurse -File -Filter '*.py'
foreach ($file in $pyFiles) { python -m py_compile $file.FullName }
"PY_COMPILE_OK count=$($pyFiles.Count)"
```

结果：

```text
PY_COMPILE_OK count=17
```

### 缓存和临时文件清理确认

命令：

```powershell
$plugin = Resolve-Path -LiteralPath 'D:\UserData\Desktop\codex\Ha\ha_custom_components_rewrite\work\custom_components\dreame_airpurifier'
Get-ChildItem -LiteralPath $plugin -Recurse -Directory -Filter '__pycache__' |
  Where-Object { $_.FullName.StartsWith($plugin.Path, [System.StringComparison]::OrdinalIgnoreCase) } |
  Remove-Item -Recurse -Force
$cacheDirs = @(Get-ChildItem -LiteralPath $plugin -Recurse -Directory -Filter '__pycache__')
$pycFiles = @(Get-ChildItem -LiteralPath $plugin -Recurse -File -Include '*.pyc')
$tempFiles = @(Get-ChildItem -LiteralPath $plugin -Recurse -File -Include '*.tmp','*.bak','*.orig','*.rej','*~')
"CACHE_TEMP_OK __pycache__=$($cacheDirs.Count) pyc=$($pycFiles.Count) temp=$($tempFiles.Count)"
```

结果：

```text
CACHE_TEMP_OK __pycache__=0 pyc=0 temp=0
```

### Brand 图片资产确认

命令：

```powershell
Get-ChildItem -LiteralPath 'D:\UserData\Desktop\codex\Ha\ha_custom_components_rewrite\work\custom_components\dreame_airpurifier\brand' -File |
  Select-Object Name,Length,@{Name='Size';Expression={Add-Type -AssemblyName System.Drawing; $img=[System.Drawing.Image]::FromFile($_.FullName); try { "$($img.Width)x$($img.Height)" } finally { $img.Dispose() } }}
```

结果：

```text
icon.png      4834  256x256
icon@2x.png   9839  512x512
logo.png      4949  640x160
logo@2x.png  11498  1280x320
```

### 敏感信息检查

命令：

```powershell
$plugin = 'D:\UserData\Desktop\codex\Ha\ha_custom_components_rewrite\work\custom_components\dreame_airpurifier'
$matches = @(rg -n -i 'BEGIN .*PRIVATE KEY|private_key|access_token|refresh_token|api[_-]?key|secret|passwd|password|authorization|basic ' $plugin)
"SENSITIVE_SCAN_MATCHES count=$($matches.Count)"
```

结果：

```text
SENSITIVE_SCAN_MATCHES count=26
```

说明：命中项为代码字段名、翻译字段、协议变量名、既有 app 协议常量引用，以及本 `CODEX_DONE.md` 中的检查说明文字；未发现私钥正文、生产 token、生产密码、API key 文件或新增凭据。普通报告中不展开命中行，避免误打印敏感样式内容。

### HA 生产环境确认

- 未修改 HA 生产配置。
- 未连接 HA。
- 未重启 HA。
- 未执行 SSH、HA API、HA CLI、Docker/Compose、路由器、NAS 生产服务修改命令。

## 7. 替换到 HA 生产环境前重点验证

- 在测试或可回滚窗口替换插件后重启 HA，确认集成能正常加载，无 `ConfigEntryNotReady`、import error、translation error。
- 打开集成设备页，确认设备名、主风扇实体名、传感器名和图标符合预期。
- 确认已有 entity registry 是否保留旧名称；如果旧名称不更新，检查是否曾在 HA UI 手动改名。
- 验证登录失败时会进入重新认证，而不是反复普通轮询失败。
- 验证轮询数据：PM2.5、PM10、TVOC、滤芯寿命、运行状态、故障代码等实体值正常。
- 验证控制动作：开机、关机、净化模式、童锁、风速 number 写入后，云端失败时 HA 不应假显示成功。
- 验证诊断实体默认禁用；需要时手动启用“调试信息”查看属性。
- 检查 HA 日志中是否有 Dreame API 返回结构不匹配、未知图标或 entity setup 警告。
