# Booth Runtime .NET Skeleton

该目录是下一代 AI Photo Booth 的 `.NET Runtime` 骨架层。

当前目标：

- 建立与现有 `backend` / `frontend` 并列的 Booth 现场运行时结构
- 固化 `Shared / Domain / App / Infra / Plugin SDK` 边界
- 给后续 WinUI Runtime、设备适配、SQLite、本地 API 留出清晰落点

当前骨架包含：

- `Booth.Runtime.App`
- `Booth.Runtime.ApiHost`
- `Booth.Runtime.SessionApp`
- `Booth.Domain.Session`
- `Booth.Shared.Contracts`
- `Booth.Infra.Storage.Sqlite`
- `Booth.Plugin.Abstractions`

当前已接通的最小端点：

- `GET /v1/health`
- `POST /v1/session/start`
- `GET /v1/sessions/{sessionId}`
- `POST /v1/sessions/{sessionId}/shots`
- `GET /v1/sessions/{sessionId}/shots`
- `POST /v1/session/{sessionId}/cancel`
- `POST /v1/print/jobs`
- `POST /v1/share/jobs`
- `GET /v1/jobs/{jobId}`
- `POST /v1/jobs/{jobId}/execute`
- `GET /v1/sessions/{sessionId}/assets`
- `GET /v1/assets/{assetId}`
- `DELETE /v1/assets/{assetId}`

当前已实现的最小执行语义：

- `capture shot` 会在 `data/captures/{sessionId}` 下真实写出采集文件
- `shots` 元数据会持久化到 SQLite
- `print/share` 入队时会保存结构化 `payload`
- `execute` 会把任务状态推进为 `running -> succeeded`
- `execute` 会在 `data/outputs/{sessionId}` 下真实写出输出文件
- `execute` 会创建 `output_assets` 记录并把 `created_asset_id` 反写到 `jobs`
- `assets` 支持单项查询与软删除
- `session details` 会聚合返回 `session + shots + jobs + assets`

本地联调请求示例见：

- `requests.http`

环境说明：

- `Runtime:DataDirectory` 可覆盖默认 `data` 目录，便于隔离测试和多实例运行
- 方案可在当前机器成功 `dotnet build`
- `dotnet test` 也已通过
- 若要直接 `dotnet run Booth.Runtime.ApiHost`，需要本机存在 `Microsoft.AspNetCore.App 8.0.x` 运行时

当前测试覆盖：

- SQLite `session` 持久化回读
- `capture shot` 文件落盘与元数据持久化
- `job execute -> output_assets` 产物链路
- `asset get/delete` 仓储语义
- 外部进程方式启动 `ApiHost` 的真实 HTTP 集成测试
