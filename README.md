# Tavily Key Generator + API Proxy

批量注册 Tavily 账户获取 API Key，并通过代理网关池化管理，对外提供统一 API 端点。

> 当前仓库包含两部分：
> 1. **Key Generator**：自动注册 Tavily 账户并产出 API Key
> 2. **API Proxy**：将多个 Tavily Key 池化，对外暴露统一 Search / Extract API

这份 README 已按当前项目结构和已验证实践更新，尤其补充了：
- `adapter` 模式的实际用法
- `camoufox + camoufox-adapter + tavily-scheduler` 的 compose 方案
- Proxy 自动上传的工作方式
- 与长期运行环境更贴近的部署建议

---

## 1. Repository Layout

```text
.
├── main.py                        # 注册入口
├── intelligent_tavily_automation.py
├── browser_solver.py
├── capsolver_solver.py
├── config.example.py              # 配置模板
├── docker-compose.yml             # 推荐的 scheduler + adapter compose 方案
├── adapter/                       # Turnstile adapter
├── camoufox/                      # Camoufox browser runtime
├── email_providers/               # 邮箱后端实现
├── proxy/                         # Tavily API proxy + web console
└── docs/                          # 截图等文档资源
```

---

## 2. What This Project Does

### A. Key Generator

自动完成 Tavily 注册流程：
- 打开注册页
- 处理 Cloudflare Turnstile
- 从邮箱中读取验证链接
- 登录并提取 API Key
- 保存到本地文件
- 可选：自动上传到 Proxy

### B. API Proxy

将多个 Tavily API Key 池化，对外提供统一 API：
- `/api/search`
- `/api/extract`
- Web 控制台
- Token 管理
- Key 管理 / 禁用 / 轮询
- 用量统计

---

## 3. Main Modes

### Mode 1: Run generator directly

适合一次性注册、调试或本地验证：

```bash
pip install -r requirements.txt
playwright install firefox
cp config.example.py config.py
# 编辑 config.py
python main.py
```

### Mode 2: Run proxy only

适合你已经有一批 Tavily API Key，只想把它们池化并提供统一 API：

```bash
cd proxy
cp .env.example .env
# 编辑 .env
docker compose up -d
```

### Mode 3: Long-running scheduler + adapter stack

适合长期低频注册。当前更推荐这个方案，而不是让一个注册进程常驻自旋并混杂所有职责。

仓库根目录自带 `docker-compose.yml`，部署的是：
- `tavily-camoufox`
- `tavily-camoufox-adapter`
- `tavily-scheduler`

这个方案适合：
- 独立 solver 栈
- 独立调度周期
- 单次注册频率可控
- 与其他自动化项目隔离

---

## 4. Generator Quick Start

```bash
git clone https://github.com/Facetomyself/tavily-key-generator.git
cd tavily-key-generator
pip install -r requirements.txt
playwright install firefox
cp config.example.py config.py
# 编辑 config.py
python main.py
```

### Minimal config

至少要配置：
- 一个邮箱后端
- 一个验证码求解方式

例如：

```python
EMAIL_PROVIDER = "cloudflare"
EMAIL_DOMAIN = "example.com"
EMAIL_PREFIX = "tavily"
EMAIL_API_URL = "https://mail.example.com"
EMAIL_API_TOKEN = "..."

CAPTCHA_SOLVER = "adapter"
TURNSTILE_ADAPTER_URL = "http://camoufox-adapter:5072"

RUN_COUNT = 1
RUN_THREADS = 1
API_KEYS_FILE = "output/api_keys.md"
```

> 注意：`API_KEYS_FILE` 在当前长期运行方案里通常建议写到 `output/api_keys.md`，并通过 volume 持久化输出。

---

## 5. Email Backends

### Cloudflare / private tmail worker

当前代码已经兼容两种常见口径：
- Bearer token 风格 worker
- 双密码私有 worker（`EMAIL_ADMIN_PASSWORD` / `EMAIL_SITE_PASSWORD`）

示例：

```python
EMAIL_PROVIDER = "cloudflare"
EMAIL_DOMAIN = "example.com"
EMAIL_PREFIX = "tavily"
EMAIL_API_URL = "https://mail.example.com"
EMAIL_API_TOKEN = ""
EMAIL_ADMIN_PASSWORD = "..."
EMAIL_SITE_PASSWORD = "..."
```

### DuckMail

```python
EMAIL_PROVIDER = "duckmail"
DUCKMAIL_API_BASE = "https://api.duckmail.sbs"
DUCKMAIL_BEARER = "..."
DUCKMAIL_DOMAIN = "duckmail.sbs"
```

如果只配置一个后端，程序会自动使用；如果配置多个，运行时会让你选择。

---

## 6. CAPTCHA Solver Modes

### Option A: CapSolver

```python
CAPTCHA_SOLVER = "capsolver"
CAPSOLVER_API_KEY = "CAP-..."
```

优点：
- 稳定
- 成功率通常更高

缺点：
- 有成本

### Option B: Adapter mode

```python
CAPTCHA_SOLVER = "adapter"
TURNSTILE_ADAPTER_URL = "http://camoufox-adapter:5072"
```

这是当前仓库更值得推荐的长期运行模式之一，特别适合配合 compose 中的：
- `camoufox`
- `camoufox-adapter`
- `tavily-scheduler`

### Option C: Browser mode

```python
CAPTCHA_SOLVER = "browser"
```

只适合本地尝试，不适合作为稳定的长期方案。

---

## 7. Recommended Long-Running Compose Deployment

仓库根目录的 `docker-compose.yml` 当前更适合作为长期低频调度方案：

- `camoufox`：浏览器运行时
- `camoufox-adapter`：Turnstile adapter
- `tavily-scheduler`：按间隔触发 `python main.py`

### Why this layout

相比“注册脚本自己在内部无限循环”，这个方案更清晰：
- 调度逻辑独立
- solver 独立
- 输出目录持久化
- 可读性更好
- 更适合与其他项目隔离运行

### Current compose behavior

默认 scheduler 行为：
- 由环境变量 `TAVILY_INTERVAL_SECONDS` 控制循环间隔
- 每轮执行一次 `python main.py`
- 单轮注册数量由 `config.py` 中的 `RUN_COUNT` / `RUN_THREADS` 决定

如果你想要“平均每 36 分钟 1 个”的节奏，可以使用类似：

```yaml
environment:
  TAVILY_INTERVAL_SECONDS: "2160"
```

同时在 `config.py` 中设置：

```python
RUN_COUNT = 1
RUN_THREADS = 1
```

这会比一次性高并发注册更稳，也更不容易触发风控。

---

## 8. Proxy Auto Upload

注册成功后，可以自动把 API Key 推送到 Proxy：

```python
PROXY_AUTO_UPLOAD = True
PROXY_URL = "http://your-server:9874"
PROXY_ADMIN_PASSWORD = "your-password"
```

### Important container note

如果 generator 跑在容器里，而 proxy 跑在宿主机或其他容器网络外部：

- **不要默认写 `127.0.0.1:9874`**
- 这通常只会指向 generator 容器自己

更常见的工作方式是：
- 使用 `host.docker.internal`
- 或使用明确的 compose 网络服务名
- 或使用宿主机可达地址

例如：

```python
PROXY_URL = "http://host.docker.internal:9874"
```

并在 compose 中加入：

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

---

## 9. Proxy Quick Start

```bash
cd proxy
cp .env.example .env
# 编辑 .env 中的 ADMIN_PASSWORD
docker compose up -d
```

默认服务运行在：
- `http://localhost:9874`
- 控制台：`/`

### Example API calls

```bash
curl -X POST http://your-server:9874/api/search \
  -H "Authorization: Bearer tvly-YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "hello world"}'

curl -X POST http://your-server:9874/api/extract \
  -H "Authorization: Bearer tvly-YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com"]}'
```

---

## 10. Operational Notes

### Rate limiting / risk control

Tavily 注册存在明显的频率与风控限制：
- 不建议高并发
- 不建议过短间隔
- 更推荐低频、长期、分散式地产生 key

当前代码中：
- 有全局冷却控制
- 默认两次注册启动之间至少有间隔
- 还有随机抖动

### Recommended production posture

对长期运行来说，更建议：
- `RUN_COUNT = 1`
- `RUN_THREADS = 1`
- 用 scheduler 控制整体节奏
- 不要和其他验证码/浏览器自动化项目共用同一套 solver，避免相互干扰

### What to back up

至少备份：
- `config.py`
- `output/`
- `proxy/.env`
- 任何本地补丁

---

## 11. Oracle-proxy Practice Notes

以下是已经被实际验证过、但不依赖某个私有环境细节的经验：

- scheduler + adapter + camoufox 的三段式部署是可行的
- `RUN_COUNT = 1` / `RUN_THREADS = 1` 更适合长期运行
- `API_KEYS_FILE = "output/api_keys.md"` 比直接写根目录更适合持久化
- 如果自动上传到 Proxy，容器内访问宿主机 proxy 时通常要用 `host.docker.internal`
- 建议给 Tavily 和其他项目分别使用独立 solver / adapter 栈，不要混用

这些经验来自真实部署验证，但 README 不绑定任何单一生产环境，也不会要求你照搬某个私有配置。

---

## 12. Common Commands

### Check scheduler stack

```bash
docker compose ps
```

### Rebuild scheduler stack

```bash
docker compose up -d --build
```

### Follow scheduler logs

```bash
docker logs -f tavily-scheduler
```

### Trigger one manual run

```bash
docker exec tavily-scheduler python main.py
```

---

## 13. Security Notes

- 不要把真实 `config.py` 提交到公开仓库
- 不要把邮箱后台密码、token、代理管理密码直接写进 README
- 对外文档写结构、写流程、写部署方式即可

---

## 14. License

MIT

## 15. Disclaimer

本项目仅供个人学习和研究使用。使用本工具产生的一切后果由使用者自行承担。请遵守 Tavily 的服务条款、目标站点规则以及相关法律法规。
