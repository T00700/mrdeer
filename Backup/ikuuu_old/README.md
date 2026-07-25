# ikuuu.win 青龙面板签到脚本 (Cookie 模式)

使用 Cookie 直接签到，无需验证码。

## 文件说明

```
ikuuu/
├── ikuuu_checkin.py    # 主脚本（Cookie 签到）
├── requirements.txt    # Python 依赖列表
└── .env.example        # 环境变量配置模板
```

## 部署步骤

### 1. 上传文件到青龙面板

在青龙面板 → **文件管理** 中新建文件夹 `ikuuu`，上传：

- `ikuuu_checkin.py`
- `requirements.txt`

### 2. 安装依赖

青龙面板 → **依赖管理** → 添加 `requests`

### 3. 获取 Cookie

1. 浏览器登录 ikuuu（`https://ikuuu.win`）
2. 按 **F12** → 切换到 **Application** 标签
3. 左侧展开 **Cookies** → 选择 `https://ikuuu.win`
4. 复制 **Name** 和 **Value** 列的所有键值对
5. 格式：`email=xxx; expire_in=xxx; ip=xxx; key=xxx; uid=xxx`

例如：
```
email=xxx; expire_in=xxx; ip=xxx; key=xxx; uid=xxx
```

### 4. 配置环境变量

青龙面板 → **环境变量** → 新建：

| 变量名 | 变量值 |
|---|---|
| `IKUUU_COOKIE` | 粘贴上面复制的 Cookie 字符串 |

多账号用换行分隔。

### 5. 添加定时任务

青龙面板 → **定时任务** → **添加任务**：

| 项 | 值 |
|---|---|
| 名称 | ikuuu签到 |
| 命令 | `python3 /ql/data/scripts/ikuuu/ikuuu_checkin.py` |
| 定时规则 | `0 8 * * *`（每天 8:00） |
| 时区 | Asia/Shanghai |

### 6. 手动测试

```bash
python3 /ql/data/scripts/ikuuu/ikuuu_checkin.py
```

## 输出示例

```
============================================================
🚀 ikuuu.win 青龙面板签到脚本 (Cookie 模式)
🌐 域名: https://ikuuu.win
============================================================

📋 [1/1] 处理账号...
👤 账号: d****n@gmail.com
🔍 验证 Cookie...
✅ Cookie 有效
📝 执行签到...
✅ 签到成功: 签到成功

============================================================
📊 签到完成: 成功 1/1, 失败 0/1
============================================================
```

## 常见问题

**Q: Cookie 从哪里获取？**

A: 浏览器登录 ikuuu → F12 → **Application** → **Cookies** → `https://ikuuu.win` → 复制所有 Name 和 Value

**Q: 提示 Cookie 已失效？**

A: Cookie 有过期时间，失效后需要重新获取。建议每 1-2 周刷新一次

**Q: 如何刷新 Cookie？**

A: 重新登录 ikuuu，按上述步骤复制新的 Cookie 更新环境变量

**Q: 支持多账号吗？**

A: 支持，在 `IKUUU_COOKIE` 环境变量中用换行分隔多个 Cookie
