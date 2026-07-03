# 部署指南

本文档提供 D-Booth 系统的完整部署说明，涵盖开发、测试和生产环境。

## 目录

- [系统要求](#系统要求)
- [开发环境部署](#开发环境部署)
- [生产环境部署](#生产环境部署)
- [Docker 部署](#docker-部署)
- [云平台部署](#云平台部署)
- [配置管理](#配置管理)
- [监控与日志](#监控与日志)
- [备份与恢复](#备份与恢复)
- [故障排查](#故障排查)

---

## 系统要求

### Backend API

- **操作系统**: Linux (Ubuntu 22.04 LTS 推荐) / Windows Server 2022
- **CPU**: 4核+ (推荐8核)
- **内存**: 8GB+ (推荐16GB)
- **存储**: 50GB+ SSD
- **Python**: 3.11+
- **数据库**: PostgreSQL 15+
- **缓存**: Redis 7+

### Frontend

- **Node.js**: 20+
- **包管理器**: npm 10+（使用 package-lock.json）
- **Web 服务器**: Nginx 1.24+ / Caddy 2.7+

### Runtime (.NET)

- **操作系统**: Windows 10/11 Pro
- **CPU**: 4核+ (Intel i5/i7 或 AMD Ryzen 5/7)
- **内存**: 16GB+ (推荐32GB)
- **存储**: 256GB+ SSD
- **.NET Runtime**: 8.0+
- **GPU**: 推荐独立显卡（用于 AI 处理）

### 网络

- **带宽**: 100Mbps+ (对称)
- **端口**:
  - Backend: 8000 (HTTP)
  - Frontend: 443 (HTTPS)
  - Runtime: 5000 (本地 HTTP)
  - PostgreSQL: 5432
  - Redis: 6379

---

## 开发环境部署

### 1. Backend 设置

```bash
# 克隆仓库
git clone <repo-url>
cd D-Booth/backend

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置数据库连接等

# 初始化数据库
alembic upgrade head

# 创建测试用户（可选）
python -m scripts.create_admin_user

# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend 设置

```bash
cd D-Booth/frontend

# 安装依赖
npm ci

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

### 3. Runtime 设置

```bash
cd D-Booth/runtime-dotnet

# 恢复 NuGet 包
dotnet restore

# 构建项目
dotnet build

# 运行 API Host
dotnet run --project src/Booth.Runtime.ApiHost

# 或运行 WinUI 应用
dotnet run --project src/Booth.Runtime.App
```

---

## 生产环境部署

### 架构概览

```
                        ┌─────────────┐
                        │   Cloudflare │
                        │   (CDN/WAF)  │
                        └──────┬───────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
            ┌───────▼────────┐   ┌───────▼────────┐
            │  Nginx (HTTPS) │   │  Nginx (HTTPS) │
            │   Load Balancer│   │   Frontend     │
            └───────┬────────┘   └────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
  ┌─────▼─────┐ ┌──▼──────┐ ┌──▼──────┐
  │ Backend 1 │ │Backend 2│ │Backend 3│
  │  (FastAPI)│ │(FastAPI)│ │(FastAPI)│
  └─────┬─────┘ └──┬──────┘ └──┬──────┘
        │          │           │
        └──────────┼───────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
  ┌─────▼────────┐   ┌───────▼────┐
  │ PostgreSQL   │   │   Redis    │
  │ (Primary +   │   │  Cluster   │
  │  Replicas)   │   │            │
  └──────────────┘   └────────────┘
```

### 1. Backend 生产部署

#### 使用 Systemd (Linux)

```bash
# /etc/systemd/system/dbooth-backend.service
[Unit]
Description=D-Booth Backend API
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=dbooth
Group=dbooth
WorkingDirectory=/opt/dbooth/backend
Environment="PATH=/opt/dbooth/backend/venv/bin"
ExecStart=/opt/dbooth/backend/venv/bin/uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --loop uvloop \
    --log-config logging.yaml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# 启用并启动服务
sudo systemctl enable dbooth-backend
sudo systemctl start dbooth-backend
sudo systemctl status dbooth-backend
```

#### Gunicorn + Uvicorn Workers

```python
# gunicorn_conf.py
import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
keepalive = 120
timeout = 300
max_requests = 1000
max_requests_jitter = 50
accesslog = "/var/log/dbooth/access.log"
errorlog = "/var/log/dbooth/error.log"
loglevel = "info"
```

```bash
gunicorn app.main:app -c gunicorn_conf.py
```

### 2. Frontend 生产部署

#### 构建优化

```bash
cd D-Booth/frontend

# 构建生产版本
npm run build

# 输出目录: dist/
```

#### Nginx 配置

```nginx
# /etc/nginx/sites-available/dbooth-frontend
server {
    listen 443 ssl http2;
    server_name app.dbooth.ai;

    ssl_certificate /etc/letsencrypt/live/dbooth.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dbooth.ai/privkey.pem;
    ssl_protocols TLSv1.3 TLSv1.2;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    root /var/www/dbooth/frontend/dist;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml+rss text/javascript;

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://backend-upstream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}

# Backend upstream
upstream backend-upstream {
    least_conn;
    server 10.0.1.10:8000 max_fails=3 fail_timeout=30s;
    server 10.0.1.11:8000 max_fails=3 fail_timeout=30s;
    server 10.0.1.12:8000 max_fails=3 fail_timeout=30s;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name app.dbooth.ai;
    return 301 https://$server_name$request_uri;
}
```

```bash
# 启用站点
sudo ln -s /etc/nginx/sites-available/dbooth-frontend /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. Database 设置

#### PostgreSQL 配置优化

```bash
# /etc/postgresql/15/main/postgresql.conf

# 连接
max_connections = 200
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 20MB
min_wal_size = 1GB
max_wal_size = 4GB
max_worker_processes = 8
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
max_parallel_maintenance_workers = 4

# 日志
log_destination = 'csvlog'
logging_collector = on
log_directory = '/var/log/postgresql'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_rotation_age = 1d
log_min_duration_statement = 1000  # 记录慢查询 (>1s)
```

#### 创建数据库和用户

```sql
-- 创建用户
CREATE USER dbooth_user WITH PASSWORD 'your_secure_password';

-- 创建数据库
CREATE DATABASE dbooth_prod OWNER dbooth_user;

-- 授权
GRANT ALL PRIVILEGES ON DATABASE dbooth_prod TO dbooth_user;

-- 启用扩展
\c dbooth_prod
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

#### 主从复制

```bash
# 主库 postgresql.conf
wal_level = replica
max_wal_senders = 10
wal_keep_size = 1GB

# 从库
standby_mode = 'on'
primary_conninfo = 'host=primary_host port=5432 user=replicator password=xxx'
```

### 4. Redis 配置

```bash
# /etc/redis/redis.conf

bind 0.0.0.0
protected-mode yes
requirepass your_redis_password
maxmemory 2gb
maxmemory-policy allkeys-lru

# 持久化
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfilename "appendonly.aof"

# 日志
loglevel notice
logfile /var/log/redis/redis-server.log
```

### 5. Celery Worker

```bash
# /etc/systemd/system/dbooth-celery.service
[Unit]
Description=D-Booth Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=dbooth
Group=dbooth
WorkingDirectory=/opt/dbooth/backend
Environment="PATH=/opt/dbooth/backend/venv/bin"
ExecStart=/opt/dbooth/backend/venv/bin/celery -A app.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --max-tasks-per-child=1000
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Docker 部署

### Docker Compose 完整配置

```yaml
# docker-compose.prod.yml
version: '3.9'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: dbooth_prod
      POSTGRES_USER: dbooth_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dbooth_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    environment:
      DATABASE_URL: postgresql+asyncpg://dbooth_user:${DB_PASSWORD}@postgres:5432/dbooth_prod
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
      DEBUG: "False"
      ENVIRONMENT: production
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 2G

  celery:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    command: celery -A app.celery_app worker --loglevel=info --concurrency=4
    environment:
      DATABASE_URL: postgresql+asyncpg://dbooth_user:${DB_PASSWORD}@postgres:5432/dbooth_prod
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Backend Dockerfile

```dockerfile
# backend/Dockerfile.prod
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非 root 用户
RUN useradd -m -u 1000 dbooth && chown -R dbooth:dbooth /app
USER dbooth

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Frontend Dockerfile

```dockerfile
# frontend/Dockerfile.prod
FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 部署命令

```bash
# 构建并启动
docker-compose -f docker-compose.prod.yml up -d --build

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f backend

# 扩容 backend
docker-compose -f docker-compose.prod.yml up -d --scale backend=5
```

---

## 云平台部署

### AWS 部署

#### 架构

- **ECS Fargate**: Backend 容器
- **RDS PostgreSQL**: 数据库
- **ElastiCache Redis**: 缓存
- **S3**: 静态资源与媒体文件
- **CloudFront**: CDN
- **ALB**: 负载均衡
- **Route 53**: DNS

#### Terraform 配置示例

```hcl
# main.tf
provider "aws" {
  region = "us-east-1"
}

# VPC
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "5.0"

  name = "dbooth-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  enable_dns_hostnames = true
}

# RDS PostgreSQL
resource "aws_db_instance" "dbooth_postgres" {
  identifier             = "dbooth-postgres"
  engine                 = "postgres"
  engine_version         = "15.4"
  instance_class         = "db.t3.medium"
  allocated_storage      = 100
  storage_type           = "gp3"
  db_name                = "dbooth_prod"
  username               = "dbooth_admin"
  password               = var.db_password
  multi_az               = true
  backup_retention_period = 7
  skip_final_snapshot    = false
  final_snapshot_identifier = "dbooth-final-snapshot"
}

# ECS Cluster
resource "aws_ecs_cluster" "dbooth" {
  name = "dbooth-cluster"
}

# ... 更多资源
```

---

## 配置管理

### 环境变量

```bash
# .env.production
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbooth_prod
REDIS_URL=redis://:pass@host:6379/0
SECRET_KEY=<generate-with-openssl-rand-hex-32>
DEBUG=False
ENVIRONMENT=production

# CORS
CORS_ORIGINS=https://app.dbooth.ai,https://admin.dbooth.ai

# S3 (AWS)
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_S3_BUCKET=dbooth-prod-media
AWS_REGION=us-east-1

# Sentry
SENTRY_DSN=https://xxx@sentry.io/xxx

# Stripe
STRIPE_API_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
```

---

## 监控与日志

### Prometheus + Grafana

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'dbooth-backend'
    static_configs:
      - targets: ['localhost:8000']
```

### 日志聚合 (ELK Stack)

```yaml
# filebeat.yml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/dbooth/*.log
    json.keys_under_root: true

output.elasticsearch:
  hosts: ["localhost:9200"]
```

---

## 备份与恢复

### 数据库备份

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="dbooth_prod_$DATE.sql.gz"

pg_dump -h localhost -U dbooth_user dbooth_prod | gzip > "$BACKUP_DIR/$FILENAME"

# 上传到 S3
aws s3 cp "$BACKUP_DIR/$FILENAME" s3://dbooth-backups/postgres/

# 保留最近30天的备份
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete
```

### 数据恢复

```bash
# 解压并恢复
gunzip < dbooth_prod_20260702.sql.gz | psql -h localhost -U dbooth_user dbooth_prod
```

---

## 故障排查

### 常见问题

#### 1. Backend 无法连接数据库

```bash
# 检查 PostgreSQL 状态
sudo systemctl status postgresql

# 检查连接
psql -h localhost -U dbooth_user -d dbooth_prod

# 查看日志
tail -f /var/log/postgresql/postgresql-15-main.log
```

#### 2. Frontend 502 Bad Gateway

```bash
# 检查 Nginx 配置
sudo nginx -t

# 检查 Backend 是否运行
curl http://localhost:8000/health

# 查看 Nginx 日志
tail -f /var/log/nginx/error.log
```

#### 3. Redis 连接超时

```bash
# 检查 Redis 状态
redis-cli ping

# 查看连接数
redis-cli info clients
```

---

完整部署清单请参考内部 Wiki。

如有部署问题，请联系 DevOps 团队: devops@dbooth.ai
