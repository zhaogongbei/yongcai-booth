# Changelog

所有对本项目的重要更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 变更
- 前端本地工作流统一使用 `npm ci`、`npm run dev`、`npm run typecheck` 和 `npm run build`，与 CI 和 `package-lock.json` 保持一致。
- 移除前端 pnpm workspace 配置，并让仓库卫生检查阻止 pnpm/yarn 锁文件回归。

### 修复
- 恢复后端服务层对旧 API 异常语义的兼容，确保 AI 任务与订阅配额错误继续按 `ValueError` 进入路由 400 处理。
- 修复团队删除后详情查询先返回 403 的顺序问题，已删除资源现在返回 404。
- 修复性能日志阈值边界，查询耗时达到阈值时记录慢查询 warning。
- 恢复 CI/CD 安全门禁、Docker 镜像命名空间和发布流程，避免旧版占位部署与弱安全审计回归。
- 修复 Makefile、README、协作文档和部署文档中的旧工作流命令，保持 npm、pip-audit 与仓库卫生规则一致。
- 同步 README badge、后端配置默认版本和前端 package 元数据到根 `VERSION`。
- 修复活动详情统计中打印和分享数量固定为 0 的数据回归。
- 修复团队最后 owner 可被移除或降级导致团队无 owner 的数据完整性回归。
- 修复 `X-Team-Id` 团队解析调用缺失兼容方法导致 Props API 返回 500 的回归。
- 修复前端 package 元数据仍使用 Figma 占位包名和 `0.0.1` 版本的问题，并让仓库卫生检查阻止回归。
- 修复调查和免责声明默认配置存在后更新返回 500 的 ORM/Core Row 混用问题。
- 修复提交调查回答缺失 `survey_id` 导致首次提交返回 500 的数据完整性问题。
- 修复调查导出缺少配置时 404 被包装为 500 的错误码回归。
- 修复免责声明接受记录缺失 `disclaimer_id` 导致首次接受返回 500 的数据完整性问题。
- 修复免责声明重复接受和非 PNG 签名上传被宽泛异常处理包装成 500 的错误码回归。
- 修复 Green Screen 设置和背景上传/删除未真实持久化的问题，避免接口返回成功后配置或背景丢失。
- 修复 Green Screen 空测试照片 400 被宽泛异常处理包装成 500 的错误码回归。
- 修复 Green Screen 缺失活动时创建设置返回 500 的数据完整性错误，改为返回 404。
- 修复前端 Green Screen 页面仍提示保存不可用的问题，重新接入设置读取、保存、背景上传和删除接口。
- 修复前端 Green Screen 预览、测试照片分析和背景缩略图仍依赖同源相对路径的问题，统一使用配置的后端 API 地址。
- 修复前端 Booth 管理页未传 `team_id` 且锁定操作被后端忽略却提示成功的问题。
- 修复前端虚拟助手播放列表、TTS 播放和设置页试听仍依赖同源相对路径的问题，并让试听使用当前编辑文本。
- 修复前端离线队列同步时绕过统一 API 客户端并请求不存在的 `/api/v1/print` 接口的问题。
- 修复前端生产环境 Web Vitals 默认上报到不存在的硬编码 `/api/v1/analytics/vitals` 接口的问题，改为仅在显式配置 endpoint 时发送。
- 修复前端统一 API 客户端在调用方传入 `AbortSignal` 时内部 timeout 失效、且取消请求被误包装为 timeout 错误的问题。
- 修复分享设置后端 WhatsApp 号码字段拼写为 `whatssapp_number` 导致前后端契约不一致的问题，并兼容历史拼错配置。
- 修复后端本地媒体读取和 Green Screen 本地资产删除使用字符串前缀判断路径归属的问题，避免同前缀兄弟目录绕过上传目录边界。
- 修复本地部署下 Green Screen 背景资产返回 `/uploads/...` 但后端未提供对应静态路由导致前端缩略图和预览背景加载失败的问题，并兼容历史 `/uploads/green-screen/...` URL。
- 修复 Green Screen 事件级接口缺少认证与团队成员授权的问题，避免跨团队读取或修改设置、背景和批处理请求。
- 修复调查和免责声明管理配置、调查导出接口缺少认证与团队成员授权的问题，避免跨团队修改活动交互配置或导出回答。
- 修复同步接口缺少认证与团队成员授权、且错误调用 Booth 服务导致同步状态查询可能返回 500 的问题。
- 修复 Booth 管理接口缺少团队授权、错误静态调用 Booth 服务导致真实请求可能返回 500、以及 booth 关联跨团队活动的问题。
- 修复虚拟助手播放列表写入接口缺少认证与团队成员授权、以及 TTS 试听接口缺少登录认证的问题。

### 优化
- Booth 注册和心跳时间戳改为 timezone-aware UTC 时间，避免 Python 3.12 `datetime.utcnow()` 弃用警告。
- Redis 缓存连接失败后短路降级，避免本地开发和测试在 Redis 不可用时反复阻塞。

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

### 计划中
- 多机位同步拍摄
- 4K 视频录制
- AR 滤镜引擎
- 云端模板市场
- AI 生成式背景
- 微信小程序集成
- 区块链照片存证

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
