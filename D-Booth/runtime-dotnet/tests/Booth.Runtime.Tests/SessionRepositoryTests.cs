using Booth.Domain.Session;
using Booth.Infra.Storage.Sqlite;
using Booth.Shared.Contracts;
using Xunit;

namespace Booth.Runtime.Tests;

public sealed class SessionRepositoryTests
{
    [Fact]
    public async Task TryAddAsync_ShouldNotReplaceExistingSessionIdentity()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"booth-runtime-{Guid.NewGuid():N}.db");
        var repository = new SqliteSessionRepository(databasePath);
        var original = new SessionAggregate("ses_try_add", "evt_original", SessionMode.Print, "dev_original");
        var conflicting = new SessionAggregate("ses_try_add", "evt_conflict", SessionMode.Gif, "dev_conflict");

        Assert.True(await repository.TryAddAsync(original, CancellationToken.None));
        Assert.False(await repository.TryAddAsync(conflicting, CancellationToken.None));

        var loaded = await repository.GetAsync(original.Id, CancellationToken.None);
        Assert.NotNull(loaded);
        Assert.Equal(original.EventId, loaded!.EventId);
        Assert.Equal(original.Mode, loaded.Mode);
        Assert.Equal(original.DeviceId, loaded.DeviceId);
    }

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
