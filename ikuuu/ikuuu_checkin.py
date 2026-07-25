#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# ikuuu.win 青龙面板签到脚本
# =============================================================================
# Author: deer
# GitHub: https://github.com/deerwan
#
# Copyright (c) deer. All rights reserved.
#
# 免责声明：
#   本项目仅供学习交流使用，请勿用于商业用途。
#   使用者需自行遵守 ikuuu.win 的服务条款及相关法律法规。
# =============================================================================
#
# 环境变量: IKUUU_ACCOUNTS (格式: email1:password1,email2:password2)
# 支持多账号，每个账号独立签到。
#
# 登录方式：极验(GeeTest V4) 行为验证码用 Playwright 无头浏览器
# 「点我开始验证」真实点击通过，避免伪造 w 参数被服务端拒绝。
# 需要安装浏览器：pip install playwright && playwright install chromium

import os
import sys
import time
import random
import json
import requests
from urllib.parse import urlparse

# ==================== 配置 ====================
# 默认域名 ikuuu.win，可通过环境变量 IKUUU_DOMAIN 覆盖（如 ikuuu.org）
BASE_DOMAIN = os.getenv("IKUUU_DOMAIN", "ikuuu.win").strip()
BASE_URL = f"https://{BASE_DOMAIN}"
LOGIN_URL = f"{BASE_URL}/auth/login"
CHECKIN_URL = f"{BASE_URL}/user/checkin"

# 浏览器登录最大重试次数
LOGIN_MAX_RETRIES = 3


def load_accounts():
    """从环境变量加载账号信息"""
    accounts_env = os.getenv("IKUUU_ACCOUNTS", "")
    if not accounts_env:
        print("❌ 未找到 IKUUU_ACCOUNTS 环境变量")
        print("📝 格式: email1:password1,email2:password2")
        sys.exit(1)

    accounts = []
    for account_str in accounts_env.split(","):
        if ":" not in account_str:
            continue
        email, password = account_str.split(":", 1)
        accounts.append({
            "email": email.strip(),
            "password": password.strip()
        })

    if not accounts:
        print("❌ 没有有效的账号配置")
        sys.exit(1)

    return accounts


def sleep_random(min_ms=500, max_ms=1500):
    """随机延迟"""
    time.sleep(random.randint(min_ms, max_ms) / 1000)


# ==================== Playwright 浏览器登录（过 Geetest V4 验证码） ====================
def _import_playwright():
    """延迟导入 Playwright，避免未安装时影响脚本整体运行。"""
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError as e:
        raise ImportError(
            "未安装 playwright。请执行: pip install playwright && playwright install chromium"
        ) from e


def _launch_browser(playwright):
    """启动浏览器：默认使用 Playwright 自带的 chromium。

    如需使用宿主机已安装的 Chrome/Edge，可设环境变量 IKUUU_BROWSER=chrome 或 msedge。
    """
    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage",
    ]
    channel = os.getenv("IKUUU_BROWSER", "").strip().lower() or None
    try:
        kwargs = {"headless": True, "args": launch_args}
        if channel:
            kwargs["channel"] = channel
            print(f"🔍 使用浏览器通道: {channel}")
        else:
            print("🔍 使用 Playwright 自带 chromium")
        browser = playwright.chromium.launch(**kwargs)
        print("🔍 浏览器启动成功")
        return browser
    except Exception as e:
        print(f"🔍 浏览器启动失败: {e}")
        raise RuntimeError(
            "无法启动浏览器。请确认已执行: playwright install chromium，"
            "并安装系统依赖: playwright install-deps"
        )


# SSPanel 会话关键 Cookie 字段
SESSION_COOKIE_NAMES = ("uid", "email", "key", "ip", "expire_in", "PHPSESSID")


def _cookie_header_from_context(context, base_url):
    """从浏览器上下文提取本站登录相关 Cookie 字符串。"""
    host = urlparse(base_url).hostname or ""
    cookies = context.cookies()
    parts = []
    seen = set()
    for name in SESSION_COOKIE_NAMES:
        for c in cookies:
            domain = (c.get("domain") or "").lstrip(".")
            if c.get("name") != name:
                continue
            if host and domain and host != domain and not host.endswith("." + domain) and not domain.endswith(host):
                if "ikuuu" not in domain and "ikuuu" not in host:
                    continue
            if name in seen:
                continue
            parts.append(f"{name}={c.get('value', '')}")
            seen.add(name)
    if not parts:
        # 兜底：凡域名含 ikuuu 的 cookie 都带上
        for c in cookies:
            domain = c.get("domain") or ""
            if "ikuuu" in domain or (host and host in domain):
                n = c.get("name")
                if n and n not in seen:
                    parts.append(f"{n}={c.get('value', '')}")
                    seen.add(n)
    return "; ".join(parts)


def _wait_and_pass_geetest(page, timeout_sec=30):
    """等待 Geetest 加载，点击「点我开始验证」，直到 Captcha.isReady()。"""
    deadline = time.time() + timeout_sec
    clicked = False

    while time.time() < deadline:
        try:
            state = page.evaluate(
                """() => {
                    const ready = !!(window.Captcha && window.Captcha.isReady && window.Captcha.isReady());
                    const loaded = !!(window.Captcha && window.Captcha.isLoaded && window.Captcha.isLoaded());
                    const err = (window.Captcha && window.Captcha.getError) ? window.Captcha.getError() : null;
                    const text = (document.querySelector('.embed-captcha') || {}).innerText || '';
                    return {ready, loaded, err, text: String(text).slice(0, 80)};
                }"""
            )
        except Exception:
            state = {"ready": False, "loaded": False, "err": None, "text": ""}

        if state.get("ready"):
            print("✅ Geetest 验证已通过")
            return True

        if state.get("err"):
            print(f"⚠️  Geetest 错误: {state['err']}")

        # 未通过时尝试点击雷达/按钮
        if not clicked or (deadline - time.time()) % 3 < 0.6:
            selectors = [
                ".geetest_radar_btn",
                ".geetest_btn_click",
                ".geetest_btn",
                ".geetest_holder",
                ".geetest_btn_svg",
                "text=点我开始验证",
            ]
            for sel in selectors:
                try:
                    loc = page.locator(sel).first
                    if loc.count() > 0 and loc.is_visible():
                        loc.click(timeout=2000)
                        clicked = True
                        print(f"🔍 已点击 Geetest 控件: {sel}")
                        page.wait_for_timeout(1200)
                        break
                except Exception:
                    continue

        page.wait_for_timeout(500)

    # 最后再查一次
    try:
        ready = page.evaluate(
            "() => !!(window.Captcha && window.Captcha.isReady && window.Captcha.isReady())"
        )
        if ready:
            print("✅ Geetest 验证已通过")
            return True
    except Exception:
        pass

    print("❌ 等待 Geetest 通过超时")
    return False


def login_with_browser(email, password, base_url, timeout_ms=60000):
    """用无头浏览器完成 Geetest 验证 + 登录，返回 Cookie 字符串；失败返回 None。"""
    if not email or not password:
        print("❌ 浏览器登录缺少邮箱或密码")
        return None

    base_url = base_url.rstrip("/")
    login_url = f"{base_url}/auth/login"
    sync_playwright = _import_playwright()

    print("ℹ️  使用浏览器真实点击过 Geetest 验证码并登录...")
    browser = None
    try:
        with sync_playwright() as p:
            browser = _launch_browser(p)
            context = browser.new_context(
                locale="zh-CN",
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
                ),
            )
            # 降低自动化指纹，Geetest 对 webdriver 更敏感
            context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
            page = context.new_page()
            page.goto(login_url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_selector("#email", timeout=20000)
            page.wait_for_timeout(800)

            page.fill("#email", email)
            # 部分主题密码框 id 为 password，name 为 passwd
            if page.locator("#password").count():
                page.fill("#password", password)
            else:
                page.fill("input[name='passwd'], input[type='password']", password)

            page.wait_for_timeout(1000)

            if not _wait_and_pass_geetest(page, timeout_sec=30):
                browser.close()
                return None

            page.click("button.login, button[type='submit'].login, .login")
            # 登录成功会跳转 /user；失败可能弹 swal 仍停在 login
            try:
                page.wait_for_url("**/user**", timeout=20000)
            except Exception:
                page.wait_for_timeout(2000)

            final_url = page.url
            if "/user" not in final_url:
                try:
                    msg = page.evaluate(
                        """() => {
                            const a = document.querySelector(
                              '.swal2-html-container, .swal2-content, .swal2-title'
                            );
                            return a ? a.innerText : '';
                        }"""
                    )
                except Exception:
                    msg = ""
                print(f"❌ 浏览器登录未进入用户中心（url={final_url}）{('，' + msg) if msg else ''}")
                browser.close()
                return None

            cookie = _cookie_header_from_context(context, base_url)
            browser.close()
            browser = None

            if not cookie or "uid=" not in cookie.lower():
                print(f"❌ 登录后 Cookie 不完整: {cookie[:80]}...")
                return None

            print("✅ 浏览器登录成功（过 Geetest 验证码）")
            return cookie
    except ImportError as e:
        print(f"❌ {e}")
        return None
    except Exception as e:
        print(f"❌ 浏览器登录失败: {e}")
        return None
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass


# ==================== 登录 ====================
def login(email, password):
    """
    登录 ikuuu.win（浏览器真实过验证码）
    返回 cookie 字符串
    """
    print(f"🔐 [{email}] 正在登录...")
    cookie = login_with_browser(email, password, BASE_URL)
    if not cookie:
        print(f"❌ [{email}] 登录失败")
        return None
    return cookie


# ==================== 签到 ====================
def checkin(cookie):
    """
    执行签到
    返回 (success, msg)
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Cookie": cookie,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    try:
        response = requests.post(
            CHECKIN_URL,
            headers=headers,
            timeout=30
        )
        result = response.json()
        ret = result.get("ret")
        msg = result.get("msg", "")

        if ret == 1:
            print(f"✅ 签到成功: {msg}")
            return True, msg
        elif "已经签到" in msg:
            print(f"✅ 今日已签到: {msg}")
            return True, msg
        else:
            print(f"⚠️  签到失败: {msg or '未知错误'}")
            return False, msg or "签到失败"
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return False, str(e)


# ==================== 主流程 ====================
def main():
    print("=" * 50)
    print("🚀 ikuuu.win 青龙面板签到脚本")
    print("=" * 50)

    accounts = load_accounts()
    total = len(accounts)
    success_count = 0
    fail_count = 0

    for i, account in enumerate(accounts, 1):
        email = account["email"]
        password = account["password"]

        print(f"\n📋 [{i}/{total}] 处理账号: {email}")

        # 登录（浏览器真实过验证码）
        cookie = login(email, password)
        if not cookie:
            fail_count += 1
            continue

        # 签到（等待 2-3 秒避免限流）
        if i > 1:
            sleep_random(2000, 3000)

        success, msg = checkin(cookie)
        if success:
            success_count += 1
        else:
            fail_count += 1

    # 汇总
    print("\n" + "=" * 50)
    print(f"📊 签到完成: 成功 {success_count}/{total}, 失败 {fail_count}/{total}")
    print("=" * 50)

    # 青龙面板通知
    notify_text = f"ikuuu签到结果\n成功: {success_count}/{total}\n失败: {fail_count}/{total}"
    print(f"\n📢 {notify_text}")


if __name__ == "__main__":
    main()
