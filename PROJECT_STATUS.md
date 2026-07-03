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
- 前端依赖管理使用 npm 和 `package-lock.json`。
- 后端 pytest 配置集中在 `D-Booth/backend/pyproject.toml`。
- 后端全量 mypy 不是 CI 门禁；当前 CI 使用 Ruff 致命错误检查，类型债务按模块逐步收敛。
- 后端模型 UUID 类型位于 `app.models.custom_types`；不要重新创建 `app.models.types`。
- Docker 发布上下文必须具备 `D-Booth/backend/Dockerfile` 和 `D-Booth/frontend/Dockerfile`。
- GitHub Release 由生产发布 job 使用 `gh release create` 创建，不使用旧 release action。

## 近期完成

- 版本报告提交带回旧 Safety、pnpm 和全量 mypy 说明后，已恢复 CI 与文档门禁。
- 已新增前端生产 Docker 镜像配置。
- 已删除不会被仓库触发的嵌套后端旧 workflow。
- 已新增聚焦的 `BaseService` 单元测试覆盖。
- 已新增 URL 型前端请求 hook `useHttpFetch`，同时保留现有 async-function 型 `useFetch`。
- 已为 CI 增加显式权限，并将生产 release 创建迁移到 GitHub CLI。

## 已知债务

- 后端全量 mypy 仍存在真实类型债务，应按模块收敛，不应重新作为全量 CI 门禁。
- 第三方 `fastapi-csrf-protect` 在当前依赖下会输出 Pydantic v1 validator 弃用警告。
- 若干旧的后端模块级 summary 文件仍作为历史信息保留；当前状态以本文件和 `CHANGELOG.md` 为准。
