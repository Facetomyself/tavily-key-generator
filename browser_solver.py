#!/usr/bin/env python3
"""
浏览器原生 Turnstile 验证码解决器（免费）
通过在真实浏览器中点击 Turnstile 复选框来通过验证
"""
import time


def solve_turnstile_browser(page, timeout=30):
    """
    在浏览器中直接解决 Turnstile 验证
    1. 找到 Turnstile iframe
    2. 点击复选框
    3. 等待验证通过（cf-turnstile-response 填充）
    返回 True/False
    """
    print("🔐 [免费模式] 尝试浏览器内解决 Turnstile...")

    # 等待 Turnstile iframe 出现
    try:
        page.wait_for_selector(
            'iframe[src*="challenges.cloudflare.com"]',
            timeout=8000,
        )
    except Exception:
        print("✅ 未检测到 Turnstile iframe，跳过")
        return True

    time.sleep(2)

    # 尝试在 iframe 中点击复选框
    clicked = False
    for frame in page.frames:
        if "challenges.cloudflare.com" not in frame.url:
            continue

        try:
            # Turnstile 复选框常见选择器
            selectors = [
                'input[type="checkbox"]',
                '[role="checkbox"]',
                '.cb-lb',
                '#challenge-stage input',
            ]
            for sel in selectors:
                try:
                    cb = frame.wait_for_selector(sel, timeout=3000)
                    if cb:
                        cb.click()
                        print(f"✅ 已点击 Turnstile 复选框: {sel}")
                        clicked = True
                        break
                except Exception:
                    continue
        except Exception:
            continue

        if clicked:
            break

    if not clicked:
        print("⚠️ 未找到可点击的复选框，等待自动验证...")

    # 等待 cf-turnstile-response 被填充（验证通过的标志）
    try:
        page.wait_for_function(
            """
            () => {
                const fields = document.querySelectorAll(
                    '[name="cf-turnstile-response"], [name="cf-chl-turnstile-response"], [name="captcha"]'
                );
                for (const f of fields) {
                    if (f.value && f.value.length > 50) return true;
                }
                return false;
            }
            """,
            timeout=timeout * 1000,
        )
        print("✅ Turnstile 验证已通过!")
        return True
    except Exception:
        print("❌ Turnstile 验证超时")
        return False
