"""
邮箱后端工厂
"""


def create_email_provider(provider_name):
    """根据名称创建邮箱服务提供商实例"""
    if provider_name == "cloudflare":
        from .cloudflare import CloudflareEmailProvider
        return CloudflareEmailProvider()
    elif provider_name == "duckmail":
        from .duckmail import DuckMailProvider
        return DuckMailProvider()
    else:
        raise ValueError(f"未知的邮箱后端: {provider_name}，可选: cloudflare, duckmail")
