# Architecture Overview

本文档描述 D-Booth 系统的整体架构设计、技术选型与关键决策。

## 系统架构

### 高层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         咏彩Booth 系统                            │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
        ┌───────▼──────┐ ┌─────▼──────┐ ┌─────▼────────┐
        │   Backend    │ │  Frontend   │ │   Runtime    │
        │   (Cloud)    │ │  (Web App)  │ │  (On-Site)   │
        └───────┬──────┘ └─────┬──────┘ └─────┬────────┘
                │               │               │
        ┌───────▼───────────────▼───────────────▼────────┐
        │            基础设施层                            │
        │  PostgreSQL │ Redis │ S3 │ Celery │ SQLite    │
        └──────────────────────────────────────────────────┘
```

### 三层架构

#### 1. Backend - 云端管理 API

**职责**:
- 用户认证与授权
- 团队与多租户管理
- 事件调度与配置
- 照片元数据管理
- AI 任务编排
- 订阅与计费
- 数据分析与报告

**技术栈**:
- **框架**: FastAPI (Python 3.11)
- **数据库**: PostgreSQL 15 (主数据) + Redis 7 (缓存)
- **ORM**: SQLAlchemy 2.0 (async)
- **任务队列**: Celery + Redis
- **存储**: S3 兼容对象存储
- **AI**: OpenCV, MediaPipe, Pillow

**架构模式**: 分层架构 + Repository 模式

```
app/
├── api/          # API 路由层 (Controller)
├── services/     # 业务逻辑层 (Service)
├── repositories/ # 数据访问层 (Repository)
├── models/       # 数据模型 (ORM Models)
├── schemas/      # 数据传输对象 (DTO/Pydantic)
├── core/         # 核心配置 (Config, DB, Auth)
└── tasks/        # 后台任务 (Celery Tasks)
```

#### 2. Frontend - Web 管理界面

**职责**:
- 活动管理
- 照片库浏览
- 模板编辑器
- 数据分析仪表板
- 系统配置
- 用户管理

**技术栈**:
- **框架**: React 18 (函数组件 + Hooks)
- **语言**: TypeScript 6 (strict mode)
- **构建**: Vite 6
- **样式**: TailwindCSS 4
- **状态管理**: React Context + Hooks
- **UI 组件**: Radix UI + 自定义组件
- **图表**: Recharts
- **请求**: fetch API (封装)

**架构模式**: 功能模块化 + 组件驱动

```
src/
├── app/
│   ├── screens/    # 页面组件
│   ├── components/ # 可复用组件
│   ├── hooks/      # 自定义 Hooks
│   ├── lib/        # 工具函数与 API 客户端
│   └── constants/  # 常量配置
└── main.tsx        # 应用入口
```

#### 3. Runtime - 现场运行时

**职责**:
- 现场拍摄控制
- 相机 SDK 集成
- 本地文件管理
- 离线运行支持
- 打印作业执行
- 硬件设备控制

**技术栈**:
- **框架**: .NET 8.0 (C# 12)
- **UI**: WinUI 3 (Windows 10/11)
- **API**: ASP.NET Core Minimal API
- **数据库**: SQLite (本地持久化)
- **架构**: DDD (领域驱动设计) + CQRS

**架构模式**: 洋葱架构 (Clean Architecture)

```
src/
├── Booth.Domain.Session/      # 领域层 (核心业务逻辑)
├── Booth.Shared.Contracts/    # 共享契约 (DTO, Enums)
├── Booth.Infra.Storage.Sqlite/# 基础设施层 (数据持久化)
├── Booth.Runtime.ApiHost/     # API 主机 (HTTP 接口)
├── Booth.Runtime.App/         # WinUI 应用 (用户界面)
└── Booth.Plugin.Abstractions/ # 插件抽象 (扩展点)
```

---

## 数据流

### 1. 拍摄流程

```
┌──────────┐   触发拍摄    ┌──────────┐   HTTP    ┌──────────┐
│  用户    │  ─────────→  │ Runtime  │  ─────→  │ Backend  │
│          │              │  (本地)   │          │  (云端)   │
└──────────┘              └────┬─────┘          └──────────┘
                               │
                          ┌────▼────┐
                          │  相机   │
                          │  SDK    │
                          └────┬────┘
                               │
                          ┌────▼────┐
                          │  本地   │
                          │  存储   │
                          └─────────┘
```

**步骤**:
1. 用户触发拍摄 (触摸屏/按钮/遥控)
2. Runtime 调用相机 SDK 捕获照片
3. 照片保存到本地存储 (`data/captures/`)
4. 元数据写入 SQLite
5. (可选) 上传照片到 Backend S3
6. Backend 记录照片元数据到 PostgreSQL

### 2. AI 处理流程

```
┌──────────┐  上传照片   ┌──────────┐  入队任务  ┌──────────┐
│ Frontend │  ────────→ │ Backend  │  ────────→│  Celery  │
│          │            │   API    │           │  Worker  │
└──────────┘            └──────────┘           └────┬─────┘
                                                     │
                                                ┌────▼────┐
                                                │   AI    │
                                                │  引擎   │
                                                └────┬────┘
                                                     │
                                                ┌────▼────┐
                                                │   S3    │
                                                │  存储   │
                                                └─────────┘
```

**步骤**:
1. 用户上传照片并选择 AI 处理类型
2. Backend 创建异步任务 (Celery)
3. Worker 从 S3 下载原图
4. 执行 AI 处理 (美颜/背景替换/滤镜)
5. 处理后照片上传回 S3
6. 更新任务状态和结果 URL

### 3. 打印流程

```
┌──────────┐  发起打印   ┌──────────┐  同步任务  ┌──────────┐
│ Runtime  │  ────────→ │ Backend  │  ────────→│ Runtime  │
│          │            │   API    │           │  打印机   │
└──────────┘            └──────────┘           └────┬─────┘
                                                     │
                                                ┌────▼────┐
                                                │  物理   │
                                                │  打印机  │
                                                └─────────┘
```

**步骤**:
1. 用户选择照片并发起打印
2. Runtime 创建打印作业 (本地 SQLite)
3. (可选) 同步到 Backend 用于统计
4. Runtime 生成打印文件 (加水印/边框)
5. 调用打印机驱动执行打印
6. 更新作业状态

---

## 技术选型

### Backend 选型

| 技术 | 选择 | 理由 |
|------|------|------|
| 框架 | FastAPI | 高性能、异步、自动文档、类型提示 |
| 数据库 | PostgreSQL | 成熟稳定、ACID、丰富功能、JSON 支持 |
| ORM | SQLAlchemy | 异步支持、灵活强大、生态完善 |
| 缓存 | Redis | 高性能、丰富数据结构、分布式锁 |
| 任务队列 | Celery | 成熟稳定、功能丰富、易于扩展 |
| 认证 | JWT | 无状态、跨域友好、易于扩展 |

### Frontend 选型

| 技术 | 选择 | 理由 |
|------|------|------|
| 框架 | React | 生态成熟、组件化、Hooks 简洁 |
| 构建 | Vite | 快速冷启动、HMR、现代化 |
| 样式 | TailwindCSS | 原子化、高效、可定制 |
| 类型 | TypeScript | 类型安全、IDE 友好、重构容易 |
| 状态 | Context + Hooks | 简单够用、无额外依赖 |

### Runtime 选型

| 技术 | 选择 | 理由 |
|------|------|------|
| 平台 | .NET 8 | 高性能、跨平台、丰富生态 |
| UI | WinUI 3 | 现代化、流畅、Windows 原生 |
| 数据库 | SQLite | 嵌入式、零配置、可靠 |
| 架构 | DDD + Clean | 清晰边界、易测试、可维护 |

---

## 关键设计决策

### 1. 为何采用三层分离架构？

**决策**: Backend (云端) + Frontend (Web) + Runtime (本地)

**理由**:
- **职责分离**: 云端管理与现场运行解耦
- **离线支持**: Runtime 可独立运行，无需网络
- **灵活部署**: 各层独立扩展和升级
- **安全隔离**: 现场设备不直接访问云端数据库

### 2. 为何 Runtime 使用 .NET 而非 Python？

**决策**: .NET 8 + C#

**理由**:
- **性能**: C# 比 Python 快 5-10 倍 (图像处理关键)
- **硬件集成**: 更好的 Windows SDK 支持 (相机/打印机)
- **UI**: WinUI 3 提供原生 Windows 体验
- **部署**: 单文件发布，无需 Python 环境
- **稳定性**: 强类型系统减少运行时错误

### 3. 为何使用 FastAPI 而非 Django？

**决策**: FastAPI

**理由**:
- **异步优先**: 原生 async/await，高并发性能
- **自动文档**: OpenAPI/Swagger 自动生成
- **类型提示**: Pydantic 数据验证，IDE 友好
- **轻量**: 按需引入功能，无冗余
- **现代**: 拥抱 Python 3.11+ 新特性

### 4. 为何使用 SQLite 作为 Runtime 数据库？

**决策**: SQLite (本地) + PostgreSQL (云端)

**理由**:
- **零配置**: 无需安装数据库服务
- **嵌入式**: 单文件数据库，易于备份
- **离线**: 无需网络连接
- **性能**: 本地读写极快
- **可靠**: 经过验证的 ACID 数据库

### 5. 为何采用 Repository 模式？

**决策**: Service + Repository 分层

**理由**:
- **测试性**: Repository 可 Mock，Service 易测试
- **复用**: Repository 方法可在多个 Service 中复用
- **解耦**: 业务逻辑与数据访问分离
- **迁移**: 更换数据库只需修改 Repository

---

## 可扩展性设计

### 水平扩展

```
                    ┌──────────────┐
                    │ Load Balancer│
                    └──────┬───────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
  ┌─────▼─────┐      ┌────▼─────┐      ┌────▼─────┐
  │ Backend 1 │      │Backend 2 │      │Backend 3 │
  └─────┬─────┘      └────┬─────┘      └────┬─────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                    ┌──────▼───────┐
                    │  PostgreSQL  │
                    │  (Primary +  │
                    │   Replicas)  │
                    └──────────────┘
```

**策略**:
- Backend 无状态，可无限扩展
- 数据库主从复制，读写分离
- Redis Cluster 分布式缓存
- Celery Worker 按需增减

### 插件系统

Runtime 支持插件扩展：

```csharp
public interface IPlugin
{
    string Name { get; }
    string Version { get; }
    Task<bool> InitializeAsync();
    Task ExecuteAsync(PluginContext context);
}
```

**扩展点**:
- 相机驱动 (Canon/Nikon/Sony/GoPro)
- 打印机驱动 (DNP/Mitsubishi/HiTi)
- AI 滤镜 (自定义算法)
- 外部触发器 (红外/按钮/RFID)

---

## 安全架构

### 多租户隔离

```python
# 所有查询自动过滤 team_id
async def get_events(current_user: User):
    return await db.execute(
        select(Event).where(Event.team_id == current_user.team_id)
    )
```

### 认证流程

```
1. 用户登录 → Backend 验证密码
2. 生成 JWT Access Token (15min) + Refresh Token (7day)
3. 前端每次请求携带 Access Token
4. Token 过期 → 使用 Refresh Token 刷新
5. Refresh Token 过期 → 重新登录
```

### 数据加密

- **传输**: HTTPS (TLS 1.3)
- **存储**: 敏感字段 AES-256 加密
- **密码**: bcrypt 哈希 (cost=12)
- **Token**: JWT 签名验证

---

## 监控与日志

### 日志层级

```
ERROR   - 需要立即处理的错误
WARNING - 需要关注但不影响运行
INFO    - 关键操作记录
DEBUG   - 调试信息 (仅开发环境)
```

### 监控指标

- **系统**: CPU, 内存, 磁盘, 网络
- **应用**: 请求延迟, 错误率, QPS
- **业务**: 拍摄次数, 打印次数, 用户活跃度
- **数据库**: 连接数, 查询耗时, 慢查询

### 告警策略

| 指标 | 阈值 | 级别 |
|------|------|------|
| API 错误率 | > 5% | P0 |
| 响应时间 | > 3s (P95) | P1 |
| 数据库连接 | > 80% | P1 |
| 磁盘使用 | > 90% | P2 |

---

## 性能优化

### Backend 优化

- **数据库**: 索引优化, 查询优化, 连接池
- **缓存**: Redis 缓存热点数据, TTL 5-60 分钟
- **异步**: 使用 asyncio 提升并发
- **CDN**: 静态资源和图片使用 CDN

### Frontend 优化

- **代码分割**: 路由懒加载
- **虚拟滚动**: 大列表性能优化
- **图片优化**: WebP 格式, 渐进加载
- **缓存**: Service Worker 离线缓存

### Runtime 优化

- **内存池**: 复用对象减少 GC
- **并行处理**: Task.WhenAll 并行任务
- **本地缓存**: 缓存配置和资源
- **批量操作**: 批量写入 SQLite

---

## 未来演进

### 短期 (3-6 个月)

- [ ] 微服务拆分 (API Gateway + 服务)
- [ ] 事件驱动架构 (Kafka/RabbitMQ)
- [ ] GraphQL API
- [ ] 移动端 App (React Native)

### 中期 (6-12 个月)

- [ ] Kubernetes 部署
- [ ] 服务网格 (Istio/Linkerd)
- [ ] 分布式追踪 (Jaeger/Zipkin)
- [ ] AI 模型训练平台

### 长期 (1-2 年)

- [ ] 多云部署 (AWS + Azure + 阿里云)
- [ ] 边缘计算 (Edge Runtime)
- [ ] 联邦学习 (隐私保护 AI)
- [ ] Web3 集成 (NFT 照片)

---

**文档维护者**: 架构团队  
**最后更新**: 2026-07-02  
**审阅周期**: 季度
