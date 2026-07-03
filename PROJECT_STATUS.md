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

## 近期完成

- 版本报告提交带回旧 Safety、pnpm 和全量 mypy 说明后，已恢复 CI 与文档门禁。
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
- 已修复 Green Screen 未实现批处理和背景删除接口返回假成功的问题，改为明确返回 501 并补充回归测试。
- 已修复打印机取消任务和测试页接口把驱动失败误报为 500 的问题，并补充 API 回归测试。

## 已知债务

- 后端全量 mypy 仍存在真实类型债务，应按模块收敛，不应重新作为全量 CI 门禁。
- 若干旧的后端模块级 summary 文件仍作为历史信息保留；当前状态以本文件和 `CHANGELOG.md` 为准。
