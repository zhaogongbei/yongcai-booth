# Changelog

所有对本项目的重要更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 修复
- 恢复后端服务层对旧 API 异常语义的兼容，确保 AI 任务与订阅配额错误继续按 `ValueError` 进入路由 400 处理。
- 修复团队删除后详情查询先返回 403 的顺序问题，已删除资源现在返回 404。
- 修复性能日志阈值边界，查询耗时达到阈值时记录慢查询 warning。
- 修复前端 hooks 类型门禁，允许 `useApi` 内部方法包装器传递 HTTP method，并收敛 `useForm` 泛型状态写入。
- 修复模板编辑器 `useUndoRedo` 调用签名，使其匹配 hooks 当前 options API。
- 修复 Makefile 和根 README 中残留的 pnpm 命令，避免本地开发、CI 与 AI 协作说明不一致。
- 修复 Runtime SQLite 批量保存事务类型，恢复 .NET Release build 门禁。
- 修复 `.gitignore` 在 Windows 下误忽略 `Booth.Infra.Storage.Sqlite` 源码目录的问题，并将 SQLite 存储项目源码纳入版本控制。
- 修复 Runtime 测试项目缺少 `coverlet.collector` 的问题，使 CI 覆盖率采集参数实际生效。
- 升级后端存在已知漏洞的 FastAPI、Starlette、python-multipart、Sentry SDK、Pillow、Pydantic Settings、pytest 和 Black 依赖。

### 优化
- Redis 缓存连接失败后短路降级，避免本地开发和测试在 Redis 不可用时反复阻塞。
- 前端安全审计统一为 `npm run audit:security`，固定使用 npm 官方审计 API，避免本地镜像 registry 不支持 audit 时门禁不可复现。
- 前端 hooks README 补齐已导出的 `useFetch` helper，并同步当前 hooks 使用方式。
- Python 依赖安全扫描从未固定的 `safety check` 切换为随开发依赖固定版本的 `pip-audit`。

### 变更
- 前端本地工作流统一使用 `npm ci`、`npm run dev`、`npm run typecheck` 和 `npm run build`，与 CI 和 `package-lock.json` 保持一致。
- 移除前端 pnpm workspace 配置，并让仓库卫生检查阻止 pnpm/yarn 锁文件回归。

### 计划中
- 多机位同步拍摄
- 4K 视频录制
- AR 滤镜引擎
- 云端模板市场
- AI 生成式背景
- 微信小程序集成
- 区块链照片存证

## [1.0.0] - 2026-07-02

### 新增

#### Backend API
- 用户认证系统（JWT + Refresh Token）
- 团队与多租户管理
- 事件与活动调度
- 照片上传与元数据管理
- 模板系统（动态模板引擎）
- 打印作业队列管理
- 分享链接与短链生成
- AI 任务编排（美颜、背景替换）
- 数据分析与报告
- 订阅管理（Stripe 集成）
- 媒体存储（S3 兼容）
- 水印与 LUT 滤镜
- 虚拟助手配置
- 电子签名采集
- 问卷调查系统
- 免责声明管理
- 数字道具库
- 分享设置（微信/抖音）
- 绿幕背景替换
- 打印机管理
- 相机控制 API
- Booth 设备注册
- 多设备同步
- 外部触发器集成
- GoPro WiFi 控制
- Webhook 集成
- 健康检查端点

#### Frontend 管理界面
- 响应式仪表板
- 活动管理界面
- 照片库与预览
- 模板编辑器
- 实时数据图表
- AI 工作室
- 系统配置面板
- 暗色/亮色主题
- 虚拟滚动优化
- 渐进式图片加载
- 错误边界处理
- 状态反馈组件

#### Runtime-dotnet 现场系统
- 会话生命周期管理
- 拍摄控制与元数据
- 本地文件存储
- SQLite 持久化
- 打印作业执行
- 分享作业处理
- 资产管理（查询/软删除）
- REST API 端点
- 健康检查
- 插件抽象层

#### 基础设施
- Docker Compose 编排
- Alembic 数据库迁移
- Celery 异步任务队列
- Redis 缓存层
- CORS 中间件
- CSRF 保护
- 速率限制
- Sentry 错误追踪
- 安全响应头
- 日志系统
- GitHub Actions CI

### 技术栈

- **Backend**: FastAPI 0.109, Python 3.11, SQLAlchemy 2.0, PostgreSQL 15
- **Frontend**: React 18, TypeScript 6, Vite 6, TailwindCSS 4
- **Runtime**: .NET 8.0, C# 12, ASP.NET Core 8, SQLite
- **AI/ML**: OpenCV 4.10, MediaPipe 0.10, Pillow 10.2
- **DevOps**: Docker, Redis 7, Celery 5, Alembic 1.13

### 文档

- 完整 README
- CLAUDE.md 开发规范
- API 文档（OpenAPI/Swagger）
- 架构设计文档
- 迭代 Prompt 集合

### 安全

- JWT 认证
- 多租户数据隔离
- RBAC 权限控制
- SQL 注入防护（参数化查询）
- XSS 防护（内容安全策略）
- CSRF 令牌验证
- 输入验证（Pydantic）
- 安全响应头
- 密码哈希（bcrypt）
- 敏感信息脱敏

---

## 版本说明

### 版本号格式：MAJOR.MINOR.PATCH

- **MAJOR**: 破坏性变更，不向后兼容
- **MINOR**: 新功能，向后兼容
- **PATCH**: Bug 修复，向后兼容

### 变更类型

- `新增` - 新功能
- `变更` - 现有功能的变更
- `弃用` - 即将移除的功能
- `移除` - 已移除的功能
- `修复` - Bug 修复
- `安全` - 安全漏洞修复
- `性能` - 性能改进
- `文档` - 文档更新

---

[1.0.0]: https://github.com/your-org/d-booth/releases/tag/v1.0.0
[Unreleased]: https://github.com/your-org/d-booth/compare/v1.0.0...HEAD
