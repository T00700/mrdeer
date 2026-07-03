# AnyRouter 签到脚本 - 青龙面板适配版

自动签到 AnyRouter 平台，支持多种通知方式。

## 功能特性

- 自动获取 WAF cookies，绕过平台防护
- 多账号支持
- 智能签到判断（通过余额变化判断上次签到是否成功）
- 支持多种通知方式（钉钉、飞书、Telegram、Bark、邮箱）
- 余额追踪和记录

## 环境要求

- Python 3.8+
- 青龙面板 (QingLong Panel)

## 安装步骤

### 1. 上传脚本到青龙面板

将 `checkin.py` 文件上传到青龙面板的脚本目录。

### 2. 安装依赖

青龙面板需要按以下方式安装依赖：

#### Python 依赖（在"Python3 依赖"中添加）

将以下内容添加到青龙面板的 **Python3 依赖** 管理中：

```
httpx>=0.27.0
playwright>=1.44.0
```

或在终端执行：
```bash
py3 install httpx playwright
```

#### Chromium 浏览器（必须在终端执行）

```bash
playwright install chromium
```

> **重要**：只安装 Python 包是不够的，必须执行此命令下载 Chromium 浏览器。

#### 系统依赖（在"Linux 依赖"中添加）

如果执行 `playwright install chromium` 时报错缺少系统库，将以下内容添加到青龙面板的 **Linux 依赖** 管理中：

```
nss libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 libglib2.0-0 fonts-noto-cjk
```

或在终端执行（自动安装系统依赖）：
```bash
playwright install --with-deps chromium
```

### 3. 配置环境变量

在青龙面板的"环境变量"页面添加以下变量：

#### 必填变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `ANYROUTER_ACCOUNTS` | 账号配置 JSON 数组 | 见下方格式 |

#### 账号配置格式

```json
[
  {
    "name": "我的主账号",
    "cookies": {
      "session": "你的session值"
    },
    "api_user": "12345"
  },
  {
    "name": "备用账号",
    "cookies": {
      "session": "另一个session值"
    },
    "api_user": "67890"
  }
]
```

**如何获取配置信息：**

1. 登录 [AnyRouter](https://anyrouter.top)
2. 打开浏览器开发者工具 (F12)
3. 切换到 Network 标签
4. 刷新页面，找到任意 API 请求
5. 从 Request Headers 中复制 `new-api-user` 的值作为 `api_user`
6. 从 Cookies 中复制 `session` 的值

#### 可选通知变量

**钉钉通知：**
```
DINGTALK_NOTIF_CONFIG={"webhook":"https://oapi.dingtalk.com/robot/send?access_token=xxx"}
```

**飞书通知：**
```
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
```

**Telegram 通知：**
```
TELEGRAM_NOTIF_CONFIG={"bot_token":"123456:ABCdefGHIjklMNOpqrsTUVwxyz","chat_id":"987654321"}
```

**Bark 通知 (iOS)：**
```
BARK_NOTIF_CONFIG={"server":"https://api.day.app/your_key"}
```

## 设置定时任务

在青龙面板中添加定时任务：

```
0 8 * * *
```

每天北京时间 8:00 执行签到。

## 文件说明

```
checkin.py          # 主脚本
requirements.txt    # Python 依赖列表
README.md           # 本说明文档
```

## 注意事项

1. 签到间隔为 24 小时，频繁签到不会重复获得奖励
2. 脚本会自动判断余额变化，避免重复签到
3. 如遇 WAF 获取失败，请检查网络连接
4. session cookie 有有效期，过期后需要重新获取

## 参考项目

- [millylee/anyrouter-check-in](https://github.com/millylee/anyrouter-check-in)
- [rakuyoMo/autocheck-anyrouter](https://github.com/rakuyoMo/autocheck-anyrouter)
