# Booth Runtime .NET Skeleton

该目录是下一代 AI Photo Booth 的 `.NET Runtime` 骨架层。

当前目标：

- 建立与现有 `backend` / `frontend` 并列的 Booth 现场运行时结构
- 固化 `Shared / Domain / App / Infra / Plugin SDK` 边界
- 给后续 WinUI Runtime、设备适配、SQLite、本地 API 留出清晰落点

当前骨架包含：

- `Booth.Runtime.App`
- `Booth.Runtime.SessionApp`
- `Booth.Domain.Session`
- `Booth.Shared.Contracts`
- `Booth.Infra.Storage.Sqlite`
- `Booth.Plugin.Abstractions`
