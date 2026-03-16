#!/usr/bin/env python3
"""
Turnstile 验证码解决器
支持：
- adapter: 使用配置中的 TURNSTILE_ADAPTER_URL 指向的 adapter 服务
- capsolver: 官方 CapSolver API
"""
import re
import time
import requests
from config import CAPSOLVER_API_KEY
import config

API_BASE = "https://api.capsolver.com"


def solve_turnstile(website_url, website_key, metadata=None):
    solver_mode = getattr(config, "CAPTCHA_SOLVER", "capsolver")
    adapter_url = getattr(config, "TURNSTILE_ADAPTER_URL", "").rstrip("/")

    if solver_mode == "adapter" and adapter_url:
        print(f"🔐 使用 adapter 解决 Turnstile: sitekey={website_key}...")
        try:
            resp = requests.get(f"{adapter_url}/turnstile", params={"url": website_url, "sitekey": website_key}, timeout=30)
            data = resp.json()
            if data.get("errorId", 0) != 0 or not data.get("taskId"):
                print(f"❌ adapter 创建任务失败: {data}")
                return None
            task_id = data["taskId"]
            print(f"✅ adapter 任务已创建: {task_id}")
        except Exception as e:
            print(f"❌ adapter 创建任务异常: {e}")
            return None

        for i in range(90):
            time.sleep(2)
            try:
                resp = requests.get(f"{adapter_url}/result", params={"id": task_id}, timeout=30)
                result = resp.json()
                status = result.get("status")
                if status == "ready":
                    token = result.get("solution", {}).get("token")
                    if token:
                        print(f"✅ adapter 已解决 Turnstile (耗时 {(i+1)*2}s)")
                        return token
                    print(f"❌ adapter 就绪但无 token: {result}")
                    return None
                elif status == "processing":
                    if i % 5 == 0:
                        print(f"⏳ adapter 等待中... ({(i+1)*2}s)")
                else:
                    print(f"❌ adapter 解决失败: {result}")
                    return None
            except Exception as e:
                print(f"⚠️ adapter 查询异常: {e}")
        print("❌ adapter 解决超时")
        return None

    print(f"🔐 使用 CapSolver 解决 Turnstile: sitekey={website_key}...")
    task = {
        "type": "AntiTurnstileTaskProxyLess",
        "websiteURL": website_url,
        "websiteKey": website_key,
    }
    if metadata:
        task["metadata"] = metadata

    try:
        resp = requests.post(f"{API_BASE}/createTask", json={
            "clientKey": CAPSOLVER_API_KEY,
            "task": task,
        }, timeout=30)
        data = resp.json()
        if data.get("errorId", 0) != 0:
            print(f"❌ 创建任务失败: {data.get('errorDescription', data)}")
            return None
        task_id = data.get("taskId")
        if not task_id:
            print(f"❌ 未获取到 taskId: {data}")
            return None
        print(f"✅ 任务已创建: {task_id}")
    except Exception as e:
        print(f"❌ 创建任务异常: {e}")
        return None

    for i in range(60):
        time.sleep(2)
        try:
            resp = requests.post(f"{API_BASE}/getTaskResult", json={
                "clientKey": CAPSOLVER_API_KEY,
                "taskId": task_id,
            }, timeout=30)
            result = resp.json()
            status = result.get("status")
            if status == "ready":
                token = result.get("solution", {}).get("token")
                if token:
                    print(f"✅ Turnstile 已解决 (耗时 {(i+1)*2}s)")
                    return token
                else:
                    print(f"❌ 解决成功但无 token: {result}")
                    return None
            elif status == "processing":
                if i % 5 == 0:
                    print(f"⏳ 等待解决中... ({(i+1)*2}s)")
            else:
                error = result.get("errorDescription", "")
                if error:
                    print(f"❌ 解决失败: {error}")
                    return None
        except Exception as e:
            print(f"⚠️ 查询结果异常: {e}")

    print("❌ 解决超时")
    return None


def extract_turnstile_sitekey(page):
    sitekey = page.evaluate("""() => {
        const selectors = [
            '[data-sitekey]',
            '[data-captcha-sitekey]',
            '.cf-turnstile',
        ];
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el) {
                return el.getAttribute('data-sitekey')
                    || el.getAttribute('data-captcha-sitekey')
                    || null;
            }
        }
        return null;
    }""")

    if sitekey:
        print(f"✅ 从 DOM 提取到 sitekey: {sitekey}")
        return sitekey

    content = page.content()
    patterns = [
        r'data-captcha-sitekey="(0x[0-9a-zA-Z_-]{10,})"',
        r'data-sitekey="(0x[0-9a-zA-Z_-]{10,})"',
        r"sitekey[\"\s:=]+[\"'](0x[0-9a-zA-Z_-]{10,})[\"']",
        r"siteKey[\"\s:=]+[\"'](0x[0-9a-zA-Z_-]{10,})[\"']",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            sitekey = match.group(1)
            print(f"✅ 从源码匹配到 sitekey: {sitekey}")
            return sitekey

    for frame in page.frames:
        url = frame.url
        if "challenges.cloudflare.com" in url:
            match = re.search(r'/(0x[0-9a-zA-Z_-]{10,})/', url)
            if match:
                sitekey = match.group(1)
                print(f"✅ 从 iframe URL 提取到 sitekey: {sitekey}")
                return sitekey

    print("❌ 未找到 Turnstile sitekey")
    return None


def inject_turnstile_token(page, token):
    page.evaluate("""(token) => {
        const inputSelectors = [
            '[name="cf-turnstile-response"]',
            '[name="cf-chl-turnstile-response"]',
            '[name="captcha"]',
            'input[data-captcha]',
        ];
        for (const sel of inputSelectors) {
            document.querySelectorAll(sel).forEach(input => {
                input.value = token;
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
            });
        }

        const callbackEls = document.querySelectorAll(
            '[data-callback], [data-captcha-sitekey], .cf-turnstile, [data-sitekey]'
        );
        for (const el of callbackEls) {
            const cbName = el.getAttribute('data-callback');
            if (cbName && typeof window[cbName] === 'function') {
                console.log('Calling callback:', cbName);
                window[cbName](token);
                return;
            }
        }

        for (const key of Object.keys(window)) {
            if (key.startsWith('captchaCallback_') && typeof window[key] === 'function') {
                console.log('Calling global callback:', key);
                window[key](token);
                return;
            }
        }
    }""", token)
    print("✅ Token 已注入页面")
