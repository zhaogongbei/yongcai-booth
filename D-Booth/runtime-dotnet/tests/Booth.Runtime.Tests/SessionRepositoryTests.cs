using Booth.Domain.Session;
using Booth.Infra.Storage.Sqlite;
using Booth.Shared.Contracts;
using Xunit;

namespace Booth.Runtime.Tests;

public sealed class SessionRepositoryTests
{
    [Fact]
    public async Task SaveAndLoad_ShouldPreserveTerminalStatusAndTimestamps()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"booth-runtime-{Guid.NewGuid():N}.db");
        var repository = new SqliteSessionRepository(databasePath);

        var session = new SessionAggregate("ses_test_001", "evt_test_001", SessionMode.Print, "dev_test_001");
        session.BeginCountdown();
        session.Complete();

        await repository.SaveAsync(session, CancellationToken.None);
        var loaded = await repository.GetAsync(session.Id, CancellationToken.None);

        Assert.NotNull(loaded);
        Assert.Equal(SessionStatus.Completed, loaded!.Status);
        Assert.Equal(session.StartedAtUtc.ToString("O"), loaded.StartedAtUtc.ToString("O"));
        Assert.Equal(session.CompletedAtUtc!.Value.ToString("O"), loaded.CompletedAtUtc!.Value.ToString("O"));
    }
}
