#!/usr/bin/env python3
"""
邮箱后端抽象基类
"""
import re
import time
import quopri
from abc import ABC, abstractmethod
from config import EMAIL_CHECK_INTERVAL, MAX_EMAIL_WAIT_TIME


class EmailProvider(ABC):
    """邮箱服务提供商抽象基类"""

    @abstractmethod
    def create_email(self, prefix=None):
        pass

    @abstractmethod
    def get_messages(self, address):
        pass

    def cleanup(self, address):
        pass

    def _decode_blob(self, value):
        if not value:
            return ""
        if not isinstance(value, str):
            value = str(value)
        # 先清理 quoted-printable 软换行，再做解码，避免 URL 被折断
        value = value.replace('=\r\n', '').replace('=\n', '')
        try:
            value = quopri.decodestring(value.encode('utf-8', errors='ignore')).decode('utf-8', errors='ignore')
        except Exception:
            pass
        value = value.replace('&amp;', '&')
        return value

    def find_verification_link(self, messages):
        """从邮件列表中查找 Tavily/Auth0 验证链接"""
        for msg in messages:
            subject = self._decode_blob((msg.get("subject") or "")).lower()
            html = self._decode_blob(msg.get("html") or "")
            text = self._decode_blob(msg.get("text") or "")
            raw = self._decode_blob(msg.get("raw") or "")

            # 有些邮箱后端不提供 subject 字段，但 raw 里有完整头部；用内容本身做 gate
            gate_blob = (subject + "\n" + html + "\n" + text + "\n" + raw).lower()
            if not any(k in gate_blob for k in ("verify", "tavily", "email-verification", "ticket=", "auth.tavily.com")):
                continue

            combined = "\n".join([html, text, raw])
            normalized = combined.replace('=3D', '=')
            normalized = normalized.replace('\r', '')
            # 去掉 URL 中被折断的换行/空白，例如 email-\nverification 或 ticket=\nabc
            normalized = re.sub(r'(?<=[A-Za-z0-9:/?&._%#=-])\n+(?=[A-Za-z0-9/_?&.%#=-])', '', normalized)
            normalized = re.sub(r'(?<=[A-Za-z0-9:/?&._%#=-])[ \t]+(?=[A-Za-z0-9/_?&.%#=-])', '', normalized)

            # 优先从 href 抓
            links = re.findall(r'href=["\'](https?://[^"\']+)["\']', normalized, flags=re.I)
            # 再抓裸 URL
            links += re.findall(r'https?://[^\s<>"\']+', normalized, flags=re.I)

            # 去重但保持顺序
            dedup = []
            seen = set()
            for link in links:
                link = link.strip().rstrip('#').replace('=3D', '=')
                if link not in seen:
                    seen.add(link)
                    dedup.append(link)

            skip_patterns = [
                '.png', '.jpg', '.gif', '.css', '.js',
                'cdn.auth0.com', 'unsubscribe', 'privacy',
                'about:blank', 'auth0.com/#', 'mailto:', '/wf/open?upn=',
            ]
            for link in dedup:
                link = link.strip().strip("()[]{}<>.,;\"'")
                link_lower = link.lower()
                if any(p in link_lower for p in skip_patterns):
                    continue
                if ('auth.tavily.com' in link_lower or 'tavily.com' in link_lower or 'auth0' in link_lower) and (
                    'email-verification' in link_lower or 'verify' in link_lower or 'ticket=' in link_lower
                ):
                    return link

        return None

    def check_for_verification_email(self, address, max_wait=None, interval=None):
        if interval is None:
            interval = EMAIL_CHECK_INTERVAL
        if max_wait is None:
            max_wait = MAX_EMAIL_WAIT_TIME

        max_retries = max_wait // interval
        print(f"📧 开始检查验证邮件，目标: {address}")
        print(f"⏳ 最大等待 {max_wait} 秒，每 {interval} 秒检查一次")

        for attempt in range(max_retries):
            print(f"🔄 第 {attempt + 1}/{max_retries} 次检查...")
            messages = self.get_messages(address)
            if messages:
                print(f"📋 找到 {len(messages)} 封邮件")
                link = self.find_verification_link(messages)
                if link:
                    print(f"✅ 找到验证链接: {link}")
                    return link
                else:
                    print("⚠️ 邮件中未找到验证链接")
            else:
                print("📭 暂无邮件")
            if attempt < max_retries - 1:
                print(f"⏳ 等待 {interval} 秒后重试...")
                time.sleep(interval)

        print("❌ 超时，未找到验证邮件")
        return None
