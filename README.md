# 咏彩Booth (D-Booth) - 下一代智能拍照亭系统

[![Version](https://img.shields.io/badge/version-1.0.45-blue.svg)](./VERSION)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](./LICENSE)

> 基于 AI 的全能拍照亭解决方案，集成云端管理、现场运行时、智能美颜、实时打印与社交分享。

## 项目概述

D-Booth 是对标 DSLRBooth Professional 的下一代 AI Photo Booth 系统，提供：

- 🎯 **多架构支持**：云端 API + 本地 Runtime + Web 管理界面
- 🤖 **AI 驱动**：智能美颜、背景替换、虚拟助手、姿态识别
- 📸 **专业拍摄**：支持 Canon/Nikon DSLR、GoPro、网络摄像头
- 🎨 **模板系统**：动态模板、绿幕合成、数字道具、水印滤镜
- 🖨️ **打印管理**：队列系统、多打印机支持、成本追踪
- 🔗 **社交分享**：短链生成、二维码、微信/抖音集成
- 📊 **数据分析**：实时统计、活动报告、订阅管理
- 🔒 **企业级**：多租户隔离、RBAC 权限、审计日志

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                      咏彩Booth 系统                       │
├─────────────────┬───────────────────┬───────────────────┤
│   Backend API   │  Frontend Admin   │  Runtime-dotnet   │
│   (FastAPI)     │  (React/Vite)     │  (C# WinUI)       │
├─────────────────┼───────────────────┼───────────────────┤
│ • 用户认证      │ • 活动管理        │ • 现场拍摄控制    │
│ • 团队管理      │ • 照片库          │ • 相机 SDK 集成   │
│ • 事件调度      │ • 模板编辑器      │ • 本地打印队列    │
│ • AI 任务       │ • 数据分析        │ • 离线运行        │
│ • 订阅计费      │ • 系统配置        │ • SQLite 持久化   │
└─────────────────┴───────────────────┴───────────────────┘
```

## 快速开始

### 前置依赖

- **Backend**: Python 3.11+, PostgreSQL 15+, Redis 7+
- **Frontend**: Node.js 20+, npm 10+
- **Runtime**: .NET 8.0 SDK, Windows 10/11

### 一键启动

```bash
# 克隆仓库
git clone <repository-url>
cd D-Booth

# 启动 Backend API
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# 启动 Frontend (新终端)
cd ../frontend
npm ci
npm run dev

# 启动 Runtime (新终端, Windows)
cd ../runtime-dotnet
dotnet build
dotnet run --project src/Booth.Runtime.ApiHost
```

> 以上为快速上手概览。完整的环境搭建与故障排查以 [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md#初次设置) 为准。

访问：
- Backend API: http://localhost:8000
- API 文档: http://localhost:8000/docs
- Frontend: http://localhost:5173
- Runtime API: http://localhost:5000

## 项目结构

```
D-Booth/
├── backend/              # FastAPI 云端 API
│   ├── app/
│   │   ├── api/v1/      # REST 端点
│   │   ├── core/        # 配置、数据库、认证
│   │   ├── models/      # SQLAlchemy 模型
│   │   ├── schemas/     # Pydantic 模式
│   │   ├── services/    # 业务逻辑
│   │   ├── repositories/# 数据访问层
│   │   └── tasks/       # Celery 后台任务
│   ├── alembic/         # 数据库迁移
│   └── tests/           # 测试套件
│
├── frontend/            # React 管理界面
│   ├── src/
│   │   ├── app/
│   │   │   ├── screens/ # 页面组件
│   │   │   ├── components/# UI 组件
│   │   │   ├── hooks/   # React Hooks
│   │   │   └── lib/     # API 客户端
│   │   └── main.tsx
│   └── public/
│
├── runtime-dotnet/      # .NET 现场运行时
│   ├── src/
│   │   ├── Booth.Runtime.App/        # WinUI 主程序
│   │   ├── Booth.Runtime.ApiHost/    # 本地 API 服务
│   │   ├── Booth.Domain.Session/     # 会话领域模型
│   │   ├── Booth.Infra.Storage.Sqlite/# SQLite 仓储
│   │   └── Booth.Plugin.Abstractions/# 插件 SDK
│   └── tests/
│
├── docs/                # 设计文档
├── tools/               # 工具脚本
├── CLAUDE.md            # AI 开发规范
├── VERSION              # 语义化版本
└── README.md            # 本文件
```

## 开发指南

### 分支策略

- `main` - 稳定生产版本
- `develop` - 开发主分支
- `feature/*` - 功能分支
- `fix/*` - 修复分支

### 提交规范

遵循 Conventional Commits：

```
feat: 新增相机 SDK 集成
fix: 修复打印队列阻塞问题
refactor: 重构模板渲染引擎
perf: 优化图像处理性能
docs: 更新部署文档
```

### 版本管理

项目使用语义化版本（SemVer）：

- **MAJOR**: 破坏性变更
- **MINOR**: 向后兼容的新功能
- **PATCH**: 向后兼容的问题修复

当前版本在 `VERSION` 文件中维护，每次提交自动递增 PATCH 版本。

### 代码规范

- **Python**: PEP 8, Black, isort, mypy
- **TypeScript**: ESLint, Prettier, strict mode
- **C#**: .editorconfig, StyleCop

详见 [CLAUDE.md](./CLAUDE.md)。

## 测试

```bash
# Backend 测试
cd backend
pytest --cov=app --cov-report=html

# Frontend 测试
cd frontend
npm run typecheck
npm run build

# Runtime 测试
cd runtime-dotnet
dotnet test
```

## 部署

### Docker 部署

```bash
# Backend + PostgreSQL + Redis
cd backend
docker-compose up -d

# Frontend (静态构建)
cd frontend
npm run build
# 部署 dist/ 到 CDN 或 Nginx
```

### 生产环境检查清单

- [ ] 设置 `SECRET_KEY` 环境变量
- [ ] 配置 PostgreSQL 连接（禁用 SQLite）
- [ ] 配置 Redis 连接
- [ ] 设置 `DEBUG=False`
- [ ] 配置 CORS 白名单
- [ ] 启用 HTTPS (TLS 1.3)
- [ ] 配置 Sentry DSN
- [ ] 设置备份策略
- [ ] 配置 CDN (Cloudflare/AWS CloudFront)
- [ ] 启用速率限制与 WAF

## 关键特性

### AI 能力

- **美颜算法**: MediaPipe 人脸检测 + OpenCV 磨皮美白
- **背景替换**: GrabCut/U2-Net 抠图 + 绿幕合成
- **虚拟助手**: 语音引导、姿态提示、倒计时动画
- **智能裁剪**: 人脸识别自动构图

### 硬件集成

- **相机**: Canon SDK, Nikon SDK, GoPro WiFi API
- **打印机**: DNP, Mitsubishi, Canon SELPHY, HiTi
- **传感器**: 红外触发器、压力垫、RFID 读卡器
- **外设**: 补光灯控制、背景幕电机

### 商业功能

- **订阅管理**: Stripe 集成、按设备计费、功能分级
- **多租户**: 团队隔离、权限控制、资源配额
- **审计日志**: 操作追踪、合规报告
- **API 集成**: Webhook、外部触发器、第三方集成

## 文档

- [架构设计文档](./docs/DSLRBooth-深度分析与下一代-AI-Photo-Booth-设计方案.md)
- [Backend API 文档](./D-Booth/backend/README.md)
- [Frontend 开发指南](./D-Booth/frontend/README.md)
- [Runtime 架构说明](./D-Booth/runtime-dotnet/README.md)
- [迭代 Prompt 集合](./D-Booth/.claude/iteration-prompts/README.md)

## 路线图

版本规划与功能路线以 [ROADMAP.md](./ROADMAP.md) 为唯一权威来源，本文件不再单独维护路线图，避免两处漂移。

## 贡献

本项目为商业闭源软件，内部开发团队贡献指南详见 Confluence。

## 许可证

Copyright © 2026 咏彩科技. All rights reserved.

Proprietary and confidential. Unauthorized copying or distribution is prohibited.

## 支持

- 📧 Email: support@dbooth.ai
- 💬 企业微信: [内部支持群]
- 🐛 Issues: [内部 JIRA]
- 📖 Wiki: [内部 Confluence]

---

**Built with ❤️ by 咏彩 AI Team**
