"""
配置文件 - 复制为 config.py 并填写你的信息
cp config.example.py config.py
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
CAPTCHA_SOLVER = "browser"
CAPSOLVER_API_KEY = ""

# ═══ 注册配置 ═══
DEFAULT_PASSWORD = "TavilyAuto123!"
API_KEYS_FILE = "api_keys.md"
RUN_COUNT = 10
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
PROXY_AUTO_UPLOAD = False
PROXY_URL = ""
PROXY_ADMIN_PASSWORD = ""

# ═══ Tavily ═══
TAVILY_HOME_URL = "https://app.tavily.com/home"
TAVILY_SIGNUP_URL = "https://app.tavily.com/home"
