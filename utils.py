"""
工具函数
"""
import time
from datetime import datetime
from config import API_KEYS_FILE


def save_api_key(email, api_key, password=None):
    """保存API key和账户信息到文件，并自动上传到 Proxy"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    account_line = f"{email},{password if password else 'N/A'},{api_key},{timestamp};\n"

    try:
        with open(API_KEYS_FILE, 'a', encoding='utf-8') as f:
            f.write(account_line)
    except FileNotFoundError:
        with open(API_KEYS_FILE, 'w', encoding='utf-8') as f:
            f.write(account_line)

    print(f"✅ 账户信息已保存到 {API_KEYS_FILE}")
    print(f"📧 邮箱: {email}")
    print(f"🔐 密码: {password if password else 'N/A'}")
    print(f"🔑 API Key: {api_key}")
    print(f"⏰ 时间: {timestamp}")

    # 自动上传到 Proxy
    upload_to_proxy(api_key, email)


def upload_to_proxy(api_key, email=""):
    """将 API Key 上传到 Proxy 网关"""
    try:
        from config import PROXY_AUTO_UPLOAD, PROXY_URL, PROXY_ADMIN_PASSWORD
    except ImportError:
        return

    if not PROXY_AUTO_UPLOAD or not PROXY_URL:
        return

    import urllib.request
    import json

    url = f"{PROXY_URL.rstrip('/')}/api/keys"
    data = json.dumps({"key": api_key, "email": email}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Admin-Password", PROXY_ADMIN_PASSWORD)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                print(f"☁️ 已自动上传到 Proxy ({PROXY_URL})")
            else:
                print(f"⚠️ Proxy 上传失败: HTTP {resp.status}")
    except Exception as e:
        print(f"⚠️ Proxy 上传失败: {e}")


def wait_with_message(seconds, message="等待中"):
    """带消息的等待函数"""
    print(f"⏳ {message}，等待 {seconds} 秒...")
    time.sleep(seconds)
