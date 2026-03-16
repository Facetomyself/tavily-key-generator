# Tavily API Proxy

将多个 Tavily API Key 池化，对外暴露统一 Tavily 兼容端点，并提供一个简洁的 Web 管理控制台。

## 功能

- **Key 池化轮询**：round-robin 分配请求到多个 API Key
- **失败熔断**：连续失败的 key 会被自动停用
- **Token 管理**：创建多个访问 token，供客户端统一接入
- **用量统计**：按 token 查看成功/失败次数与延迟
- **Web 控制台**：图形化管理 key / token / 统计数据
- **批量导入**：支持从 `api_keys.md` 文本批量导入 key
- **兼容 Tavily 官方 API**：客户端通常只需要改 base URL 和 token

---

## 快速开始

### Docker 部署（推荐）

```bash
cd proxy
cp .env.example .env
# 编辑 .env 中的 ADMIN_PASSWORD
docker compose up -d
```

默认监听：
- `http://localhost:9874`

### 本地运行

```bash
cd proxy
pip install -r requirements.txt
ADMIN_PASSWORD=your-password uvicorn server:app --host 0.0.0.0 --port 9874
```

---

## 控制台

控制台入口是：

- `GET /`

也就是：

- `http://localhost:9874/`

> 注意：当前控制台首页路径是 `/`，不是 `/console`。

---

## 使用流程

1. 访问 `http://localhost:9874/`
2. 输入管理密码登录
3. 导入 Tavily API Key（单个添加或批量导入）
4. 创建 token
5. 在应用中调用 `/api/search` 或 `/api/extract`

---

## 代理端点

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/search` | 代理 Tavily Search API |
| POST | `/api/extract` | 代理 Tavily Extract API |

### 客户端认证

支持两种方式传入访问 token：

1. `Authorization: Bearer <token>`
2. 请求体中的 `api_key` 字段

示例：

```bash
curl -X POST http://localhost:9874/api/search \
  -H "Authorization: Bearer tvly-YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "hello world"}'
```

或：

```bash
curl -X POST http://localhost:9874/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "hello world", "api_key": "tvly-YOUR_TOKEN"}'
```

---

## 管理端点

管理接口默认需要管理密码认证。

支持两种认证方式：

1. `X-Admin-Password: <ADMIN_PASSWORD>`
2. `Authorization: Bearer <ADMIN_PASSWORD>`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | Web 管理控制台 |
| GET | `/api/stats` | 查看统计概览 |
| GET | `/api/keys` | 列出所有 key（脱敏） |
| POST | `/api/keys` | 添加单个 key 或批量导入 |
| DELETE | `/api/keys/{id}` | 删除 key |
| PUT | `/api/keys/{id}/toggle` | 启用 / 禁用 key |
| GET | `/api/tokens` | 列出 token |
| POST | `/api/tokens` | 创建 token |
| DELETE | `/api/tokens/{id}` | 删除 token |
| PUT | `/api/password` | 修改管理密码 |

### 添加单个 key

```json
{"key":"tvly-xxx"}
```

### 添加单个 key 并记录邮箱

```json
{"key":"tvly-xxx","email":"demo@example.com"}
```

### 批量导入

```json
{"file":"email,password,tvly-xxx,2026-03-16 10:00:00;"}
```

---

## 配置

### 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `ADMIN_PASSWORD` | `admin` | 控制台与管理 API 的初始管理密码 |

### 数据持久化

SQLite 数据库存储在：

- `data/proxy.db`

Docker compose 默认会挂载：

- `./data:/app/data`

---

## Token 配额

每个 token 会记录自己的调用情况，并执行配额检查。

默认实现支持：
- hourly limit
- daily limit
- monthly limit

超过配额时会返回：
- `429 Too Many Requests`

---

## 与 Generator 的配合方式

如果你让 generator 自动上传 key 到 proxy，请在 generator 的 `config.py` 中启用：

```python
PROXY_AUTO_UPLOAD = True
PROXY_URL = "http://your-server:9874"
PROXY_ADMIN_PASSWORD = "your-password"
```

如果 generator 跑在容器里而 proxy 跑在宿主机：
- 通常不要直接写 `127.0.0.1:9874`
- 更常见的可用方式是 `host.docker.internal:9874`

---

## 安全建议

- 第一次部署后就修改默认 `ADMIN_PASSWORD`
- 如果对公网开放，建议配合 HTTPS 和额外访问控制
- 不要把真实 `.env` 提交到仓库

---

## 备注

这个 proxy 目标是：
- 简单
- 可自托管
- 能和 generator 配合
- 尽量少侵入 Tavily 官方客户端用法
