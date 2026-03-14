#!/usr/bin/env python3
"""
Cloudflare Email Worker / 私有 tmail worker 邮箱后端
兼容两种模式：
1. 旧版 Bearer Token: Authorization: Bearer <token>
2. 私有 worker 双密码: x-admin-auth + x-custom-auth/x-site-password
"""
import random
import string
import time
import requests
from config import (
    EMAIL_API_URL,
    EMAIL_API_TOKEN,
    EMAIL_DOMAIN,
    EMAIL_PREFIX,
    EMAIL_ADMIN_PASSWORD,
    EMAIL_SITE_PASSWORD,
)
from .base import EmailProvider


class CloudflareEmailProvider(EmailProvider):
    def __init__(self):
        self.api_url = EMAIL_API_URL.rstrip("/")
        self.email_domain = EMAIL_DOMAIN
        self.api_token = (EMAIL_API_TOKEN or "").strip()
        self.admin_password = (EMAIL_ADMIN_PASSWORD or "").strip()
        self.site_password = (EMAIL_SITE_PASSWORD or self.admin_password or "").strip()
        self._jwt = None
        self._address = None

    def _private_site_headers(self):
        if not self.site_password:
            return {}
        return {
            "x-custom-auth": self.site_password,
            "x-site-password": self.site_password,
        }

    def _create_headers(self):
        headers = {}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        if self.admin_password:
            headers["x-admin-auth"] = self.admin_password
        headers.update(self._private_site_headers())
        return headers

    def _read_headers(self):
        headers = self._private_site_headers()
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def _request_with_retry(self, method, url, *, timeout=20, **kwargs):
        last_exc = None
        for _ in range(2):
            try:
                return requests.request(method, url, timeout=timeout, **kwargs)
            except Exception as exc:
                last_exc = exc
                time.sleep(0.5)
        if last_exc:
            raise last_exc
        raise RuntimeError("unexpected email worker request failure")

    def create_email(self, prefix=None):
        if prefix is None:
            prefix = EMAIL_PREFIX
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        address = f"{prefix}-{suffix}@{self.email_domain}"

        if self.admin_password:
            try:
                name = f"{prefix}{suffix}"
                resp = self._request_with_retry(
                    "POST",
                    f"{self.api_url}/admin/new_address",
                    json={"enablePrefix": True, "name": name, "domain": self.email_domain},
                    headers={"Content-Type": "application/json", **self._create_headers()},
                    timeout=20,
                )
                resp.raise_for_status()
                data = resp.json()
                self._jwt = data.get("jwt")
                self._address = data.get("address") or address
                print(f"✅ 私有 worker 邮箱已创建: {self._address}")
                return self._address
            except Exception as e:
                print(f"⚠️ 私有 worker 创建邮箱失败，退回 catch-all: {e}")

        self._jwt = None
        self._address = address
        print(f"✅ 生成 catch-all 邮箱: {address}")
        return address

    def get_messages(self, address):
        try:
            # 私有 worker：优先用 /admin/mails 读取（字段最全，含 raw），避免 /api/mails 结构漂移
            if self.admin_password:
                resp = self._request_with_retry(
                    'GET',
                    f"{self.api_url}/admin/mails",
                    params={'address': address, 'limit': 10, 'offset': 0},
                    headers=self._create_headers(),
                    timeout=20,
                )
                resp.raise_for_status()
                data = resp.json()
                results = data.get('results') or []

                def extract_subject(raw_text: str) -> str:
                    if not raw_text:
                        return ''
                    lines = raw_text.splitlines()
                    subj = ''
                    i = 0
                    while i < len(lines):
                        line = lines[i]
                        if line.lower().startswith('subject:'):
                            subj = line.split(':', 1)[1].strip()
                            j = i + 1
                            # header folding: subsequent lines starting with whitespace belong to subject
                            while j < len(lines) and (lines[j].startswith(' ') or lines[j].startswith('	')):
                                subj += ' ' + lines[j].strip()
                                j += 1
                            return subj.strip()
                        i += 1
                    return ''

                out = []
                for item in results:
                    raw = item.get('raw') or ''
                    out.append({
                        'subject': extract_subject(raw),
                        'html': item.get('html') or '',
                        'text': item.get('text') or '',
                        'raw': raw,
                    })
                return out
            if self._jwt:
                resp = self._request_with_retry(
                    "GET",
                    f"{self.api_url}/api/mails",
                    params={"limit": 10, "offset": 0},
                    headers={
                        "Authorization": f"Bearer {self._jwt}",
                        "Content-Type": "application/json",
                        **self._private_site_headers(),
                    },
                    timeout=20,
                )
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results") or []
                return [
                    {
                        "subject": item.get("subject") or "",
                        "html": item.get("html") or "",
                        "text": item.get("text") or "",
                        "raw": item.get("raw") or "",
                    }
                    for item in results
                ]

            resp = self._request_with_retry(
                "GET",
                f"{self.api_url}/messages",
                params={"address": address},
                headers=self._read_headers(),
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("messages", [])
        except Exception as e:
            print(f"❌ 获取邮件失败: {e}")
            return []

    def cleanup(self, address):
        try:
            if self._jwt:
                return
            resp = self._request_with_retry(
                "DELETE",
                f"{self.api_url}/messages",
                params={"address": address},
                headers=self._create_headers(),
                timeout=15,
            )
            resp.raise_for_status()
            print(f"🗑️ 已清理 {address} 的邮件")
        except Exception as e:
            print(f"⚠️ 清理邮件失败: {e}")
