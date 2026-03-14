#!/usr/bin/env python3
"""
DuckMail 临时邮箱后端
API: https://api.duckmail.sbs
"""
import random
import string
import requests
from config import DUCKMAIL_API_BASE, DUCKMAIL_BEARER, DUCKMAIL_DOMAIN
from .base import EmailProvider


class DuckMailProvider(EmailProvider):
    """基于 DuckMail API 的临时邮箱服务"""

    def __init__(self):
        self.api_base = DUCKMAIL_API_BASE.rstrip("/")
        self.admin_headers = {"Authorization": f"Bearer {DUCKMAIL_BEARER}"}
        # 每个邮箱有独立的 mail_token，用 address -> token 映射
        self._mail_tokens = {}

    def create_email(self, prefix=None):
        """创建 DuckMail 临时邮箱"""
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        if prefix:
            address = f"{prefix}-{suffix}@{DUCKMAIL_DOMAIN}"
        else:
            address = f"tavily-{suffix}@{DUCKMAIL_DOMAIN}"

        password = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

        # 1. 创建账号
        resp = requests.post(
            f"{self.api_base}/accounts",
            json={"address": address, "password": password},
            headers=self.admin_headers,
            timeout=15,
        )
        if resp.status_code not in [200, 201]:
            raise Exception(f"DuckMail 创建邮箱失败: {resp.status_code} - {resp.text[:200]}")

        # 2. 获取邮箱读取 token
        token_resp = requests.post(
            f"{self.api_base}/token",
            json={"address": address, "password": password},
            timeout=15,
        )
        if token_resp.status_code != 200:
            raise Exception(f"DuckMail 获取 token 失败: {token_resp.status_code}")

        mail_token = token_resp.json().get("token")
        if not mail_token:
            raise Exception("DuckMail 返回的 token 为空")

        self._mail_tokens[address] = mail_token
        print(f"✅ DuckMail 邮箱已创建: {address}")
        return address

    def get_messages(self, address):
        """获取邮件列表（含正文）"""
        mail_token = self._mail_tokens.get(address)
        if not mail_token:
            print(f"❌ 未找到 {address} 的 mail_token")
            return []

        headers = {"Authorization": f"Bearer {mail_token}"}

        try:
            # 获取邮件列表
            resp = requests.get(
                f"{self.api_base}/messages",
                headers=headers,
                timeout=15,
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            message_list = data.get("hydra:member") or data.get("member") or data.get("data") or []

            # 逐条获取邮件详情（列表接口不含正文）
            messages = []
            for item in message_list:
                msg_id = item.get("id") or item.get("@id", "").split("/")[-1]
                if not msg_id:
                    continue

                detail = self._fetch_message_detail(headers, msg_id)
                if detail:
                    messages.append(detail)

            return messages

        except Exception as e:
            print(f"❌ 获取邮件失败: {e}")
            return []

    def _fetch_message_detail(self, headers, msg_id):
        """获取单封邮件详情"""
        try:
            resp = requests.get(
                f"{self.api_base}/messages/{msg_id}",
                headers=headers,
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    def cleanup(self, address):
        """DuckMail 临时邮箱自动过期，无需清理"""
        pass
