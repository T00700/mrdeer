#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AnyRouter 签到脚本 - 适配青龙面板
参考: https://github.com/millylee/anyrouter-check-in
      https://github.com/rakuyoMo/autocheck-anyrouter
"""

import json
import os
import sys
import time
import hashlib
import logging
import urllib.parse
from datetime import datetime, timedelta

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 尝试导入依赖
try:
    import httpx
except ImportError:
    logger.error("未安装 httpx，请在青龙面板执行: py3 install httpx")
    sys.exit(1)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    logger.error("未安装 playwright，请在青龙面板执行: py3 install playwright && playwright install chromium")
    sys.exit(1)


# ==================== 环境检测 ====================

def check_environment():
    """检测运行环境，提示缺失的依赖"""
    # 检测 Playwright 浏览器是否安装
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch()
    except Exception as e:
        error_msg = str(e)
        if 'Executable doesn\'t exist' in error_msg or 'browser not installed' in error_msg.lower():
            logger.error("=" * 60)
            logger.error("Playwright 浏览器未安装！")
            logger.error("=" * 60)
            logger.error("请在青龙面板终端执行以下命令安装浏览器：")
            logger.error("")
            logger.error("  playwright install chromium")
            logger.error("")
            logger.error("如果上述命令失败，可以尝试安装所有浏览器：")
            logger.error("  playwright install")
            logger.error("=" * 60)
            sys.exit(1)
        else:
            # 其他错误，继续运行
            pass


# ==================== 通知模块 ====================

class Notifier:
    """通知推送类，支持多种通知方式"""

    def __init__(self):
        self.enabled = False
        self.notif_config = {}

        # 读取通知配置
        dingtalk_config = os.getenv('DINGTALK_NOTIF_CONFIG', '').strip()
        if dingtalk_config:
            try:
                self.notif_config['dingtalk'] = json.loads(dingtalk_config)
                self.enabled = True
            except json.JSONDecodeError:
                # 兼容简单 webhook 格式
                self.notif_config['dingtalk'] = {'webhook': dingtalk_config}
                self.enabled = True

        telegram_config = os.getenv('TELEGRAM_NOTIF_CONFIG', '').strip()
        if telegram_config:
            try:
                self.notif_config['telegram'] = json.loads(telegram_config)
                self.enabled = True
            except json.JSONDecodeError:
                pass

        bark_config = os.getenv('BARK_NOTIF_CONFIG', '').strip()
        if bark_config:
            try:
                self.notif_config['bark'] = json.loads(bark_config)
                self.enabled = True
            except json.JSONDecodeError:
                pass

        email_config = os.getenv('EMAIL_NOTIF_CONFIG', '').strip()
        if email_config:
            try:
                self.notif_config['email'] = json.loads(email_config)
                self.enabled = True
            except json.JSONDecodeError:
                pass

        # 兼容旧版环境变量格式
        dingding_webhook = os.getenv('DINGDING_WEBHOOK', '').strip()
        if dingding_webhook and 'dingtalk' not in self.notif_config:
            self.notif_config['dingtalk'] = {'webhook': dingding_webhook}
            self.enabled = True

        feishu_webhook = os.getenv('FEISHU_WEBHOOK', '').strip()
        if feishu_webhook:
            self.notif_config['feishu'] = {'webhook': feishu_webhook}
            self.enabled = True

    def send(self, title, content, trigger='checkin'):
        """发送通知"""
        if not self.enabled:
            return

        message = f"{title}\n\n{content}"

        # 钉钉通知
        if 'dingtalk' in self.notif_config:
            self._send_dingtalk(message)

        # 飞书通知
        if 'feishu' in self.notif_config:
            self._send_feishu(title, message)

        # Telegram 通知
        if 'telegram' in self.notif_config:
            self._send_telegram(title, content)

        # Bark 通知
        if 'bark' in self.notif_config:
            self._send_bark(title, content)

    def _send_dingtalk(self, message):
        """钉钉通知"""
        config = self.notif_config['dingtalk']
        webhook = config.get('webhook', '')
        if not webhook:
            return

        # 支持签名加密
        secret = config.get('secret', '')
        if secret:
            timestamp = str(round(time.time() * 1000))
            import hmac
            import base64
            string_to_sign = f'{timestamp}\n{secret}'
            hmac_code = hmac.new(secret.encode(), string_to_sign.encode(), digestmod=hashlib.sha256).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
            webhook = f'{webhook}&timestamp={timestamp}&sign={sign}'

        try:
            resp = httpx.post(webhook, json={
                'msgtype': 'text',
                'text': {'content': message}
            }, timeout=10)
            logger.info(f"钉钉通知发送结果: {resp.status_code}")
        except Exception as e:
            logger.warning(f"钉钉通知发送失败: {e}")

    def _send_feishu(self, title, message):
        """飞书通知"""
        config = self.notif_config['feishu']
        webhook = config.get('webhook', '')
        if not webhook:
            return

        try:
            resp = httpx.post(webhook, json={
                'msg_type': 'text',
                'content': {'text': f"{title}\n\n{message}"}
            }, timeout=10)
            logger.info(f"飞书通知发送结果: {resp.status_code}")
        except Exception as e:
            logger.warning(f"飞书通知发送失败: {e}")

    def _send_telegram(self, title, content):
        """Telegram 通知"""
        config = self.notif_config['telegram']
        bot_token = config.get('bot_token', '')
        chat_id = config.get('chat_id', '')
        if not bot_token or not chat_id:
            return

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        try:
            resp = httpx.post(url, json={
                'chat_id': chat_id,
                'text': f"{title}\n\n{content}",
                'parse_mode': 'Markdown'
            }, timeout=10)
            result = resp.json()
            logger.info(f"Telegram 通知发送结果: {result.get('ok')}")
        except Exception as e:
            logger.warning(f"Telegram 通知发送失败: {e}")

    def _send_bark(self, title, content):
        """Bark 通知"""
        config = self.notif_config['bark']
        server = config.get('server', '')
        if not server:
            return

        url = f"{server}/{urllib.parse.quote(title)}/{urllib.parse.quote(content)}"
        try:
            resp = httpx.post(url, timeout=10)
            logger.info(f"Bark 通知发送结果: {resp.status_code}")
        except Exception as e:
            logger.warning(f"Bark 通知发送失败: {e}")


# ==================== WAF 绕过模块 ====================

def get_waf_cookies(session_cookie, api_user):
    """
    使用 Playwright 浏览器访问登录页，获取 WAF cookies
    返回: (all_cookies_dict, success_bool)
    """
    all_cookies = {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                ]
            )
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/125.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )

            # 先设置 session cookie
            if session_cookie:
                context.add_cookies([{
                    'name': 'session',
                    'value': session_cookie,
                    'domain': 'anyrouter.top',
                    'path': '/'
                }])

            page = context.new_page()
            try:
                page.goto('https://anyrouter.top/login', wait_until='networkidle', timeout=30000)
                time.sleep(2)  # 等待 WAF 检测完成
            except Exception as e:
                logger.warning(f"页面加载异常: {e}")

            # 获取所有 cookies
            cookies = context.cookies()
            for cookie in cookies:
                all_cookies[cookie['name']] = cookie['value']

            page.close()
            browser.close()

    except Exception as e:
        logger.error(f"获取 WAF cookies 失败: {e}")
        return {}, False

    if not all_cookies:
        logger.warning("未获取到 cookies，可能已被封禁或网络问题")
        return {}, False

    logger.info(f"成功获取 cookies: {list(all_cookies.keys())}")
    return all_cookies, True


# ==================== 签到核心逻辑 ====================

def get_user_info(client, headers, cookies):
    """获取用户信息和余额"""
    client.cookies.update(cookies)

    try:
        response = client.get(
            'https://anyrouter.top/api/user/self',
            headers=headers,
            timeout=15
        )
        data = response.json()

        if data.get('success') and data.get('data'):
            quota = data['data'].get('quota', 0) / 500000
            used_quota = data['data'].get('used_quota', 0) / 500000
            return {
                'success': True,
                'quota': quota,
                'used_quota': used_quota,
                'data': data['data']
            }
        else:
            logger.warning(f"获取用户信息失败: {data}")
            return {'success': False, 'error': data.get('msg', '未知错误')}

    except Exception as e:
        logger.error(f"获取用户信息异常: {e}")
        return {'success': False, 'error': str(e)}


def check_in(client, headers, cookies):
    """执行签到"""
    client.cookies.update(cookies)

    checkin_headers = headers.copy()
    checkin_headers.update({
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
    })

    try:
        response = client.post(
            'https://anyrouter.top/api/user/sign_in',
            headers=checkin_headers,
            timeout=15
        )
        data = response.json()
        return data
    except Exception as e:
        logger.error(f"签到请求异常: {e}")
        return {'ret': 0, 'msg': str(e)}


def process_account(account_config, balance_manager):
    """处理单个账号的签到"""
    name = account_config.get('name', '未命名账号')
    cookies = account_config.get('cookies', {})
    api_user = account_config.get('api_user', '')
    session_cookie = cookies.get('session', '')

    if not session_cookie or not api_user:
        logger.warning(f"[{name}] 缺少必要配置 (session 或 api_user)，跳过")
        return None

    # 构建请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/125.0.0.0 Safari/537.36',
        'new-api-user': api_user,
        'Referer': 'https://anyrouter.top/console',
        'Origin': 'https://anyrouter.top'
    }

    # 创建 httpx 客户端
    with httpx.Client(verify=False, follow_redirects=True) as client:
        # 获取 WAF cookies
        logger.info(f"[{name}] 正在获取 WAF cookies...")
        all_cookies, success = get_waf_cookies(session_cookie, api_user)
        if not success:
            return {'name': name, 'status': 'failed', 'error': 'Cookies 获取失败'}

        # 获取签到前余额
        logger.info(f"[{name}] 正在获取用户信息...")
        user_info = get_user_info(client, headers, all_cookies)
        if not user_info['success']:
            return {'name': name, 'status': 'failed', 'error': user_info.get('error', '获取用户信息失败')}

        before_quota = user_info['quota']
        logger.info(f"[{name}] 当前余额: ${before_quota:.4f}")

        # 检查是否需要签到
        if not balance_manager.should_checkin(name, before_quota):
            logger.info(f"[{name}] 上次签到后余额无变化，跳过本次签到")
            return {'name': name, 'status': 'skipped', 'quota': before_quota}

        # 执行签到
        logger.info(f"[{name}] 正在执行签到...")
        time.sleep(1)  # 短暂延迟
        result = check_in(client, headers, all_cookies)

        # 获取签到后余额
        time.sleep(1)
        user_info_after = get_user_info(client, headers, all_cookies)

        after_quota = user_info_after['quota'] if user_info_after['success'] else before_quota

        # 判断签到结果
        if result.get('ret') == 1 or result.get('code') == 0 or result.get('success'):
            msg = result.get('msg', '')
            if any(keyword in msg for keyword in ['已经签到', '已签到', '重复签到', 'already checked']):
                status = 'already_done'
                sign_in_msg = f"今日已签到: {msg}"
            else:
                status = 'success'
                sign_in_msg = f"签到成功: {msg}" if msg else "签到成功"
        elif 'ret' in result and result['ret'] != 1:
            status = 'failed'
            sign_in_msg = f"签到失败: {result.get('msg', '未知错误')}"
        else:
            status = 'unknown'
            sign_in_msg = f"签到结果不确定: {result}"

        # 更新余额记录
        balance_manager.record_balance(name, after_quota)

        return {
            'name': name,
            'status': status,
            'before_quota': before_quota,
            'after_quota': after_quota,
            'change': round(after_quota - before_quota, 4),
            'message': sign_in_msg
        }


# ==================== 余额管理器 ====================

class BalanceManager:
    """管理账号余额 hash，用于判断是否已签到"""

    def __init__(self, hash_file='balance_hash.json'):
        self.hash_file = hash_file
        self.balances = self._load()

    def _load(self):
        """加载保存的余额 hash"""
        try:
            if os.path.exists(self.hash_file):
                with open(self.hash_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"加载余额记录失败: {e}")
        return {}

    def _save(self):
        """保存余额 hash"""
        try:
            with open(self.hash_file, 'w', encoding='utf-8') as f:
                json.dump(self.balances, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"保存余额记录失败: {e}")

    def get_hash(self, name, quota):
        """生成余额的 hash"""
        data = f"{name}:{quota:.6f}"
        return hashlib.md5(data.encode()).hexdigest()

    def should_checkin(self, name, current_quota):
        """判断是否应该签到"""
        saved_hash = self.balances.get(name)
        if not saved_hash:
            return True  # 首次运行，需要签到

        current_hash = self.get_hash(name, current_quota)
        # 如果余额变化了，说明上次签到成功，需要再次签到
        return current_hash != saved_hash

    def record_balance(self, name, quota):
        """记录当前余额 hash"""
        self.balances[name] = self.get_hash(name, quota)
        self._save()


# ==================== 主程序 ====================

def load_accounts():
    """从环境变量加载账号配置"""
    accounts_json = os.getenv('ANYROUTER_ACCOUNTS', '').strip()
    if not accounts_json:
        logger.error("未找到 ANYROUTER_ACCOUNTS 环境变量")
        logger.error("请在青龙面板环境变量中添加: ANYROUTER_ACCOUNTS")
        return []

    try:
        accounts = json.loads(accounts_json)
        if isinstance(accounts, str):
            accounts = json.loads(accounts)

        if not isinstance(accounts, list):
            accounts = [accounts]

        # 为每个账号设置默认名称
        for i, account in enumerate(accounts):
            if 'name' not in account:
                account['name'] = f"账号{i+1}"

        return accounts

    except json.JSONDecodeError as e:
        logger.error(f"解析账号配置失败: {e}")
        logger.error(f"原始内容: {accounts_json[:200]}")
        return []


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("AnyRouter 签到脚本启动")
    logger.info(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)

    # 检测运行环境
    check_environment()

    # 初始化通知器
    notifier = Notifier()

    # 加载账号
    accounts = load_accounts()
    if not accounts:
        logger.error("没有可用的账号配置")
        return 1

    logger.info(f"共加载 {len(accounts)} 个账号")

    # 初始化余额管理器
    balance_manager = BalanceManager()

    # 处理所有账号
    results = []
    for account in accounts:
        logger.info("-" * 40)
        result = process_account(account, balance_manager)
        if result:
            results.append(result)

    # 汇总结果
    logger.info("")
    logger.info("=" * 50)
    logger.info("签到结果汇总:")
    logger.info("=" * 50)

    success_count = 0
    failed_count = 0
    skipped_count = 0

    for result in results:
        name = result.get('name', '未知')
        status = result.get('status', 'unknown')
        message = result.get('message', '')

        if status == 'success':
            success_count += 1
            logger.info(f"[{name}] ✅ {message} (余额: ${result.get('before_quota', 0):.4f} -> ${result.get('after_quota', 0):.4f})")
        elif status == 'already_done':
            skipped_count += 1
            logger.info(f"[{name}] ⏭️ {message}")
        elif status == 'skipped':
            skipped_count += 1
            logger.info(f"[{name}] ⏭️ 余额无变化，跳过签到")
        else:
            failed_count += 1
            logger.error(f"[{name}] ❌ {message}")

    logger.info("")
    logger.info(f"总计: {len(results)} 个账号 | 成功: {success_count} | 跳过: {skipped_count} | 失败: {failed_count}")

    # 发送通知
    if results:
        title = "AnyRouter 签到结果"
        content_lines = [f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
        content_lines.append("")

        for result in results:
            name = result.get('name', '未知')
            status = result.get('status', 'unknown')
            emoji = {'success': '✅', 'already_done': '⏭️', 'skipped': '⏭️', 'failed': '❌'}.get(status, '❓')

            line = f"{emoji} {name}: {result.get('message', '')}"
            if result.get('before_quota') is not None:
                line += f" (${result['before_quota']:.4f} -> ${result['after_quota']:.4f})"
            content_lines.append(line)

        content_lines.append("")
        content_lines.append(f"总计: 成功 {success_count} | 跳过 {skipped_count} | 失败 {failed_count}")

        notifier.send(title, "\n".join(content_lines))

    return 0 if failed_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
