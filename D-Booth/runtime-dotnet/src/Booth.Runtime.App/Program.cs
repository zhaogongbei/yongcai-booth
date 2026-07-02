using Booth.Infra.Storage.Sqlite;
using Booth.Runtime.SessionApp;
using Booth.Shared.Contracts;

var dataDir = Path.Combine(AppContext.BaseDirectory, "data");
var databasePath = Path.Combine(dataDir, "runtime.db");
var repository = new SqliteSessionRepository(databasePath);
var shotRepository = new SqliteShotRepository(databasePath);
var capturesRoot = Path.Combine(dataDir, "captures");
var service = new SessionApplicationService(repository, shotRepository, capturesRoot);

var session = await service.StartAsync(
    new SessionStartRequest(
        SessionId: "ses_demo_001",
        EventId: "evt_demo_001",
        Mode: SessionMode.Print,
        DeviceId: "dev_demo_001"),
    CancellationToken.None);

Console.WriteLine($"Booth Runtime skeleton started session: {session.Id} [{session.Status}]");
