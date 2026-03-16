"""
配置文件模板

使用方法：
  cp config.example.py config.py

说明：
- 本文件只放示例值，不要提交真实密码 / token
- 长期运行时，推荐把 API_KEYS_FILE 指向 output/ 目录
- 如果使用 adapter 模式，记得配置 TURNSTILE_ADAPTER_URL
"""

EMAIL_PROVIDER = "cloudflare"

# ═══ Cloudflare Email Worker / 私有 tmail worker ═══
EMAIL_DOMAIN = ""
EMAIL_PREFIX = "tavily"
EMAIL_API_URL = ""
EMAIL_API_TOKEN = ""        # 兼容旧版 Bearer Token Worker；若使用双密码私有 worker 可留空
EMAIL_ADMIN_PASSWORD = ""   # 私有 tmail worker 管理密码
EMAIL_SITE_PASSWORD = ""    # 私有 tmail worker 站点密码（可与管理密码相同）

# ═══ DuckMail (EMAIL_PROVIDER = "duckmail" 时必填) ═══
DUCKMAIL_API_BASE = "https://api.duckmail.sbs"
DUCKMAIL_BEARER = ""
DUCKMAIL_DOMAIN = "duckmail.sbs"

# ═══ 验证码 ═══
# 可选值：
# - "browser"    : 浏览器内尝试点击/等待，不适合长期稳定运行
# - "capsolver" : 使用 CapSolver API
# - "adapter"   : 使用本项目自带的 camoufox-adapter
CAPTCHA_SOLVER = "adapter"
CAPSOLVER_API_KEY = ""
TURNSTILE_ADAPTER_URL = "http://camoufox-adapter:5072"

# ═══ 注册配置 ═══
DEFAULT_PASSWORD = "TavilyAuto123!"
API_KEYS_FILE = "output/api_keys.md"
RUN_COUNT = 1
RUN_THREADS = 1

# ═══ 等待时间（秒） ═══
WAIT_TIME_SHORT = 2
WAIT_TIME_MEDIUM = 5
WAIT_TIME_LONG = 10
EMAIL_CHECK_INTERVAL = 10
MAX_EMAIL_WAIT_TIME = 300

# ═══ 浏览器 ═══
HEADLESS = True
BROWSER_TIMEOUT = 30000
BROWSER_TYPE = "firefox"

# ═══ Proxy 自动上传 ═══
# 说明：
# - 若 generator 跑在容器里，PROXY_URL 不要想当然写 127.0.0.1
# - 常见可用方式是 host.docker.internal 或同 compose 网络服务名
PROXY_AUTO_UPLOAD = False
PROXY_URL = ""
PROXY_ADMIN_PASSWORD = ""

# ═══ Tavily ═══
TAVILY_HOME_URL = "https://app.tavily.com/home"
TAVILY_SIGNUP_URL = "https://app.tavily.com/home"
