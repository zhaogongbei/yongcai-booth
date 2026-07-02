using Booth.Infra.Storage.Sqlite;
using Booth.Runtime.SessionApp;
using Booth.Shared.Contracts;

var repository = new SqliteSessionRepository();
var service = new SessionApplicationService(repository);

var session = await service.StartAsync(
    new SessionStartRequest(
        SessionId: "ses_demo_001",
        EventId: "evt_demo_001",
        Mode: SessionMode.Print,
        DeviceId: "dev_demo_001"),
    CancellationToken.None);

Console.WriteLine($"Booth Runtime skeleton started session: {session.Id} [{session.Status}]");
