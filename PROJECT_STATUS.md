# 项目状态

本文件是持续 AI 协作维护时的简洁项目记忆入口。

## 当前质量门禁

- 仓库卫生检查：`python tools/check_repository_hygiene.py`
- 后端 lint 门禁：`black --check .`、`isort --check-only .`、`ruff check app/ --select E9,F63,F7,F82`
- 后端测试：`python -m pytest -q`
- Python 依赖审计：`python -m pip_audit -r requirements.txt -r requirements-dev.txt --strict`
- 前端门禁：`npm run typecheck`、`npm run build`、`npm run audit:security`
- Runtime 门禁：`dotnet build --configuration Release --no-restore`、`dotnet test --configuration Release --no-build`

## 当前架构事实

- 根目录 `.github/workflows/ci.yml` 是唯一权威 CI workflow。
- 根目录 `VERSION` 是项目默认版本源；README 徽章和后端 `settings.VERSION` 默认值必须与它一致。
- 前端 `package.json` 和 `package-lock.json` 根包名必须是 `dbooth-frontend`，版本必须与根 `VERSION` 一致。
- 仓库卫生检查同时覆盖已跟踪和未跟踪的生成型报告/本地产物。
- 前端依赖管理使用 npm 和 `package-lock.json`。
- 前端文档、部署示例和开发指南不得回退到 pnpm/yarn。
- 前端是应用而不是库，`react` 和 `react-dom` 必须作为直接 runtime dependencies 声明。
- 前端 React runtime 与 `@types/react` / `@types/react-dom` 必须保持同一主版本。
- 后端 pytest 配置集中在 `D-Booth/backend/pyproject.toml`。
- 后端全量 mypy 不是 CI 门禁；当前 CI 使用 Ruff 致命错误检查，类型债务按模块逐步收敛。
- 后端模型 UUID 类型位于 `app.models.custom_types`；不要重新创建 `app.models.types`。
- Docker 发布上下文必须具备 `D-Booth/backend/Dockerfile` 和 `D-Booth/frontend/Dockerfile`。
- Docker 发布必须等待后端、前端、Runtime 和安全扫描全部通过，镜像命名空间来自 `DOCKER_USERNAME` secret。
- GitHub Release 由 release job 使用 `gh release create` 创建，不使用旧 release action；没有真实部署脚本时，CI 不应声明 staging/production 部署成功。
- CI 中第三方 GitHub Actions 必须使用版本 tag，不能使用浮动 `main` 或 `master` 分支。
- CI 安全扫描中的 Python 依赖审计必须使用项目声明的 `PYTHON_VERSION`，不能依赖 runner 默认 Python。
- Green Screen 设置和背景资产由后端数据库持久化；前端页面已接入读取、保存、背景上传、删除、预览和测试照片分析接口，并通过统一 API 地址解析后端上传资产。
- Booth 管理页必须通过真实 `team_id` 调用后端 `/booths`，不得提供后端 schema 不支持的假锁定成功操作。
- 虚拟助手前端播放列表、TTS 播放和设置页试听必须通过统一 API 地址访问后端；设置页试听使用当前编辑文本。
- 离线队列同步必须复用统一 API 客户端；打印任务使用后端真实 `/print-jobs` 接口，不得调用不存在的 `/api/v1/print`。
- 前端 Web Vitals 上报必须显式配置 `VITE_WEB_VITALS_ENDPOINT`；未配置时只保留开发环境 console 输出，不得默认请求后端不存在的 analytics endpoint。
- 前端统一 API 客户端必须同时支持调用方取消信号和内部 timeout；调用方取消应保持 `AbortError` 语义，不得误包装为 timeout 或普通请求失败。
- 分享设置 WhatsApp 号码字段的权威名称是 `whatsapp_number`；后端只应输出正确字段，但需要继续读取历史拼错的 `whatssapp_number` 配置。

## 近期完成

- 外部版本报告提交带回旧 Safety、pnpm、全量 mypy、旧 release action 和生成报告入库后，已恢复 CI/CD、文档、版本源和仓库卫生门禁。
- 已修复外部提交回退导致的活动统计打印和分享数量固定为 0 的数据回归。
- 已修复外部提交回退导致的团队最后 owner 可被移除/降级、Props API `X-Team-Id` 解析 500 的回归。
- 已修复前端 package 元数据中的 Figma 占位包名和版本漂移，并加入仓库卫生检查。
- 已修复调查和免责声明默认配置更新、调查回答关联、调查导出缺失配置、免责声明接受记录关联、重复提交/接受错误码和非 PNG 签名上传错误码的后端回归，并补充 API 回归测试。
- 已修复 Green Screen 设置和背景上传/删除未真实持久化的问题，并补齐 ORM、迁移和 API 回归测试。
- 已重新接入前端 Green Screen 页面读取、保存、背景上传和删除接口，避免用户侧仍表现为配置丢失。
- 已修复前端 Green Screen 预览、测试照片分析和背景缩略图仍依赖同源相对路径的问题。
- 已修复前端 Booth 管理页缺少 `team_id` 导致列表稳定加载失败、以及锁定操作假成功的问题。
- 已修复前端虚拟助手跨源部署下播放列表/TTS 失败，以及设置页试听不使用当前文本的问题。
- 已修复前端离线队列照片上传绕过统一 API 客户端、打印任务请求不存在接口的问题。
- 已修复前端生产环境 Web Vitals 默认上报到不存在硬编码接口导致 404 噪音的问题。
- 已修复前端统一 API 客户端在 hook 传入取消信号时 timeout 失效、取消请求进入普通错误状态的问题。
- 已修复分享设置后端 WhatsApp 字段拼写错误导致前后端契约不一致的问题，并补充 API 回归测试。
- 已新增前端生产 Docker 镜像配置。
- 已删除不会被仓库触发的嵌套后端旧 workflow。
- 已新增聚焦的 `BaseService` 单元测试覆盖。
- 已新增 URL 型前端请求 hook `useHttpFetch`，同时保留现有 async-function 型 `useFetch`。
- 已为 CI 增加显式权限，并将生产 release 创建迁移到 GitHub CLI。
- 已让 Docker 发布等待完整质量门禁，并移除硬编码镜像命名空间。
- 已升级 `fastapi-csrf-protect` 到 Pydantic v2 兼容版本，消除测试中的第三方 validator 弃用警告。
- 已将 Trivy 安全扫描 action 固定到版本 tag，避免浮动分支影响 CI 可复现性。
- 已将 React 运行时依赖从 optional peer 声明改为直接依赖，保证干净 `npm ci` 环境可复现。
- 已将 React 类型包从 19.x 收敛到 18.x，避免类型面领先运行时。
- 已移除后端未使用的 `python-magic` 运行时依赖，减少镜像依赖面。
- 已固定 CI 安全扫描里的 Python 依赖审计运行版本，避免 runner 默认 Python 漂移。
- 已清理部署/开发指南中的旧 pnpm 指令，并删除过期 AI 指令备份文件。
- 已统一根 `VERSION`、README 徽章和后端默认 API 版本，并让仓库卫生检查阻止版本源分裂回归。
- 已扩展仓库卫生检查，让未跟踪的生成型报告也会在本地暴露。
- 已移除 CI 中仅 echo 的假部署步骤，生产主线只保留真实的 GitHub Release 创建。
- 已修复活动统计服务中打印和分享数量固定为 0 的数据错误，并补充回归测试。
- 已修复 Green Screen 未实现批处理接口返回假成功的问题，改为明确返回 501 并补充回归测试。
- 已修复打印机取消任务和测试页接口把驱动失败误报为 500 的问题，并补充 API 回归测试。
- 已修复团队唯一 owner 可移除或降级自己导致团队无 owner 的数据完整性问题，并补充团队 API 回归测试。
- 已修复打印机校准接口未持久化却返回保存成功的问题，改为明确返回 501 并补充 API 回归测试。
- 已修复 Green Screen 设置更新接口未持久化却返回更新成功的问题，现已落库并补充 API 回归测试。
- 已修复 Props API 被重复挂载为 `/api/v1/props/props` 的路径问题、`X-Team-Id` 团队解析 500 问题，并让上传/删除业务规则错误返回 400。
- 前端 Green Screen 保存入口已从临时不可用提示恢复为真实保存，并复用统一 API 客户端。

## 已知债务

- 后端全量 mypy 仍存在真实类型债务，应按模块收敛，不应重新作为全量 CI 门禁。
- 若干旧的后端模块级 summary 文件仍作为历史信息保留；当前状态以本文件和 `CHANGELOG.md` 为准。
