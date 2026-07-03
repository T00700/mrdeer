#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# ikuuu.win 青龙面板签到脚本 (Cookie 模式)
# =============================================================================
# 使用 Cookie 直接签到，无需验证码
#
# 环境变量: IKUUU_COOKIE (Cookie 字符串，多账号用换行分隔)
# =============================================================================

import os
import sys
import time
import random
import requests

# ==================== 配置 ====================
BASE_URL = "https://ikuuu.win"
CHECKIN_URL = f"{BASE_URL}/user/checkin"
USER_URL = f"{BASE_URL}/user"


def load_cookies():
    """从环境变量加载 Cookie，支持多账号（换行分隔）"""
    cookie_str = os.getenv("IKUUU_COOKIE", "")
    
    if not cookie_str:
        print("❌ 未找到 IKUUU_COOKIE 环境变量")
        print("📝 获取方法：浏览器登录 ikuuu → F12 → Application → Cookies → ikuuu.win")
        print("📝 复制 Name 和 Value，格式: email=xxx; expire_in=xxx; ip=xxx; key=xxx; uid=xxx")
        sys.exit(1)
    
    accounts = []
    for i, line in enumerate(cookie_str.strip().split("\n"), 1):
        line = line.strip()
        if not line:
            continue
        accounts.append({
            "index": i,
            "cookie": line
        })
    
    if not accounts:
        print("❌ 没有有效的 Cookie 配置")
        sys.exit(1)
    
    return accounts


def parse_cookie(cookie_str: str) -> dict:
    """将 Cookie 字符串解析为 dict"""
    cookies = {}
    if not cookie_str:
        return cookies
    for item in cookie_str.split(';'):
        item = item.strip()
        if '=' in item:
            k, v = item.split('=', 1)
            cookies[k.strip()] = v.strip()
    return cookies


def mask_email(cookie_dict: dict) -> str:
    """脱敏显示 email"""
    email = cookie_dict.get('email', 'unknown')
    if '@' in email:
        parts = email.split('@')
        if len(parts[0]) <= 2:
            masked = parts[0]
        else:
            masked = parts[0][0] + '*' * (len(parts[0]) - 2) + parts[0][-1]
        return f"{masked}@{parts[1]}"
    return email[:10] + '...' if len(email) > 10 else email


def validate_cookie(session: requests.Session) -> tuple:
    """验证 Cookie 是否有效"""
    try:
        resp = session.get(USER_URL, timeout=15, allow_redirects=False)
        
        # 重定向到登录页 = Cookie 失效
        if resp.status_code in (302, 301):
            location = resp.headers.get('Location', '')
            if 'login' in location.lower():
                return False, "Cookie 已失效（重定向到登录页）"
        
        # 检查页面内容
        if resp.status_code == 200:
            text_lower = resp.text.lower()
            if 'cloudflare' in text_lower and 'just a moment' in text_lower:
                return False, "被 Cloudflare 拦截"
            if 'login' in text_lower and '<form' in text_lower:
                return False, "Cookie 已失效（页面为登录表单）"
            return True, "有效"
        
        return False, f"HTTP {resp.status_code}"
    except requests.exceptions.Timeout:
        return False, "请求超时"
    except requests.exceptions.ConnectionError:
        return False, "网络连接失败"
    except Exception as e:
        return False, f"验证异常: {str(e)}"


def checkin(session: requests.Session) -> tuple:
    """执行签到"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Origin': BASE_URL,
        'Referer': f"{USER_URL}/",
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    try:
        resp = session.post(CHECKIN_URL, headers=headers, timeout=15)
        result = resp.json()
        
        ret = result.get('ret', -1)
        msg = result.get('msg', '')
        
        if ret == 1:
            return True, f"签到成功: {msg}"
        elif ret == 0:
            if '已经签到' in msg or 'already' in msg.lower():
                return True, f"今日已签到: {msg}"
            return False, f"签到失败: {msg}"
        else:
            return False, f"未知响应 (ret={ret}): {msg}"
    except Exception as e:
        return False, f"请求异常: {str(e)}"


def main():
    print("=" * 60)
    print("🚀 ikuuu.win 青龙面板签到脚本 (Cookie 模式)")
    print(f"🌐 域名: {BASE_URL}")
    print("=" * 60)
    
    accounts = load_cookies()
    total = len(accounts)
    success_count = 0
    fail_count = 0
    
    for account in accounts:
        idx = account["index"]
        raw_cookie = account["cookie"]
        
        print(f"\n📋 [{idx}/{total}] 处理账号...")
        
        # 解析 Cookie
        cookies_dict = parse_cookie(raw_cookie)
        display_email = mask_email(cookies_dict)
        print(f"👤 账号: {display_email}")
        
        # 构建 Session
        session = requests.Session()
        session.cookies.update(cookies_dict)
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        
        # 验证 Cookie
        print("🔍 验证 Cookie...")
        valid, diagnostic = validate_cookie(session)
        if not valid:
            print(f"❌ Cookie 验证失败: {diagnostic}")
            fail_count += 1
            continue
        print(f"✅ Cookie 有效")
        
        # 随机延迟（避免同一时间签到）
        if idx > 1:
            delay = random.uniform(2, 5)
            print(f"⏱️  等待 {delay:.1f} 秒...")
            time.sleep(delay)
        
        # 执行签到
        print("📝 执行签到...")
        signed, msg = checkin(session)
        if signed:
            print(f"✅ {msg}")
            success_count += 1
        else:
            print(f"❌ {msg}")
            fail_count += 1
    
    # 汇总
    print("\n" + "=" * 60)
    print(f"📊 签到完成: 成功 {success_count}/{total}, 失败 {fail_count}/{total}")
    print("=" * 60)
    
    # 青龙面板通知
    notify_text = f"ikuuu签到结果\n成功: {success_count}/{total}\n失败: {fail_count}/{total}"
    print(f"\n📢 {notify_text}")


if __name__ == "__main__":
    main()
