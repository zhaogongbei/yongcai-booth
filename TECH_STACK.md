# Technology Stack

D-Booth 项目的完整技术栈详解。

## 概览

| 层级 | 技术选型 | 版本 | 用途 |
|------|---------|------|------|
| Backend | Python + FastAPI | 3.11 / 0.109 | 云端 API 服务 |
| Frontend | React + TypeScript | 18 / 6 | Web 管理界面 |
| Runtime | .NET + C# | 8.0 / 12 | 现场运行时 |
| Database | PostgreSQL | 15+ | 主数据存储 |
| Cache | Redis | 7+ | 缓存与队列 |
| Queue | Celery | 5.3 | 异步任务 |
| Storage | S3/R2 | - | 对象存储 |

---

## Backend Stack

### 核心框架

**FastAPI 0.109.0**
- 高性能异步 Web 框架
- 自动 OpenAPI/Swagger 文档
- 原生类型提示支持
- 依赖注入系统
- 异步数据库支持

**Python 3.11+**
- 性能提升 25% (相比 3.10)
- 改进的错误消息
- 异步改进

### 数据库与 ORM

**PostgreSQL 15+**
```sql
-- 特性使用
- JSONB 列存储灵活数据
- 全文搜索 (to_tsvector)
- 递归查询 (WITH RECURSIVE)
- 并发控制 (SELECT FOR UPDATE)
- 分区表 (大数据量优化)
```

**SQLAlchemy 2.0.25**
```python
# 异步 ORM
from sqlalchemy.ext.asyncio import AsyncSession

async with AsyncSession(engine) as session:
    result = await session.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()
```

**Alembic 1.13.1**
- 数据库迁移管理
- 版本控制
- 自动生成迁移脚本

### 认证与安全

**PyJWT 2.13+**
- JWT 生成与验证
- RSA/HMAC 签名算法

**bcrypt 4.0+**
```python
# 密码哈希
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
```

**fastapi-csrf-protect 0.3.4**
- CSRF 令牌保护
- Cookie-based 存储

### 数据验证

**Pydantic 2.5.3**
```python
from pydantic import BaseModel, EmailStr, constr

class UserCreate(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=128)
    username: constr(pattern=r'^[a-zA-Z0-9_-]{3,20}$')
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!",
                "username": "john_doe"
            }
        }
```

### 异步任务

**Celery 5.3.6**
```python
# 异步任务定义
@celery_app.task(bind=True, max_retries=3)
def process_photo(self, photo_id: str):
    try:
        # 处理逻辑
        return {"status": "success"}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
```

**Redis 5.0.1**
- Celery Broker
- 缓存存储
- 分布式锁

### 图像处理

**Pillow 10.2.0**
```python
from PIL import Image, ImageEnhance

# 图像优化
img = Image.open(photo_path)
img.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
img.save(output_path, "JPEG", quality=85, optimize=True)
```

**OpenCV 4.10.0**
```python
import cv2

# 人脸检测
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
faces = face_cascade.detectMultiScale(gray, 1.3, 5)
```

**MediaPipe 0.10.14**
```python
import mediapipe as mp

# 姿态检测
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
results = pose.process(image)
```

### HTTP 客户端

**httpx 0.26.0**
```python
# 异步 HTTP 请求
async with httpx.AsyncClient() as client:
    response = await client.get('https://api.example.com/data')
    data = response.json()
```

### 支付集成

**Stripe 7.11.0**
```python
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

# 创建订阅
subscription = stripe.Subscription.create(
    customer=customer_id,
    items=[{"price": price_id}]
)
```

### 云存储

**boto3 1.34.131** (AWS SDK)
```python
import boto3

s3 = boto3.client('s3',
    endpoint_url=settings.R2_ENDPOINT_URL,
    aws_access_key_id=settings.R2_ACCESS_KEY_ID,
    aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY
)

# 上传文件
s3.upload_file(local_path, bucket, key)
```

**aioboto3 13.1.1** (异步版本)

### 错误追踪

**sentry-sdk 1.39.2**
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    traces_sample_rate=1.0,
    integrations=[FastApiIntegration()]
)
```

### 开发工具

**pytest 7.4+**
```python
@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    response = await client.post("/api/v1/users", json={...})
    assert response.status_code == 201
```

**black** - 代码格式化
**isort** - 导入排序
**mypy** - 类型检查
**ruff** - 快速 Linter

---

## Frontend Stack

### 核心框架

**React 18.3.1**
```tsx
import { useState, useEffect } from 'react';

export const Component: React.FC = () => {
  const [data, setData] = useState<Data[]>([]);
  
  useEffect(() => {
    fetchData();
  }, []);
  
  return <div>{/* UI */}</div>;
};
```

**TypeScript 6.0.3**
```typescript
// 严格类型检查
interface User {
  id: string;
  email: string;
  role: 'admin' | 'user';
}

const getUser = async (id: string): Promise<User> => {
  const response = await fetch(`/api/users/${id}`);
  return response.json();
};
```

### 构建工具

**Vite 6.4.3**
```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
});
```

### UI 框架

**TailwindCSS 4.1.12**
```tsx
// 原子化 CSS
<button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
  Click Me
</button>
```

**Radix UI 1.2.3**
```tsx
import * as Slider from '@radix-ui/react-slider';

<Slider.Root min={0} max={100} step={1}>
  <Slider.Track>
    <Slider.Range />
  </Slider.Track>
  <Slider.Thumb />
</Slider.Root>
```

**Lucide React 0.487.0**
```tsx
import { Camera, Upload, Download } from 'lucide-react';

<Camera size={24} className="text-blue-600" />
```

### 动画

**Motion 12.23.24** (Framer Motion)
```tsx
import { motion } from 'motion';

<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.3 }}
>
  Content
</motion.div>
```

### 数据可视化

**Recharts 2.15.2**
```tsx
import { LineChart, Line, XAxis, YAxis } from 'recharts';

<LineChart data={data}>
  <XAxis dataKey="date" />
  <YAxis />
  <Line type="monotone" dataKey="value" stroke="#8884d8" />
</LineChart>
```

### 工具库

**clsx 2.1.1** - 条件类名
```typescript
import clsx from 'clsx';

const className = clsx(
  'base-class',
  isActive && 'active-class',
  hasError && 'error-class'
);
```

**uuid 14.0.1** - UUID 生成
**qrcode 1.5.3** - 二维码生成

### 开发工具

**TypeScript** - 类型检查
**Vite** - 前端构建
**Vitest** - 单元测试

---

## Runtime Stack

### 核心框架

**.NET 8.0**
```csharp
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/v1/health", () => new { status = "healthy" });

app.Run();
```

**C# 12**
- Primary Constructors
- Collection Expressions
- Alias any type
- Default Lambda Parameters

### UI 框架

**WinUI 3**
```xml
<Page x:Class="Booth.Runtime.App.MainPage">
    <StackPanel>
        <TextBlock Text="Welcome to D-Booth" Style="{StaticResource TitleTextBlockStyle}" />
        <Button Content="Start Session" Click="OnStartSession" />
    </StackPanel>
</Page>
```

### 数据库

**SQLite**
```csharp
using Microsoft.EntityFrameworkCore;

public class BoothDbContext : DbContext
{
    public DbSet<Session> Sessions { get; set; }
    public DbSet<Shot> Shots { get; set; }
    
    protected override void OnConfiguring(DbContextOptionsBuilder options)
    {
        options.UseSqlite($"Data Source={dataDirectory}/booth.db");
    }
}
```

### 测试

**xUnit**
```csharp
[Fact]
public void CaptureShot_WhenActive_AddsShot()
{
    // Arrange
    var session = new SessionAggregate(Guid.NewGuid());
    session.Start();
    
    // Act
    session.CaptureShot("/path/photo.jpg", new CaptureMetadata());
    
    // Assert
    Assert.Single(session.Shots);
}
```

---

## Infrastructure Stack

### 容器化

**Docker**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

**Docker Compose**
```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: dbooth
      POSTGRES_USER: dbooth_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

### CI/CD

**GitHub Actions**
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pytest
```

### 监控

**Prometheus** - 指标收集
**Grafana** - 可视化
**Sentry** - 错误追踪
**ELK Stack** - 日志聚合

---

## 开发工具

### 版本控制

**Git** - 代码版本控制
**GitHub/GitLab** - 代码托管

### IDE

**VS Code** - 主力编辑器
**PyCharm Professional** - Python 开发
**Visual Studio** - C# 开发

### API 测试

**Postman** - API 测试
**Insomnia** - REST 客户端
**curl** - 命令行测试

### 数据库工具

**DBeaver** - 数据库客户端
**pgAdmin** - PostgreSQL 管理
**Redis Commander** - Redis 管理

---

## 部署栈

### 云平台

**AWS**
- EC2 (计算)
- RDS (PostgreSQL)
- ElastiCache (Redis)
- S3 (存储)
- CloudFront (CDN)

**Cloudflare**
- R2 (对象存储)
- CDN
- WAF
- DDoS 防护

### Web 服务器

**Nginx 1.24+**
```nginx
server {
    listen 443 ssl http2;
    server_name api.dbooth.ai;
    
    location /api/ {
        proxy_pass http://backend:8000;
    }
}
```

**Gunicorn**
```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

---

## 安全工具

**pip-audit** - Python 依赖安全检查
**npm audit** - Node.js 依赖审计
**Trivy** - 容器镜像扫描
**OWASP ZAP** - Web 应用安全测试

---

## 性能工具

**Locust** - 负载测试
**k6** - 性能测试
**py-spy** - Python 性能分析
**Chrome DevTools** - 前端性能分析

---

**文档维护者**: Tech Team  
**最后更新**: 2026-07-02
