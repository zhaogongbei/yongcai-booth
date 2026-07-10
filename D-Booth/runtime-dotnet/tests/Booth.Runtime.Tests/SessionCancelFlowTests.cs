using Booth.Domain.Session;
using Booth.Infra.Storage.Sqlite;
using Booth.Runtime.SessionApp;
using Booth.Shared.Contracts;
using Xunit;

namespace Booth.Runtime.Tests;

public sealed class SessionCancelFlowTests
{
    [Fact]
    public async Task CancelAsync_ShouldBeIdempotent_WhenSessionIsAlreadyCancelled()
    {
        var context = CreateContext();
        await context.Service.StartAsync(
            new SessionStartRequest("ses_double_cancel", "evt_double_cancel", SessionMode.Print, "dev_double_cancel"),
            CancellationToken.None);

        var first = await context.Service.CancelAsync("ses_double_cancel", CancellationToken.None);
        var second = await context.Service.CancelAsync("ses_double_cancel", CancellationToken.None);

        Assert.NotNull(first);
        Assert.NotNull(second);
        Assert.Equal(SessionStatus.Cancelled, second!.Status);
        Assert.Equal(
            first!.CompletedAtUtc?.ToString("O"),
            second.CompletedAtUtc?.ToString("O"));
    }

    [Fact]
    public async Task CancelAsync_ShouldFailClosed_WhenSessionIsCompleted()
    {
        var context = CreateContext();
        var completed = SessionAggregate.Rehydrate(
            "ses_completed_cancel",
            "evt_completed_cancel",
            SessionMode.Print,
            "dev_completed_cancel",
            SessionStatus.Completed,
            DateTimeOffset.UtcNow.AddMinutes(-5),
            DateTimeOffset.UtcNow.AddMinutes(-1),
            retryCount: 0);
        await context.SessionRepository.SaveAsync(completed, CancellationToken.None);

        var exception = await Assert.ThrowsAsync<SessionStateException>(() =>
            context.Service.CancelAsync("ses_completed_cancel", CancellationToken.None));
        var persisted = await context.Service.GetAsync("ses_completed_cancel", CancellationToken.None);

        Assert.Equal(ErrorCodes.SessionInvalidState, exception.ErrorCode);
        Assert.NotNull(persisted);
        Assert.Equal(SessionStatus.Completed, persisted!.Status);
    }

    private static TestContext CreateContext()
    {
        var tempRoot = Path.Combine(Path.GetTempPath(), $"booth-runtime-session-cancel-{Guid.NewGuid():N}");
        Directory.CreateDirectory(tempRoot);
        var databasePath = Path.Combine(tempRoot, "runtime.db");
        var sessionRepository = new SqliteSessionRepository(databasePath);
        var service = new SessionApplicationService(
            sessionRepository,
            new SqliteShotRepository(databasePath),
            Path.Combine(tempRoot, "captures"));
        return new TestContext(service, sessionRepository);
    }

    private sealed record TestContext(SessionApplicationService Service, SqliteSessionRepository SessionRepository);
}
