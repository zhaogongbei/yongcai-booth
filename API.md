# API Documentation

D-Booth Backend API 完整参考文档。

## Base URL

```
Development: http://localhost:8000
Staging:     https://staging-api.dbooth.ai
Production:  https://api.dbooth.ai
```

## Authentication

所有需要认证的端点需要在请求头中包含 JWT Token：

```http
Authorization: Bearer <access_token>
```

### 获取 Token

**POST** `/api/v1/auth/login`

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 刷新 Token

**POST** `/api/v1/auth/refresh`

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

---

## Error Responses

所有错误响应遵循统一格式：

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2026-07-02T10:30:00Z",
  "path": "/api/v1/events"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 204 | No Content | 删除成功，无返回内容 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证或 Token 无效 |
| 403 | Forbidden | 无权限访问 |
| 404 | Not Found | 资源不存在 |
| 422 | Unprocessable Entity | 数据验证失败 |
| 429 | Too Many Requests | 请求过于频繁 |
| 500 | Internal Server Error | 服务器内部错误 |

---

## API Endpoints

完整的 API 文档请访问 Swagger UI：
- Development: http://localhost:8000/docs
- Production: https://api.dbooth.ai/docs

---

## Rate Limiting

API 请求受到基于客户端 IP 的固定窗口速率限制保护（Redis 计数，回退到内存）：

- **每分钟**: 60 requests（`RATE_LIMIT_PER_MINUTE`）
- **每小时**: 1000 requests（`RATE_LIMIT_PER_HOUR`）
- `/health`、`/metrics` 和 `/api/v1/internal/*` 豁免限流

超出限制将返回 `429 Too Many Requests`。

每个响应头中包含限制信息：

```http
X-RateLimit-Limit-Minute: 60
X-RateLimit-Limit-Hour: 1000
X-RateLimit-Remaining-Minute: 45
X-RateLimit-Remaining-Hour: 980
```

---

## Pagination

列表端点支持分页查询：

**Query Parameters:**
- `page`: 页码（从 1 开始）
- `page_size`: 每页数量（默认 20，最大 100）

**Response:**
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "pages": 8
}
```

---

## Filtering & Sorting

**Filtering:**
```
GET /api/v1/events?status=active&event_type=wedding
```

**Sorting:**
```
GET /api/v1/events?sort_by=created_at&order=desc
```

---

## Webhooks

配置 Webhook 以接收事件通知：

**POST** `/api/v1/webhooks`

```json
{
  "url": "https://your-server.com/webhook",
  "events": ["photo.created", "print.completed"],
  "secret": "your_webhook_secret"
}
```

### Webhook Events

- `photo.created` - 新照片上传
- `photo.processed` - AI 处理完成
- `print.created` - 打印作业创建
- `print.completed` - 打印完成
- `session.started` - 会话开始
- `session.completed` - 会话结束

### Webhook Payload

```json
{
  "event": "photo.created",
  "timestamp": "2026-07-02T10:30:00Z",
  "data": {
    "id": "uuid",
    "url": "https://cdn.dbooth.ai/photos/xxx.jpg"
  }
}
```

### Signature Verification

验证 Webhook 请求签名：

```python
import hmac
import hashlib

signature = hmac.new(
    secret.encode(),
    request.body,
    hashlib.sha256
).hexdigest()

if signature != request.headers['X-Webhook-Signature']:
    raise ValueError("Invalid signature")
```

---

更多详细信息请查看 [OpenAPI 规范](https://api.dbooth.ai/openapi.json)。
